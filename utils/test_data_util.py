# 前置造数据工具类
import uuid
from datetime import date, timedelta

from utils.password_util import hash_password


def unique_name(prefix):
    """生成唯一测试名称，避免重复执行时冲突。"""
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def create_test_user(
    db,
    username=None,
    password="123456",
    name="临时测试用户",
    role="student",
    status=1,
    email=None,
    phone=None,
):
    """创建临时测试用户，返回用户信息。"""
    username = username or unique_name("temp_user")
    password_hash = hash_password(str(password))

    db.execute(
        """
        INSERT INTO users (
            username,
            password,
            name,
            role,
            email,
            phone,
            status,
            create_time,
            update_time
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """,
        (username, password_hash, name, role, email, phone, status),
    )

    user = db.query_one(
        "SELECT id, username, name, role, status FROM users WHERE username = %s LIMIT 1",
        (username,),
    )

    return {
        **user,
        "password": password,
    }


def delete_test_user(db, user_id=None, username=None):
    """删除临时测试用户。"""
    if user_id is not None:
        return db.execute("DELETE FROM users WHERE id = %s", (user_id,))

    if username is not None:
        return db.execute("DELETE FROM users WHERE username = %s", (username,))

    raise ValueError("删除测试用户时 user_id 和 username 至少传一个")


def create_test_lab(
    db,
    name=None,
    location="自动化测试楼 A101",
    capacity=30,
    open_time="09:00",
    close_time="18:00",
    description="自动化测试实验室",
    img=None,
    status=1,
):
    """创建临时测试实验室，返回实验室信息。"""
    name = name or unique_name("temp_lab")

    db.execute(
        """
        INSERT INTO labs (
            name,
            location,
            capacity,
            open_time,
            close_time,
            description,
            img,
            status,
            create_time,
            update_time
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """,
        (name, location, capacity, open_time, close_time, description, img, status),
    )

    return db.query_one(
        "SELECT * FROM labs WHERE name = %s LIMIT 1",
        (name,),
    )


def delete_test_lab(db, lab_id):
    """删除临时测试实验室。"""
    return db.execute("DELETE FROM labs WHERE id = %s", (lab_id,))


def create_test_equipment(
    db,
    lab_id,
    name=None,
    description="自动化测试设备",
    img=None,
    spec="AUTO-SPEC",
    quantity=1,
    status=1,
):
    """创建临时测试设备，返回设备信息。"""
    name = name or unique_name("temp_equipment")

    db.execute(
        """
        INSERT INTO equipments (
            lab_id,
            name,
            description,
            img,
            spec,
            quantity,
            status,
            create_time,
            update_time
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """,
        (lab_id, name, description, img, spec, quantity, status),
    )

    return db.query_one(
        "SELECT * FROM equipments WHERE name = %s LIMIT 1",
        (name,),
    )


def delete_test_equipment(db, equipment_id):
    """删除临时测试设备。"""
    return db.execute("DELETE FROM equipments WHERE id = %s", (equipment_id,))


def create_test_reservation(
    db,
    user_id,
    lab_id,
    equipment_id=None,
    reserve_date=None,
    start_time="09:00",
    end_time="10:00",
    remark="自动化测试预约",
    status=0,
):
    """创建临时测试预约，返回预约信息。"""
    reserve_date = reserve_date or str(date.today() + timedelta(days=1))

    db.execute(
        """
        INSERT INTO reservations (
            user_id,
            lab_id,
            equipment_id,
            date,
            start_time,
            end_time,
            remark,
            status,
            create_time,
            update_time
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
        """,
        (
            user_id,
            lab_id,
            equipment_id,
            reserve_date,
            start_time,
            end_time,
            remark,
            status,
        ),
    )

    return db.query_one(
        """
        SELECT *
        FROM reservations
        WHERE user_id = %s
          AND lab_id = %s
          AND date = %s
          AND start_time = %s
          AND end_time = %s
        ORDER BY id DESC
        LIMIT 1
        """,
        (user_id, lab_id, reserve_date, start_time, end_time),
    )


def delete_test_reservation(db, reservation_id):
    """删除临时测试预约。"""
    return db.execute("DELETE FROM reservations WHERE id = %s", (reservation_id,))
