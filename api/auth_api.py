# 登录、注册接口封装
from api.base_api import BaseApi


class AuthApi(BaseApi):
    module = "auth"

    def login(self, payload):
        """用户登录"""
        return self.request("login", json=payload)

    def register(self, payload):
        """用户注册"""
        return self.request("register", json=payload)
