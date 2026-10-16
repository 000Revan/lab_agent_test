import pytest

from utils.test_data_util import unique_name


@pytest.fixture(scope="function")
def unique_equipment_name():
    """生成不会与已有设备冲突的名称。"""
    return unique_name("auto_equipment")


@pytest.fixture(scope="function")
def not_exists_equipment_id(db):
    """生成当前 equipments 表中不存在的设备 ID。"""
    result = db.query_one(
        "SELECT COALESCE(MAX(id), 0) + 10000 AS equipment_id FROM equipments"
    )
    return result["equipment_id"]


@pytest.fixture(scope="function")
def not_exists_equipment_lab_id(db):
    """生成当前 labs 表中不存在的实验室 ID。"""
    result = db.query_one("SELECT COALESCE(MAX(id), 0) + 10000 AS lab_id FROM labs")
    return result["lab_id"]


@pytest.fixture(scope="function")
def query_equipment(db):
    """根据设备 ID，或实验室 ID 与名称查询数据库记录。"""

    def query(*, equipment_id=None, lab_id=None, name=None):
        if equipment_id is not None:
            if lab_id is not None or name is not None:
                raise ValueError("按 equipment_id 查询时不能再传入 lab_id 或 name")
            return db.query_one(
                "SELECT * FROM equipments WHERE id = %s LIMIT 1",
                (equipment_id,),
            )

        if lab_id is None or name is None:
            raise ValueError("按名称查询设备时必须同时传入 lab_id 和 name")
        return db.query_one(
            """
            SELECT *
            FROM equipments
            WHERE lab_id = %s AND name = %s
            LIMIT 1
            """,
            (lab_id, name),
        )

    return query


@pytest.fixture(scope="function")
def delete_test_equipment_by_identity(db, temp_lab):
    """登记接口可能创建的设备，并在用例结束后兜底清理。"""
    identities = []

    def register(lab_id, name):
        identities.append((lab_id, name))

    yield register

    for lab_id, name in reversed(identities):
        db.execute(
            "DELETE FROM equipments WHERE lab_id = %s AND name = %s",
            (lab_id, name),
        )
