import pytest

from utils.test_data_util import unique_name


@pytest.fixture(scope="function")
def unique_lab_name():
    """生成不会与已有实验室冲突的名称。"""
    return unique_name("auto_lab")


@pytest.fixture(scope="function")
def not_exists_lab_id(db):
    """生成当前 labs 表中不存在的实验室 ID。"""
    result = db.query_one("SELECT COALESCE(MAX(id), 0) + 10000 AS lab_id FROM labs")
    return result["lab_id"]


@pytest.fixture(scope="function")
def query_lab(db):
    """根据实验室 ID 或名称查询数据库记录。"""

    def query(*, lab_id=None, name=None):
        if (lab_id is None) == (name is None):
            raise ValueError("lab_id 和 name 必须且只能传入一个")

        condition = "id" if lab_id is not None else "name"
        value = lab_id if lab_id is not None else name
        return db.query_one(
            f"SELECT * FROM labs WHERE {condition} = %s LIMIT 1",
            (value,),
        )

    return query


@pytest.fixture(scope="function")
def delete_test_lab_by_name(db):
    """登记由接口创建的实验室名称，并在用例结束后兜底清理。"""
    names = []

    def register(name):
        names.append(name)

    yield register

    for name in reversed(names):
        db.execute("DELETE FROM labs WHERE name = %s", (name,))
