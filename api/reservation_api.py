# 预约创建、列表、取消、审核接口封装

from api.base_api import BaseApi


class ReservationApi(BaseApi):
    module = "reservation"

    def create(self, payload):
        """用户创建预约"""
        return self.request("create", json=payload)

    def list(self, params=None):
        """查询预约列表"""
        return self.request("list", params=params)

    def cancel(self, reservation_id):
        """用户取消预约"""
        return self.request(
            "cancel",
            path_params={"reservation_id": reservation_id},
        )

    def audit(self, reservation_id, payload):
        """管理员审核预约"""
        return self.request(
            "audit",
            path_params={"reservation_id": reservation_id},
            json=payload,
        )
