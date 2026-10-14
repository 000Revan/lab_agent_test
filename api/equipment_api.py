# 设备列表、新增、修改、删除接口封装

from api.base_api import BaseApi


class EquipmentApi(BaseApi):
    module = "equipment"

    def list(self, params=None):
        """查询设备列表"""
        return self.request("list", params=params)

    def create(self, payload):
        """管理员新增设备"""
        return self.request("create", json=payload)

    def update(self, equipment_id, payload):
        """管理员修改设备"""
        return self.request(
            "update",
            path_params={"equipment_id": equipment_id},
            json=payload,
        )

    def delete(self, equipment_id):
        """管理员删除设备"""
        return self.request("delete", path_params={"equipment_id": equipment_id})
