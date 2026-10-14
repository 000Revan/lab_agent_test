class BaseApi:
    module = None

    def __init__(self, client, api_path):
        self.client = client
        self.api_path = api_path

    def get_api_config(self, name):
        """获取接口配置"""
        if not self.module:
            raise ValueError("API子类必须定义 module")
        try:
            return self.api_path[self.module][name]
        except KeyError as e:
            raise KeyError(f"接口配置不存在: {self.module}.{name}") from e

    def get_path(self, name, **path_params):
        """获取接口路径，并替换路径参数。"""
        path = self.get_api_config(name)["path"]
        return path.format(**path_params)

    def request(self, name, path_params=None, **kwargs):
        """按 api_paths.yaml 配置发送请求。"""
        path_params = path_params or {}

        api_config = self.get_api_config(name)
        method = api_config["method"].upper()
        path = self.get_path(name, **path_params)

        return self.client.request(method, path, **kwargs)
