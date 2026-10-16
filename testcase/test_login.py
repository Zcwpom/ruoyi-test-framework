"""登录模块接口测试"""
import allure
import pytest

from common.yaml_util import read_yaml


@allure.epic("若依权限管理系统")
@allure.feature("登录认证")
class TestLogin:
    """
    登录接口 —— 正常流 + 异常流 + 鉴权

    Allure 装饰器说明（报告里 Behaviors 页面的分组依据）：
      epic     —— 最顶层，一个项目/系统
      feature  —— 功能模块，如"登录认证"
      story    —— 具体场景，如"正常登录"
      title    —— 用例在报告里显示的中文名（不写就显示函数名）
      severity —— 严重级别：BLOCKER / CRITICAL / NORMAL / MINOR / TRIVIAL
    """

    # ---------------- 正常场景 ----------------

    @allure.story("正常登录")
    @allure.title("正确的用户名密码登录成功并返回 Token")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.smoke
    @pytest.mark.p0
    def test_login_success(self, client, login_api):
        """正确的用户名密码，应登录成功并返回 token"""
        with allure.step("调用登录接口"):
            resp = login_api.login("admin", "admin123")

        with allure.step("校验 HTTP 状态码为 200"):
            assert resp.status_code == 200

        with allure.step("校验业务码为 200"):
            body = resp.json()
            assert body["code"] == 200, f"登录失败：{body.get('msg')}"

        with allure.step("校验返回了有效 Token"):
            assert body.get("token"), "登录成功但没返回 token"
            assert len(body["token"]) > 20

    @allure.story("登录态获取")
    @allure.title("登录后可获取本人用户信息与权限")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.p1
    def test_get_info_after_login(self, client):
        """登录后能拿到自己的用户信息"""
        with allure.step("请求 /getInfo"):
            resp = client.get("/getInfo")
            body = client.assert_ok(resp, "获取用户信息")

        with allure.step("校验用户名与权限标识"):
            assert body["user"]["userName"] == "admin"
            assert "permissions" in body
            # admin 是超管，应带 *:*:* 权限
            assert "*:*:*" in body["permissions"]

    @allure.story("登录态获取")
    @allure.title("登录后可获取动态菜单路由")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.p1
    def test_get_routers(self, client):
        """登录后能拿到动态菜单路由"""
        with allure.step("请求 /getRouters"):
            body = client.assert_ok(client.get("/getRouters"), "获取菜单路由")
        with allure.step("校验路由数据非空"):
            assert body["data"], "菜单路由为空"

    # ---------------- 异常场景（参数化，一条用例覆盖多种错误输入） ----------------

    @allure.story("异常登录")
    @allure.title("非法凭证登录必须被拒绝")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.p0
    @pytest.mark.parametrize("username,password,desc", [
        ("admin",  "wrong_password",  "密码错误"),
        ("nouser", "admin123",        "用户名不存在"),
        ("",       "admin123",        "用户名为空"),
        ("admin",  "",                "密码为空"),
        ("",       "",                "用户名密码都为空"),
        ("admin' OR '1'='1", "x",     "SQL 注入尝试"),
        ("admin",  "admin123" + " " * 50, "密码超长"),
    ])
    def test_login_fail(self, client, login_api, username, password, desc):
        """异常登录：必须失败，且不能返回 500"""
        allure.dynamic.title(f"异常登录 - {desc}")

        with allure.step(f"使用非法凭证登录（{desc}）"):
            resp = login_api.login(username, password)

        with allure.step("校验 HTTP 层未崩溃"):
            assert resp.status_code == 200, f"【{desc}】HTTP 状态码异常：{resp.status_code}"

        with allure.step("校验登录被拒绝且有错误提示"):
            body = resp.json()
            assert body["code"] != 200, f"【{desc}】非法凭证竟然登录成功了！"
            assert body.get("msg"), f"【{desc}】失败但没返回错误提示"

    # ---------------- 鉴权 / 越权 ----------------
    #
    # ★ 重要实测发现：
    #   若依鉴权失败返回的是 HTTP 200 + body.code = 401，
    #   而不是 HTTP 401。
    #
    #   这是若依的统一响应设计：所有响应都走 HTTP 200，业务码放在 body 里。
    #   好处：前端 axios 拦截器只需处理一套逻辑。
    #   代价：API 网关、监控系统、安全扫描器、非浏览器客户端
    #        无法通过 HTTP 状态码区分鉴权失败 —— REST 语义上的设计瑕疵。
    #
    #   → 这一条可以写进测试报告，作为「设计观察」。

    @allure.story("鉴权与越权")
    @allure.title("未携带 Token 访问受保护接口必须被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.p0
    def test_access_without_token(self):
        """未登录访问受保护接口 —— 应被拒绝"""
        from common.request_util import RequestUtil

        with allure.step("使用未登录的客户端请求用户列表"):
            raw = RequestUtil(read_yaml("config/config.yaml")["base_url"])
            resp = raw.get("/system/user/list", params={"pageNum": 1, "pageSize": 10})
            body = resp.json()

        with allure.step("校验业务码为 401 且提示认证失败"):
            assert body["code"] == 401, f"未携带 Token 竟然能访问用户列表！返回 {body}"
            assert "认证失败" in body.get("msg", ""), f"拒绝原因不明确：{body.get('msg')}"

    @allure.story("鉴权与越权")
    @allure.title("伪造 Token 访问受保护接口必须被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.p0
    def test_access_with_invalid_token(self):
        """伪造 Token 访问 —— 应被拒绝"""
        from common.request_util import RequestUtil

        with allure.step("使用伪造 Token 请求用户列表"):
            raw = RequestUtil(read_yaml("config/config.yaml")["base_url"])
            raw.set_token("fake.token.value")
            resp = raw.get("/system/user/list", params={"pageNum": 1, "pageSize": 10})
            body = resp.json()

        with allure.step("校验业务码为 401"):
            assert body["code"] == 401, f"伪造 Token 竟然能通过鉴权！返回 {body}"
            assert "认证失败" in body.get("msg", "")

    @allure.story("鉴权与越权")
    @allure.title("特性记录：鉴权失败的 HTTP 状态码为 200（非 401）")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.p2
    def test_auth_failure_http_status_is_200(self):
        """
        特性记录测试（characterization test）

        ★ 这里不断言"应该怎样"，而是记录"现在怎样"。
          一旦以后若依改了行为，这条测试会红，提醒你更新认知。

        实测：鉴权失败的 HTTP 状态码是 200，业务码是 401。
        """
        from common.request_util import RequestUtil

        with allure.step("请求受保护接口并观察 HTTP 状态码"):
            raw = RequestUtil(read_yaml("config/config.yaml")["base_url"])
            resp = raw.get("/system/user/list", params={"pageNum": 1, "pageSize": 10})

        with allure.step("记录现状：HTTP 200 + 业务码 401"):
            assert resp.status_code == 200, "HTTP 状态码变了，需更新测试认知"
            assert resp.json()["code"] == 401, "业务码变了，需更新测试认知"
