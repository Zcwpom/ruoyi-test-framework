"""
requests 二次封装

为什么不用原生 requests：
  1. 统一日志：每个请求和响应自动打日志，出问题能追溯
  2. 统一超时：避免用例卡死
  3. 统一 Token：登录一次，后续请求自动带上
  4. 统一 base_url：用例里只写 /system/user/list
  5. Session 复用：保持 Cookie 和连接，性能更好
  6. 自动附加到 Allure 报告：每条用例都能看到真实请求/响应
"""
import json
import re
import requests

from common.logger_util import log


# ---------- 脱敏 ----------
# 日志文件和 Allure 报告会被多人查看、长期归档，凭证不能明文落地。
# 统一打码规则：保留前 4 位 + 标注总长度。
#   好处：既能判断「两个请求用的是不是同一个 token」，又拿不到可用的凭证。
# 如果本地排查确实需要看全，临时把 MASK_ENABLE 改成 False 即可。
MASK_ENABLE = True

SENSITIVE_KEYS = ("password", "passwd", "pwd", "token", "secret", "authorization", "cookie")


def _mask(value) -> str:
    """把单个敏感值打码"""
    s = "" if value is None else str(value)
    if not s:
        return s
    if len(s) <= 8:
        return "*" * len(s)
    return f"{s[:4]}***（共{len(s)}位，已脱敏）"


def mask_obj(obj):
    """递归脱敏 dict / list 里的敏感字段（用于 JSON 结构）"""
    if not MASK_ENABLE:
        return obj
    if isinstance(obj, dict):
        return {
            k: (_mask(v) if any(s in str(k).lower() for s in SENSITIVE_KEYS) else mask_obj(v))
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [mask_obj(i) for i in obj]
    return obj


# 兜底用的正则，覆盖三种常见写法：
#   ① JSON             "token":"xxx"
#   ② form / query     token=xxx   token: xxx
#   ③ 请求头            Authorization: Bearer xxx
_MASK_RE = re.compile(
    r'("(?:' + "|".join(SENSITIVE_KEYS) + r')"\s*:\s*")([^"]*)(")',
    re.IGNORECASE,
)
_MASK_KV_RE = re.compile(
    r'(' + "|".join(SENSITIVE_KEYS) + r')'   # 键
    r'(\s*[=:]\s*)'                          # 分隔符
    r'((?:Bearer\s+)?)'                      # 可选 Bearer 前缀
    r'([^\s,;&"\'}\]]+)',                    # 值
    re.IGNORECASE,
)


def mask_text(text: str) -> str:
    """文本脱敏：正则替换，不解析 JSON，适合直接打日志（开销小）"""
    if not MASK_ENABLE or not text:
        return text
    text = _MASK_RE.sub(lambda m: m.group(1) + _mask(m.group(2)) + m.group(3), text)
    return _MASK_KV_RE.sub(
        lambda m: m.group(1) + m.group(2) + m.group(3) + _mask(m.group(4)), text
    )


def desensitize(text: str) -> str:
    """结构脱敏：能解析成 JSON 就按字段处理，否则退回正则"""
    if not MASK_ENABLE or not text:
        return text
    try:
        return json.dumps(mask_obj(json.loads(text)), ensure_ascii=False)
    except Exception:
        return mask_text(text)

try:
    import allure
except ImportError:      # allure 没装时不影响用例执行
    allure = None


def _attach(name: str, body: str, as_json: bool = False):
    """把内容附加到 Allure 报告（失败静默，不影响用例）"""
    if allure is None:
        return
    try:
        allure.attach(
            body,
            name=name,
            attachment_type=allure.attachment_type.JSON if as_json
            else allure.attachment_type.TEXT,
        )
    except Exception:
        pass


class RequestUtil:
    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.token = None

    # ---------- Token ----------

    def set_token(self, token: str):
        """设置 Token，之后所有请求自动带 Authorization 头"""
        self.token = token
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"
        else:
            self.session.headers.pop("Authorization", None)

    # ---------- 核心请求 ----------

    def request(self, method: str, url: str, **kwargs):
        full_url = url if url.startswith("http") else f"{self.base_url}{url}"
        kwargs.setdefault("timeout", self.timeout)

        # ---- 请求日志 + Allure 附件 ----
        log.info(f"→ {method.upper()} {full_url}")
        req_desc = [f"{method.upper()} {full_url}"]
        if kwargs.get("params"):
            log.info(f"  params: {kwargs['params']}")
            req_desc.append(f"params: {json.dumps(kwargs['params'], ensure_ascii=False)}")
        if kwargs.get("json"):
            body_str = desensitize(json.dumps(kwargs["json"], ensure_ascii=False))
            log.info(f"  json:   {body_str}")
            req_desc.append(f"body:   {body_str}")
        if kwargs.get("data"):
            log.info(f"  data:   {kwargs['data']}")
            req_desc.append(f"data:   {kwargs['data']}")
        _attach("请求", "\n".join(req_desc))

        resp = self.session.request(method, full_url, **kwargs)

        # ---- 响应日志 + Allure 附件（均先脱敏再落盘）----
        # 注意顺序：先脱敏再截断。反过来的话，超长响应被截断后
        # 正则匹配不到收尾的引号，token 会漏出去。
        log.info(f"← {resp.status_code}  {mask_text(resp.text)[:500]}")
        is_json = resp.headers.get("content-type", "").startswith("application/json")
        try:
            _attach(f"响应 {resp.status_code}",
                    json.dumps(mask_obj(resp.json()), ensure_ascii=False, indent=2) if is_json
                    else mask_text(resp.text[:5000]),
                    as_json=is_json)
        except Exception:
            _attach(f"响应 {resp.status_code}", mask_text(resp.text[:5000]))

        return resp

    def get(self, url, **kwargs):
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        return self.request("POST", url, **kwargs)

    def put(self, url, **kwargs):
        return self.request("PUT", url, **kwargs)

    def delete(self, url, **kwargs):
        return self.request("DELETE", url, **kwargs)

    # ---------- 便捷断言 ----------

    def assert_ok(self, resp, msg: str = ""):
        """断言 HTTP 200 且业务 code == 200（若依约定 code=200 为成功）"""
        assert resp.status_code == 200, \
            f"{msg} HTTP 状态码异常：{resp.status_code}, {resp.text[:200]}"
        body = resp.json()
        assert body.get("code") == 200, \
            f"{msg} 业务码异常：{body.get('code')} - {body.get('msg')}"
        return body
