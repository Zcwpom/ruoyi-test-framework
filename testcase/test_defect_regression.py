# -*- coding: utf-8 -*-
"""
已知缺陷回归用例（D1 / D7 / D9）

来源：Postman 集合里的「01 用户管理 / 91 已知缺陷回归」那一组，
      原来是 3 条 JS 断言，只能在 Newman 里跑。这里用 pytest 重写，
      好处是和 D10~D12 进同一个套件、同一套 CI。

★ 断言写的是「缺陷修好之后应该是什么样」，所以现在都是红的。
  用 xfail 备案：现在红是预期内（不算失败），修好之后会变成 XPASS，
  提醒你去掉 xfail 标记。

缺陷报告在另一个仓库 ruoyi-api-test 里：
  D1  用户详情 NPE 信息泄露      严重程度 中
  D7  分页参数静默降级            严重程度 低
  D9  isAsc 未校验导致 SQL 泄露   严重程度 高
"""
import json

import allure
import pytest

REPORT_BASE = "https://github.com/Zcwpom/ruoyi-api-test/blob/main/"

# 响应里绝对不该出现的东西：包名 / 类名 / 方法名 / SQL 关键字 / 服务器路径
INTERNAL_LEAKS = [
    "com.ruoyi",                # 包名
    "SysUser",                  # 类名
    "getRoles",                 # 方法名
    "java.lang",                # JDK 类型名
    "SELECT",                   # SQL 语句
    "LEFT JOIN",                # SQL 语句
    "SQLSyntaxErrorException",  # 数据库异常类
    "SysUserMapper",            # Mapper 类名
    "ruoyi-admin.jar",          # 服务器上的 jar 包名
    "mapper/system",            # Mapper XML 路径
]


def _text_of(body) -> str:
    return json.dumps(body, ensure_ascii=False)


def _find_leaks(body) -> list:
    """返回响应体里出现的敏感关键词（空列表 = 干净）"""
    upper = _text_of(body).upper()
    return [k for k in INTERNAL_LEAKS if k.upper() in upper]


def _collect_problems(body) -> list:
    """把响应里的问题一次性收集出来，而不是断言到第一个就停"""
    problems = []

    leaks = _find_leaks(body)
    if leaks:
        problems.append(f"响应里泄露了后端内部信息：{leaks}")

    if body.get("code") != 200:
        msg = str(body.get("msg") or "")
        if not any("\u4e00" <= c <= "\u9fff" for c in msg):
            problems.append(f"报错提示不可读（一个中文都没有）：{msg[:120]!r}")

    return problems


@allure.epic("若依权限管理系统")
@allure.feature("已知缺陷回归")
class TestDefectRegression:
    """
    已提交缺陷的回归用例。

    运行方式：
        pytest testcase/test_defect_regression.py -v            # 正常跑（缺陷未修 → xfail）
        pytest testcase/test_defect_regression.py -v --runxfail # 强制跑，看真实失败原因
    """

    # ================================================================
    # D1 —— 查询不存在的用户时返回 Java 异常信息
    # ================================================================

    @allure.story("D1 用户详情信息泄露")
    @allure.title("[D1] 查询不存在的用户，响应不得出现包名 / 类名 / 方法名")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.issue(REPORT_BASE + "缺陷报告-D1-用户详情NPE信息泄露.md", "D1 缺陷报告")
    @pytest.mark.p1
    @pytest.mark.xfail(
        reason="D1 未修复：接口把 NullPointerException 的异常信息直接返回给了客户端",
        strict=False,
    )
    def test_d1_nonexistent_user_no_internal_leak(self, user_api):
        """
        预期（来自缺陷报告 D1）：
          返回一句能看懂的提示，比如 {"code":500,"msg":"用户不存在"}，
          不要暴露后端内部信息。

        依据：同一个系统的 GET /system/config/configKey/不存在的key
              返回 {"msg":"","code":200}，没有泄露任何内部实现 ——
              说明这个接口本来可以做得更好。

        实测：HTTP 200，业务 code=500，
          {"msg":"Cannot invoke \\"com.ruoyi.common.core.domain.entity.SysUser.getRoles()\\"
                  because \\"sysUser\\" is null","code":500}
        """
        with allure.step("请求一个不存在的用户 userId=999999"):
            body = user_api.get_user(999999).json()

        with allure.step("校验响应里没有后端内部信息、且提示可读"):
            problems = _collect_problems(body)
            assert not problems, (
                "\n".join(problems) + "\n实际返回：" + _text_of(body)[:300]
            )

    # ================================================================
    # D7 —— 分页参数静默降级
    # ================================================================

    @allure.story("D7 分页参数静默降级")
    @allure.title("[D7] 分页参数传非数字应给出提示，而不是静默当成默认值")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.issue(REPORT_BASE + "缺陷报告-D7-分页参数静默降级.md", "D7 缺陷报告")
    @pytest.mark.p2
    @pytest.mark.xfail(
        reason="D7 未修复：分页参数被静默降级，和同模块 userId 的处理方式不一致",
        strict=False,
    )
    @pytest.mark.parametrize("page_num,page_size,desc", [
        ("abc", 10, "pageNum 传非数字"),
        (1, "abc", "pageSize 传非数字"),
    ])
    def test_d7_non_numeric_paging_should_warn(self, user_api, page_num, page_size, desc):
        """
        预期（来自缺陷报告 D7）：
          pageNum / pageSize 传非数字时应该给出明确的参数错误提示，和 userId 保持一致。

        依据：同一个模块 GET /system/user/abc 返回
          {"code":500,"msg":"请求参数类型不匹配，参数[userId]要求类型为：'java.lang.Long'，
                             但输入值为：'abc'"}
          —— 说明这个模块的策略是「非法参数给明确提示」，分页参数这里是漏了。

        实测：pageNum=abc 返回 HTTP 200 + code=200，静默按 pageNum=1 处理，
              没有任何提示。（影响 role / dict / config / post / operlog / job 六个列表接口）
        """
        allure.dynamic.title(f"[D7] {desc} 应给出提示")

        with allure.step(f"请求：pageNum={page_num}，pageSize={page_size}"):
            body = user_api.list_user(page_num, page_size).json()

        with allure.step("校验：不应静默当成默认值返回成功"):
            assert body.get("code") != 200, (
                f"{desc} 被静默当成默认值处理了（code=200），没有任何提示。\n"
                f"预期：返回明确的参数错误提示，和同模块 /system/user/abc 的处理方式一致。\n"
                f"实际返回：{_text_of(body)[:200]}"
            )

    @allure.story("D7 分页参数静默降级")
    @allure.title("[D7 对照] 正常的分页参数仍然要能正常返回")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.p2
    def test_d7_control_normal_paging_still_works(self, user_api):
        """
        对照用例：证明上面那条不是在要求「什么都报错」。
        合法的分页参数必须照常返回数据。
        """
        with allure.step("请求 pageNum=1，pageSize=10"):
            body = user_api.list_user(1, 10).json()

        with allure.step("校验正常返回"):
            assert body.get("code") == 200, f"正常分页参数反而报错了：{_text_of(body)[:200]}"
            assert "rows" in body, "正常返回里应该有 rows 字段"

    # ================================================================
    # D9 —— isAsc 未校验导致 SQL 与服务器路径泄露
    # ================================================================

    @allure.story("D9 排序参数未校验")
    @allure.title("[D9] isAsc 传非法值，响应不得泄露 SQL 语句和服务器路径")
    @allure.severity(allure.severity_level.BLOCKER)
    @allure.issue(REPORT_BASE + "缺陷报告-D9-isAsc未校验导致SQL信息泄露.md", "D9 缺陷报告")
    @pytest.mark.p1
    @pytest.mark.xfail(
        reason="D9 未修复：isAsc 未做枚举校验，非法值触发数据库异常并把内部信息返回给客户端",
        strict=False,
    )
    def test_d9_invalid_is_asc_no_leak(self, user_api):
        """
        预期（来自缺陷报告 D9）：
          isAsc 只应该接受 asc / desc，传其他值应返回能看懂的提示；
          不得泄露 SQL 语句、服务器路径、内部类名。

        依据：同一个接口的 orderByColumn 是有校验的 ——
              传 1,(select 1) 会返回「参数不符合规范，不能进行查询」，
              说明 isAsc 是漏了校验。

        实测：业务 code=500，响应体 1129 字符，含
              完整 SQL 语句 / 表名字段名 / 服务器本地路径 /
              jar 包名与内部类名 / Mapper 路径 / 数据库类型。
        """
        with allure.step("请求用户列表，isAsc 传非法值 xxx"):
            body = user_api.list_user(
                1, 10, orderByColumn="userName", isAsc="xxx"
            ).json()

        with allure.step("校验响应里没有 SQL 语句、服务器路径和内部类名"):
            problems = _collect_problems(body)
            assert not problems, (
                "\n".join(problems) + "\n实际返回：" + _text_of(body)[:300]
            )

    @allure.story("D9 排序参数未校验")
    @allure.title("[D9 对照] 合法的排序方向仍然要能正常返回")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.p2
    def test_d9_control_normal_sort_still_works(self, user_api):
        """对照用例：asc / desc / ASC 必须照常返回，不能被上面的修复要求误伤"""
        for value in ("asc", "desc", "ASC"):
            with allure.step(f"请求 isAsc={value}"):
                body = user_api.list_user(
                    1, 10, orderByColumn="userName", isAsc=value
                ).json()
            assert body.get("code") == 200, \
                f"isAsc={value} 应该正常返回，实际：{_text_of(body)[:200]}"

    @allure.story("D9 排序参数未校验")
    @allure.title("[D9 对照] orderByColumn 的注入仍应被拦截（这是 D9 预期的依据）")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.p2
    def test_d9_control_order_by_column_injection_blocked(self, user_api):
        """
        对照用例：同一个参数位置上，orderByColumn 的安全校验是有效的。
        这条通过，才能说明「isAsc 这里是漏了」，而不是「整个接口都不校验」。
        """
        with allure.step("请求 orderByColumn=1,(select 1)"):
            body = user_api.list_user(
                1, 10, orderByColumn="1,(select 1)", isAsc="asc"
            ).json()

        with allure.step("校验被拦截"):
            assert body.get("code") != 200, "注入载荷居然被放行了"
            assert "不符合规范" in str(body.get("msg") or ""), \
                f"拦截提示不符合预期：{_text_of(body)[:200]}"
