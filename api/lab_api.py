# 实验室列表、详情、新增、修改、删除接口封装
from api.base_api import BaseApi


class LabApi(BaseApi):
    module = "lab"

    def list_lab(self, params=None):
        """查询实验室列表"""
        return self.request("list", params=params)

    def detail(self, lab_id):
        """查询实验室详情"""
        return self.request("detail", path_params={"lab_id": lab_id})

    def create(self, payload):
        """管理员新增实验室"""
        return self.request("create", json=payload)

    def update(self, lab_id, payload):
        """管理员修改实验室"""
        return self.request("update", path_params={"lab_id": lab_id}, json=payload)

    def delete(self, lab_id):
        """管理员删除实验室"""
        return self.request("delete", path_params={"lab_id": lab_id})
