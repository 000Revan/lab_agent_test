# requests 二次封装，统一处理 base_url、headers、token、日志、超时

import time

import requests
from common.logger import get_logger, safe_log_data

logger = get_logger("request_client")


class RequestClient:
    def __init__(self, base_url, timeout=10, headers=None):
        if not base_url:
            raise ValueError("base_url不能为空")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

        default_headers = {"Accept": "application/json"}
        if headers:
            default_headers.update(headers)
        self.session.headers.update(default_headers)

    def set_token(self, token, token_type="Bearer"):
        """请求头内添加token"""
        if not token:
            raise ValueError("token不能为空")
        self.session.headers.update({"Authorization": f"{token_type} {token}"})

    def clear_token(self):
        """清理token"""
        self.session.headers.pop("Authorization", None)

    def _build_url(self, path):
        """构建请求URL"""
        if path.startswith(("http://", "https://")):
            return path
        return self.base_url.rstrip("/") + "/" + path.lstrip("/")

    def request(self, method, path, **kwargs):
        method = method.upper()
        url = self._build_url(path)

        # 如果kwargs没有timeout参数，则设置timeout参数为默认参数
        kwargs.setdefault("timeout", self.timeout)

        # 拷贝请求头，防止直接修改session原始headers
        headers = dict(self.session.headers)
        # pop(key,默认值)：取出key对应的值，并删除key
        headers.update(kwargs.pop("headers", {}) or {})
        kwargs["headers"] = headers

        log_kwargs = {
            key: value for key, value in kwargs.items() if key not in ("headers",)
        }

        logger.info(f"请求方法：{method}")
        logger.info(f"请求URL：{url}")
        logger.info(f"请求头：{safe_log_data(headers)}")
        logger.info(f"请求参数：{safe_log_data(log_kwargs)}")

        start_time = time.time()

        try:
            response = self.session.request(method, url, **kwargs)
        except requests.RequestException as e:
            logger.error(f"请求异常：{method} {url}, error={e}")
            raise

        elapsed = round(time.time() - start_time, 3)
        logger.info(f"响应状态码：{response.status_code}")
        logger.info(f"响应耗时：{elapsed}s")
        logger.info(f"响应内容：{safe_log_data(self._get_response_log_data(response))}")
        return response

    @staticmethod
    def _get_response_log_data(response):
        """获取适合日志打印的响应内容。"""
        try:
            return response.json()
        except ValueError:
            return response.text[:1000]

    def get(self, path, **kwargs):
        return self.request("GET", path, **kwargs)

    def post(self, path, **kwargs):
        return self.request("POST", path, **kwargs)

    def put(self, path, **kwargs):
        return self.request("PUT", path, **kwargs)

    def patch(self, path, **kwargs):
        return self.request("PATCH", path, **kwargs)

    def delete(self, path, **kwargs):
        return self.request("DELETE", path, **kwargs)

    def close(self):
        self.session.close()
