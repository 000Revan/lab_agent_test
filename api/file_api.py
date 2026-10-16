# 文件上传接口封装

from api.base_api import BaseApi


class FileApi(BaseApi):
    module = "files"

    def upload(self, files=None, data=None, **kwargs):
        """上传文件"""
        return self.request("upload", files=files, data=data, **kwargs)

    def access(self, filename):
        """访问已上传文件。"""
        return self.request(
            "access",
            path_params={"filename": filename},
        )
