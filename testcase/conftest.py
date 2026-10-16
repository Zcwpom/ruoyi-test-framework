"""
conftest.py —— pytest 的"公共夹具"文件

pytest 会自动发现这个文件，不需要 import。
核心价值：把"每个用例都要做的事"抽出来，只写一次。

scope 说明（重要，面试会问）：
  session —— 整个测试会话只执行一次（最适合登录）
  module  —— 每个 .py 文件执行一次
  class   —— 每个测试类执行一次
  function—— 每个用例执行一次（默认）
"""
import os
import platform
import random
import uuid
from datetime import datetime

import pytest

from api.login_api import LoginApi
from common.request_util import RequestUtil
from common.logger_util import log
from common.yaml_util import read_yaml

# 全局配置，整个测试会话只读一次
CONF = read_yaml("config/config.yaml")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 内置账号，任何情况下都不允许被测试清理掉
PROTECTED_USERS = {"admin", "ry"}


# ============================================================
# 会话级：HTTP 客户端 + 登录（只执行一次，所有用例共用）
# ============================================================
@pytest.fixture(scope="session")
def client():
    """
    返回一个已登录的 RequestUtil 实例。
    所有用例通过参数 client 拿到它，天然共享登录态。
    """
    log.info("=" * 60)
    log.info("初始化测试会话：创建客户端并登录")

    c = RequestUtil(CONF["base_url"], timeout=CONF.get("timeout", 10))

    login_api = LoginApi(c)
    resp = login_api.login(
        CONF["account"]["username"],
        CONF["account"]["password"],
    )

    assert resp.status_code == 200, f"登录请求失败：{resp.status_code} {resp.text[:200]}"
    body = resp.json()
    assert body.get("code") == 200, f"登录失败：{body.get('msg')}"

    token = body["token"]
    c.set_token(token)
    log.info(f"登录成功，Token = {token[:30]}...")
    log.info("=" * 60)

    yield c

    log.info("测试会话结束")


# ============================================================
# 函数级：用例前后打日志
# ============================================================
@pytest.fixture(autouse=True)
def case_logger(request):
    """每个用例前后打日志，方便定位是哪条用例出的问题"""
    log.info(f"---- 开始执行：{request.node.name} ----")
    yield
    log.info(f"---- 执行结束：{request.node.name} ----")


# ============================================================
# 常用 fixture：直接拿各个 API 对象
# ============================================================
@pytest.fixture
def user_api(client):
    from api.user_api import UserApi
    return UserApi(client)


@pytest.fixture
def login_api(client):
    return LoginApi(client)


# ============================================================
# ★ 测试数据治理（自动化测试的必修课）
# ============================================================

@pytest.fixture
def uniq():
    """
    唯一后缀（8 位十六进制），用于用户名、邮箱等字符串字段。

    为什么需要：
      固定用户名重复运行会撞唯一约束，导致用例结果不可信：
        本该 fail 的变成 xpass（假通过）
        本该 pass 的变成 fail（假失败）
    """
    return uuid.uuid4().hex[:8]


@pytest.fixture
def uniq_num():
    """
    唯一数字后缀（8 位数字），用于手机号。

    ★ 为什么单独搞一个：
      手机号只能是数字，而 uuid 里含字母。
      这就是「唯一化」最容易漏的地方 ——
      你只把用户名唯一化了，手机号还是写死的，照样撞。
    """
    return f"{random.randint(0, 99999999):08d}"


@pytest.fixture
def fake_user(uniq, uniq_num):
    """
    生成一套「所有唯一性字段都不重复」的用户数据。

    ★ 设计要点：
      造测试数据前，先搞清楚被测系统对哪些字段做了唯一性校验。
      若依的 sys_user 表对 userName / phonenumber / email 三个字段
      都有唯一约束，只唯一化其中一个是不够的。
    """
    return {
        "userName": f"autotest_{uniq}",
        "nickName": f"自动化用户_{uniq}",
        "password": "Test@123456",
        "phonenumber": f"13{uniq_num[:9]}",        # 11 位数字
        "email": f"autotest_{uniq}@test.com",
        "status": "0",
    }


@pytest.fixture
def data_cleanup(user_api):
    """
    用例自清理：把创建的用户名注册进来，用例结束后自动删除。

    为什么用 yield：
      yield 之后的代码是 teardown，**即使用例断言失败也一定会执行**，
      保证脏数据不会留在环境里。

    用法：
        def test_xxx(user_api, data_cleanup, fake_user):
            data_cleanup.append(fake_user["userName"])   # 注册，结束后自动删
            user_api.add_user(**fake_user)

    ★ 两处保护（2026-10 修，原来是两个隐患）：
      1. 内置账号（PROTECTED_USERS）直接跳过 ——
         「用户名重复」那条用例提交的 userName 就是 admin，
         它会被注册进清理列表，原来会真的去调删除接口删 admin。
      2. 检查删除接口的返回码 ——
         原来不看返回码，删失败了也记「已删除」，等于在假装清理。
    """
    names = []
    yield names

    # ---- 无论用例成功还是失败，都执行清理 ----
    for name in names:
        name = (name or "").strip()

        if not name:
            continue
        if name in PROTECTED_USERS:
            log.warning(f"[数据清理] 跳过内置账号：{name}")
            continue

        try:
            found = user_api.find_user_by_name(name)
            if not found:
                log.info(f"[数据清理] {name} 未落库，无需删除")
                continue

            resp = user_api.delete_user(found["userId"]).json()
            if resp.get("code") == 200:
                log.info(f"[数据清理] 已删除测试用户 {name}（userId={found['userId']}）")
            else:
                log.warning(
                    f"[数据清理] 删除 {name}（userId={found['userId']}）被拒绝："
                    f"{resp.get('code')} - {resp.get('msg')}"
                )
        except Exception as e:
            log.warning(f"[数据清理] 删除 {name} 出错：{e}")


# ============================================================
# ★ Allure 报告增强
# ============================================================

def pytest_sessionfinish(session, exitstatus):
    """
    测试会话结束后，写入 Allure 的「环境信息」。
    生成 report/allure-results/environment.properties，
    Allure 会自动读它并显示在报告的 Environment 区块。
    """
    results_dir = os.path.join(ROOT, "report", "allure-results")
    if not os.path.isdir(results_dir):
        return

    env = {
        "Base.URL": CONF["base_url"],
        "Test.Account": CONF["account"]["username"],
        "Python": platform.python_version(),
        "OS": f"{platform.system()} {platform.release()}",
        "Framework": "pytest + requests + Allure",
        "Run.Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        with open(os.path.join(results_dir, "environment.properties"),
                  "w", encoding="utf-8") as f:
            for k, v in env.items():
                f.write(f"{k}={v}\n")
        log.info("[Allure] 已写入 environment.properties")
    except Exception as e:
        log.warning(f"[Allure] 写入环境信息失败：{e}")
