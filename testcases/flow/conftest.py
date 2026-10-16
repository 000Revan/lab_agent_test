from datetime import date, timedelta

import pytest

from common.request_client import RequestClient


@pytest.fixture(scope="function")
def flow_api_factory(env_config, api_path, api_classes):
    """按运行时 token 创建 Flow 专用 API 对象，并统一关闭临时客户端。"""
    clients = []

    def create(module, token):
        if module not in api_classes:
            raise ValueError(f"不支持的API模块: {module}")

        client = RequestClient(
            base_url=env_config["base_url"],
            timeout=env_config.get("timeout", 10),
        )
        client.set_token(token)
        clients.append(client)
        return api_classes[module](client, api_path)

    yield create

    for client in clients:
        client.close()


@pytest.fixture(scope="function")
def flow_resource_registry(db):
    """登记 Flow 通过接口创建的资源，异常时按设备、实验室逆序兜底清理。"""
    resources = {"equipment_ids": [], "lab_ids": []}
    yield resources

    for equipment_id in reversed(resources["equipment_ids"]):
        db.execute("DELETE FROM equipments WHERE id = %s", (equipment_id,))
    for lab_id in reversed(resources["lab_ids"]):
        db.execute("DELETE FROM labs WHERE id = %s", (lab_id,))


@pytest.fixture(scope="function")
def flow_reservation_registry(db, temp_user_account, temp_equipment):
    """登记接口创建的预约，并确保在用户、设备和实验室清理前删除。"""
    identities = []
    yield identities.append

    for identity in reversed(identities):
        db.execute(
            """
            DELETE FROM reservations
            WHERE user_id = %s
              AND lab_id = %s
              AND equipment_id <=> %s
              AND date = %s
              AND start_time = %s
              AND end_time = %s
            """,
            identity,
        )


@pytest.fixture(scope="function")
def query_flow_reservation(db):
    """按本次 Flow 的业务唯一字段查询预约。"""

    def query(identity):
        return db.query_one(
            """
            SELECT *
            FROM reservations
            WHERE user_id = %s
              AND lab_id = %s
              AND equipment_id <=> %s
              AND date = %s
              AND start_time = %s
              AND end_time = %s
            ORDER BY id DESC
            LIMIT 1
            """,
            identity,
        )

    return query


@pytest.fixture(scope="function")
def flow_reservation_date():
    """提供不会依赖固定日历日期的预约日期。"""
    return str(date.today() + timedelta(days=1))
