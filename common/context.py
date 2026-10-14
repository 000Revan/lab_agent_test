# 测试上下文管理，保存 token、业务 id、临时变量等
class TestContext:
    """测试上下文管理，用于保存全局变量、模块变量和临时变量。"""

    def __init__(self):
        # 全局变量
        self.global_data = {}
        # 模块变量
        self.module_data = {}
        # 临时变量
        self.temp_data = {}

    # 全局变量操作
    def set_global(self, key, value):
        """设置全局变量"""
        self.global_data[key] = value

    def get_global(self, key):
        """获取全局变量"""
        return self.global_data.get(key)

    def clear_global(self):
        """清空全局变量。"""
        self.global_data.clear()

    # 模块变量操作
    def set_module(self, key, value):
        """设置模块变量"""
        self.module_data[key] = value

    def get_module(self, key):
        """获取模块变量"""
        return self.module_data.get(key)

    def clear_module(self):
        """清空模块变量"""
        self.module_data.clear()

    # 临时变量操作

    def set_temp(self, key, value):
        """设置临时变量"""
        self.temp_data[key] = value

    def get_temp(self, key):
        """获取临时变量"""
        return self.temp_data.get(key)

    def clear_temp(self):
        """清空临时变量"""
        self.temp_data.clear()
