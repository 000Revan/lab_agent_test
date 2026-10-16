from datetime import date, timedelta

import pytest

from utils.test_data_util import (
    create_test_equipment,
    create_test_lab,
    create_test_reservation,
    delete_test_equipment,
    delete_test_lab,
    delete_test_reservation,
    unique_name,
)


@pytest.fixture(scope="function")
def reservation_dates():
    """提供不依赖硬编码日期的预约测试日期。"""
    today = date.today()
    return {
        "yesterday": str(today - timedelta(days=1)),
        "tomorrow": str(today + timedelta(days=1)),
        "day_after_tomorrow": str(today + timedelta(days=2)),
    }


@pytest.fixture(scope="function")
def closed_lab(db):
    """创建已关闭实验室。"""
    lab = create_test_lab(
        db=db,
        name=unique_name("closed_lab"),
        open_time="08:00",
        close_time="18:00",
        status=0,
    )
    yield lab
    delete_test_lab(db, lab_id=lab["id"])


@pytest.fixture(scope="function")
def maintenance_equipment(db, temp_lab):
    """创建处于维护状态的设备。"""
    equipment = create_test_equipment(
        db=db,
        lab_id=temp_lab["id"],
        name=unique_name("maintenance_equipment"),
        status=0,
    )
    yield equipment
    delete_test_equipment(db, equipment_id=equipment["id"])


@pytest.fixture(scope="function")
def other_lab_equipment(db):
    """创建另一实验室及其设备，用于校验设备归属。"""
    lab = create_test_lab(db=db, name=unique_name("other_lab"))
    equipment = create_test_equipment(
        db=db,
        lab_id=lab["id"],
        name=unique_name("other_lab_equipment"),
    )
    yield {"lab": lab, "equipment": equipment}
    delete_test_equipment(db, equipment_id=equipment["id"])
    delete_test_lab(db, lab_id=lab["id"])


@pytest.fixture(scope="function")
def not_exists_reservation_lab_id(db):
    """生成当前 labs 表中不存在的实验室 ID。"""
    result = db.query_one("SELECT COALESCE(MAX(id), 0) + 10000 AS lab_id FROM labs")
    return result["lab_id"]


@pytest.fixture(scope="function")
def not_exists_reservation_equipment_id(db):
    """生成当前 equipments 表中不存在的设备 ID。"""
    result = db.query_one(
        "SELECT COALESCE(MAX(id), 0) + 10000 AS equipment_id FROM equipments"
    )
    return result["equipment_id"]


@pytest.fixture(scope="function")
def query_reservation(db):
    """根据预约 ID 或预约业务字段查询数据库记录。"""

    def query(
        *,
        reservation_id=None,
        user_id=None,
        lab_id=None,
        equipment_id=None,
        reserve_date=None,
        start_time=None,
        end_time=None,
    ):
        if reservation_id is not None:
            return db.query_one(
                "SELECT * FROM reservations WHERE id = %s LIMIT 1",
                (reservation_id,),
            )

        required = (user_id, lab_id, reserve_date, start_time, end_time)
        if any(value is None for value in required):
            raise ValueError("按业务字段查询预约时缺少必要参数")
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
            (
                user_id,
                lab_id,
                equipment_id,
                reserve_date,
                start_time,
                end_time,
            ),
        )

    return query


@pytest.fixture(scope="function")
def delete_api_reservations(db, temp_equipment):
    """登记接口可能创建的预约，并在设备和实验室清理前删除。"""
    identities = []

    def register(identity):
        identities.append(identity)

    yield register

    for item in reversed(identities):
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
            item,
        )


def _create_reservation_fixture(
    db,
    prepared_accounts,
    temp_lab,
    reservation_dates,
    *,
    status,
    start_time="09:00",
    end_time="10:00",
):
    """创建指定状态的当前普通用户预约。"""
    return create_test_reservation(
        db=db,
        user_id=prepared_accounts["user"]["id"],
        lab_id=temp_lab["id"],
        reserve_date=reservation_dates["tomorrow"],
        start_time=start_time,
        end_time=end_time,
        status=status,
    )


@pytest.fixture(scope="function")
def pending_reservation(db, prepared_accounts, temp_lab, reservation_dates):
    """创建当前普通用户的待审核预约。"""
    reservation = _create_reservation_fixture(
        db,
        prepared_accounts,
        temp_lab,
        reservation_dates,
        status=0,
    )
    yield reservation
    delete_test_reservation(db, reservation_id=reservation["id"])


@pytest.fixture(scope="function")
def approved_reservation(db, prepared_accounts, temp_lab, reservation_dates):
    """创建当前普通用户的已通过预约。"""
    reservation = _create_reservation_fixture(
        db,
        prepared_accounts,
        temp_lab,
        reservation_dates,
        status=1,
    )
    yield reservation
    delete_test_reservation(db, reservation_id=reservation["id"])


@pytest.fixture(scope="function")
def conflict_reservation(db, prepared_accounts, temp_lab, reservation_dates):
    """创建用于时间冲突校验的待审核预约。"""
    reservation = _create_reservation_fixture(
        db,
        prepared_accounts,
        temp_lab,
        reservation_dates,
        status=0,
    )
    yield reservation
    delete_test_reservation(db, reservation_id=reservation["id"])


@pytest.fixture(scope="function")
def reservation_list_records(
    db,
    prepared_accounts,
    temp_user_account,
    temp_lab,
    reservation_dates,
):
    """创建两个不同用户的预约，用于校验列表数据权限。"""
    current_user_reservation = create_test_reservation(
        db=db,
        user_id=prepared_accounts["user"]["id"],
        lab_id=temp_lab["id"],
        reserve_date=reservation_dates["tomorrow"],
        start_time="10:00",
        end_time="11:00",
    )
    other_user_reservation = create_test_reservation(
        db=db,
        user_id=temp_user_account["id"],
        lab_id=temp_lab["id"],
        reserve_date=reservation_dates["tomorrow"],
        start_time="11:00",
        end_time="12:00",
    )
    records = {
        "current": current_user_reservation,
        "other": other_user_reservation,
    }
    yield records
    delete_test_reservation(db, reservation_id=current_user_reservation["id"])
    delete_test_reservation(db, reservation_id=other_user_reservation["id"])
