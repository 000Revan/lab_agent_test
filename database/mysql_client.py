# MySQL 客户端封装，负责查询、执行、批量执行、关闭连接
import pymysql
from pymysql.cursors import DictCursor


class MySQLClient:
    def __init__(self, db_config):
        self.db_config = db_config
        self.conn = None

    def connect(self):
        self.conn = pymysql.connect(
            host=self.db_config["host"],
            port=int(self.db_config.get("port", 3306)),
            user=self.db_config["user"],
            password=str(self.db_config["password"]),
            database=self.db_config["database"],
            charset=self.db_config.get("charset", "utf8mb4"),
            cursorclass=DictCursor,
            autocommit=True,
        )
        return self

    def _ensure_connected(self):
        """检测数据库是否连接"""
        if not self.conn:
            raise RuntimeError("数据库未连接，请先调用 connect()")

    def query_one(self, sql, params=None):
        """查询单条数据"""
        self._ensure_connected()
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone()

    def query_all(self, sql, params=None):
        """查询多条数据"""
        self._ensure_connected()
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def execute(self, sql, params=None):
        """执行单挑增删改SQL"""
        self._ensure_connected()
        try:
            with self.conn.cursor() as cursor:
                row_count = cursor.execute(sql, params)
            self.conn.commit()
            return row_count
        except Exception:
            self.conn.rollback()
            raise

    def execute_many(self, sql, params_list=None):
        """批量执行SQL"""
        self._ensure_connected()
        try:
            with self.conn.cursor() as cursor:
                row_count = cursor.executemany(sql, params_list)
            self.conn.commit()
            return row_count
        except Exception:
            self.conn.rollback()
            raise

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
