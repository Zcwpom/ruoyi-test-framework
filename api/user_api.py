"""接口层 —— 用户管理模块"""
from common.request_util import RequestUtil


class UserApi:
    def __init__(self, client: RequestUtil):
        self.client = client

    # ---------- 查询 ----------

    def list_user(self, page_num: int = 1, page_size: int = 10, **filters):
        """
        查询用户列表（分页）

        :param filters: userName / phonenumber / status / deptId 等
        """
        params = {"pageNum": page_num, "pageSize": page_size}
        params.update(filters)
        return self.client.get("/system/user/list", params=params)

    def get_user(self, user_id: int):
        """根据 ID 查用户详情"""
        return self.client.get(f"/system/user/{user_id}")

    # ---------- 增删改 ----------

    def add_user(self, **data):
        """
        新增用户

        必填：userName, nickName, password
        常用：phonenumber, email, sex, status, deptId, roleIds, postIds
        """
        return self.client.post("/system/user", json=data)

    def update_user(self, **data):
        """修改用户（必须带 userId）"""
        return self.client.put("/system/user", json=data)

    def delete_user(self, *user_ids):
        """删除用户，支持批量：delete_user(1, 2, 3)"""
        ids = ",".join(str(i) for i in user_ids)
        return self.client.delete(f"/system/user/{ids}")

    # ---------- 辅助 ----------

    def find_user_by_name(self, user_name: str):
        """按用户名查，返回第一条或 None（常用于清理测试数据）"""
        body = self.list_user(1, 100, userName=user_name).json()
        rows = body.get("rows") or []
        return rows[0] if rows else None
