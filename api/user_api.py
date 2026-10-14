# 用户信息、用户管理、修改密码等接口封装

from api.base_api import BaseApi


class UserApi(BaseApi):
    module = "user"

    def info(self):
        """获取当前登录用户信息"""
        return self.request("info")

    def update(self, payload):
        """修改当前登录用户信息"""
        return self.request("update", json=payload)

    def password(self, payload):
        """修改当前用户登录密码"""
        return self.request("password", json=payload)

    def list(self, params=None):
        """管理员查询用户列表"""
        return self.request("list", params=params)

    def create(self, payload):
        """管理员新增用户"""
        return self.request("create", json=payload)

    def update_by_id(self, user_id, payload):
        """管理员修改指定用户"""
        return self.request(
            "update_by_id", path_params={"user_id": user_id}, json=payload
        )

    def delete(self, user_id):
        """管理员删除指定用户"""
        return self.request("delete", path_params={"user_id": user_id})
