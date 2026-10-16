"""用户管理模块接口测试"""
import allure
import pytest

from common.yaml_util import read_yaml, render_data

# 测试数据（数据驱动：改数据不用改代码）
USER_DATA = read_yaml("data/user_data.yaml")


@allure.epic("若依权限管理系统")
@allure.feature("用户管理")
class TestUserQuery:
    """用户查询 —— 正常流 + 分页边界"""

    @allure.story("用户列表查询")
    @allure.title("默认分页查询用户列表")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.smoke
    @pytest.mark.p0
    def test_list_default(self, client, user_api):
        """默认分页查询"""
        with allure.step("调用用户列表接口（第 1 页，每页 10 条）"):
            resp = user_api.list_user(1, 10)
            body = client.assert_ok(resp, "查询用户列表")

        with allure.step("校验总数大于 0"):
            assert body["total"] > 0, "用户总数为 0，环境可能有问题"

        with allure.step("校验返回条数不超过 pageSize"):
            assert len(body["rows"]) <= 10, "返回条数超过了 pageSize"

    @allure.story("用户列表查询")
    @allure.title("用户列表返回字段完整性校验")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.p1
    def test_list_fields(self, client, user_api):
        """返回字段完整性校验（接口测试的常见考点）"""
        with allure.step("查询 1 条用户记录"):
            body = client.assert_ok(user_api.list_user(1, 1), "查询用户列表")
            row = body["rows"][0]

        with allure.step("逐个校验关键字段存在"):
            for field in ["userId", "userName", "nickName", "status", "createTime"]:
                assert field in row, f"返回结果缺字段：{field}"

    @allure.story("分页边界")
    @allure.title("分页参数边界值不应导致服务异常")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.p1
    @pytest.mark.parametrize("page_num,page_size,desc", [
        (0,     10,    "页码为 0"),
        (-1,    10,    "页码为负数"),
        (1,     0,     "每页 0 条"),
        (1,     -5,    "每页负数"),
        (99999, 10,    "页码远超数据量"),
        (1,     99999, "每页条数超大"),
    ])
    def test_list_paging_boundary(self, client, user_api, page_num, page_size, desc):
        """
        分页参数边界 —— 不应返回 500
        ★ 这类用例最容易发现真 bug：开发常常忘了校验负数
        """
        allure.dynamic.title(f"分页边界 - {desc}")

        with allure.step(f"使用异常分页参数 pageNum={page_num}, pageSize={page_size}"):
            resp = user_api.list_user(page_num, page_size)

        with allure.step("校验 HTTP 层未崩溃"):
            assert resp.status_code == 200, f"【{desc}】HTTP 异常：{resp.status_code}"

        with allure.step("校验业务层未报错"):
            body = resp.json()
            assert body["code"] == 200, \
                f"【{desc}】业务异常：{body.get('msg')}（参数没做边界校验）"

    @allure.story("用户列表查询")
    @allure.title("按用户名模糊查询")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.p1
    def test_list_filter_by_name(self, client, user_api):
        """按用户名模糊查询"""
        with allure.step("以 userName=admin 做模糊查询"):
            body = client.assert_ok(user_api.list_user(1, 10, userName="admin"), "模糊查询")

        with allure.step("校验结果匹配"):
            assert body["total"] >= 1
            assert "admin" in body["rows"][0]["userName"]

    @allure.story("用户列表查询")
    @allure.title("查询不存在的用户应返回空列表而非报错")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.p2
    def test_list_filter_no_result(self, client, user_api):
        """查询不存在的用户 —— 应返回空列表而不是报错"""
        with allure.step("查询一个不存在的用户名"):
            body = client.assert_ok(
                user_api.list_user(1, 10, userName="definitely_not_exist_xyz"),
                "空结果查询",
            )

        with allure.step("校验返回空列表且 code 正常"):
            assert body["total"] == 0
            assert body["rows"] == []


@allure.epic("若依权限管理系统")
@allure.feature("用户管理")
class TestUserCrud:
    """
    用户增删改

    ★ 设计原则一：每条用例自成闭环（self-contained）
      用例自己造数据、自己校验、自己清理，**不依赖其他用例的执行结果**。
      否则单独执行会失败、执行顺序变化会影响结果，测试就不可信了。

    ★ 设计原则二：所有唯一性字段都要唯一化
      若依 sys_user 对 userName / phonenumber / email 都有唯一约束。
      fake_user fixture 一次性生成三个都唯一的成套数据。
    """

    # ---------------- 新增 ----------------

    @allure.story("新增用户")
    @allure.title("新增用户 - 正常数据")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.p0
    def test_add_user_success(self, client, user_api, fake_user, data_cleanup):
        """新增用户：正常数据"""
        data_cleanup.append(fake_user["userName"])      # 结束后自动清理

        with allure.step("调用新增用户接口"):
            client.assert_ok(user_api.add_user(**fake_user), "新增用户")

        with allure.step("回查确认数据已落库"):
            # ★ 接口返回成功 ≠ 数据真的写进去了，必须回查
            found = user_api.find_user_by_name(fake_user["userName"])
            assert found is not None, f"接口返回成功，但查不到用户 {fake_user['userName']}"

        with allure.step("校验关键字段与提交值一致"):
            assert found["nickName"] == fake_user["nickName"]
            assert found["phonenumber"] == fake_user["phonenumber"]

    @allure.story("新增用户")
    @allure.title("新增用户 - 参数校验（数据驱动）")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.p1
    @pytest.mark.parametrize("case", USER_DATA["add_user"], ids=lambda c: c["desc"])
    def test_add_user_data_driven(self, client, user_api, uniq, uniq_num,
                                  data_cleanup, case, request):
        """
        新增用户：数据驱动

        {uniq} / {uniq_num} 会被替换成唯一值 —— 这是防止数据污染的关键。
        没有唯一化，重复执行会撞唯一约束并返回 500，
        让本该 xfail 的用例变成 xpass（假通过）。
        """
        data = render_data(case["data"], uniq=uniq, uniq_num=uniq_num)

        # 注册清理标识。
        # ★ 优先用唯一后缀 {uniq}，而不是完整的 userName ——
        #   因为接口可能改写输入值（实测：userName 里的 <script> 会被剥掉），
        #   用完整 userName 去查就查不到，脏数据会留在库里。
        #   {uniq} 这段不会被改写，用它查一定能匹配上。
        if data.get("userName"):
            key = uniq if (uniq and uniq in str(data["userName"])) else data["userName"]
            data_cleanup.append(key)

        if case.get("xfail"):
            request.node.add_marker(
                pytest.mark.xfail(reason=case.get("xfail_reason", ""), strict=False)
            )

        with allure.step(f"提交新增用户请求：{case['desc']}"):
            body = user_api.add_user(**data).json()

        with allure.step(f"校验业务码为 {case['expect_code']}"):
            assert body["code"] == case["expect_code"], \
                f"【{case['desc']}】期望 code={case['expect_code']}，" \
                f"实际 {body['code']} - {body.get('msg')}"

    # ---------------- 修改 ----------------

    @allure.story("修改用户")
    @allure.title("修改用户昵称并校验生效")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.p1
    def test_update_user(self, client, user_api, fake_user, data_cleanup):
        """修改用户昵称（用例自己造前置数据）"""
        data_cleanup.append(fake_user["userName"])

        with allure.step("前置：新增一个用户"):
            client.assert_ok(user_api.add_user(**fake_user), "前置：新增用户")
            uid = user_api.find_user_by_name(fake_user["userName"])["userId"]

        with allure.step("调用修改接口，把昵称改为「改名后的昵称」"):
            client.assert_ok(
                user_api.update_user(
                    userId=uid,
                    userName=fake_user["userName"],
                    nickName="改名后的昵称",
                ),
                "修改用户",
            )

        with allure.step("回查确认昵称已更新"):
            after = user_api.get_user(uid).json()
            assert after["data"]["nickName"] == "改名后的昵称"

    # ---------------- 删除 ----------------

    @allure.story("删除用户")
    @allure.title("删除用户并校验已不存在")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.p2
    def test_delete_user(self, client, user_api, fake_user):
        """删除用户（用例自己造数据、自己删、自己验证）"""
        with allure.step("前置：新增一个用户"):
            client.assert_ok(user_api.add_user(**fake_user), "前置：新增用户")
            uid = user_api.find_user_by_name(fake_user["userName"])["userId"]

        with allure.step("调用删除接口"):
            client.assert_ok(user_api.delete_user(uid), "删除用户")

        with allure.step("回查确认用户已不存在"):
            assert user_api.find_user_by_name(fake_user["userName"]) is None, \
                "删除后仍能查到该用户"

    @allure.story("删除用户")
    @allure.title("删除当前登录用户必须被拒绝")
    @allure.severity(allure.severity_level.BLOCKER)
    @pytest.mark.p0
    def test_delete_current_user_should_fail(self, client, user_api):
        """
        异常流：删除当前登录用户（admin）必须被拒绝

        ★ 实测发现：若依的保护规则是「不能删除当前登录用户」，
          文案为 "当前用户不能删除"；而不是「不能删除超级管理员」。
          这是两条不同的规则 —— 意味着换个管理员来删 admin 可能就删掉了。

        断言只验证「行为被拒绝」，不写死文案 —— 文案变化不应导致用例失败。
        """
        with allure.step("查询 admin 的 userId"):
            admin = user_api.find_user_by_name("admin")
            assert admin is not None, "找不到 admin，环境异常"

        with allure.step("尝试删除 admin"):
            body = user_api.delete_user(admin["userId"]).json()

        with allure.step("校验操作被拒绝且有提示"):
            assert body["code"] != 200, "竟然允许删除当前登录用户！这是严重缺陷"
            assert body.get("msg"), "被拒绝了但没有给出原因，用户体验差"

    @allure.story("权限边界")
    @allure.title("[跟进] 换管理员删除 admin 是否可行（危险，默认跳过）")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.p2
    def test_admin_can_be_deleted_by_another_admin(self, client, user_api):
        """
        跟进测试：若依的保护规则是「不能删自己」而非「不能删超管」。
        那么换一个管理员账号，是否就能删掉 admin？

        ★ 这条用例的价值在于：验证的是「保护规则是否足够」，
          而不只是「功能是否报错」。

        ⚠️ 危险操作，默认跳过。确认环境可恢复后再手动开启。
        """
        pytest.skip("危险操作：会删除 admin，需要可恢复的环境才执行")
