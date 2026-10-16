"""
接口层 —— 登录模块

分层的意义：
  用例层（test_login.py）只关心"测什么"，不关心"怎么发请求"
  接口层（这个文件）只关心"路径是什么、参数叫什么"
  一旦接口变了，只改这里，所有用例自动跟着变
"""
from common.request_util import RequestUtil


class LoginApi:
    def __init__(self, client: RequestUtil):
        self.client = client

    def login(self, username: str, password: str, code: str = "", uuid: str = ""):
        """
        登录

        ⚠️ 若依默认开启验证码。自动化测试前需要在
           「系统管理 → 参数设置」把 sys.account.captchaEnabled 改成 false，
           然后重启后端（或清 Redis 缓存），否则登录会一直失败。
        """
        return self.client.post("/login", json={
            "username": username,
            "password": password,
            "code": code,
            "uuid": uuid,
        })

    def logout(self):
        return self.client.post("/logout")

    def get_info(self):
        """获取当前登录用户信息（含权限、角色）"""
        return self.client.get("/getInfo")

    def get_routers(self):
        """获取当前用户的动态菜单路由"""
        return self.client.get("/getRouters")
