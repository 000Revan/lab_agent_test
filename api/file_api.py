# 文件上传接口封装

from api.base_api import BaseApi


class FileApi(BaseApi):
    module = "files"

    def upload(self, files, data=None):
        """上传文件"""
        return self.request("upload", files=files, data=data)
