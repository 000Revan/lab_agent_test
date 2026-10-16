import base64
from pathlib import Path

import pytest


UPLOAD_CONTENT = {
    "png": base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zl9sAAAAASUVORK5CYII="
    ),
    "pdf": (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog >>\nendobj\n"
        b"trailer\n<< /Root 1 0 R >>\n%%EOF\n"
    ),
    "exe": b"MZ test executable content",
}


@pytest.fixture(scope="function")
def upload_file_factory(tmp_path):
    """根据 YAML 文件描述构造 multipart 参数，并管理临时文件流。"""
    opened_streams = []

    def build(file_spec):
        if file_spec is None:
            return {
                "files": None,
                "filename": None,
                "content": None,
                "size": 0,
            }

        filename = file_spec["filename"]
        content_type = file_spec.get(
            "content_type",
            "application/octet-stream",
        )
        size_bytes = file_spec.get("size_bytes")

        if size_bytes is not None:
            file_path = tmp_path / Path(filename).name
            with file_path.open("wb") as file_writer:
                file_writer.truncate(size_bytes)
            content = file_path.open("rb")
            opened_streams.append(content)
        else:
            content = UPLOAD_CONTENT[file_spec["content_kind"]]

        return {
            "files": {"file": (filename, content, content_type)},
            "filename": filename,
            "content": content if isinstance(content, bytes) else None,
            "size": size_bytes if size_bytes is not None else len(content),
        }

    yield build

    for stream in opened_streams:
        stream.close()


@pytest.fixture(scope="function")
def uploaded_file_cleanup(env_config):
    """登记本次测试上传的服务端文件，并在用例结束后安全删除。"""
    upload_dir_value = env_config.get("upload_dir")
    if not upload_dir_value:
        raise KeyError("当前环境缺少 upload_dir 配置，无法清理上传测试文件")

    upload_dir = Path(upload_dir_value).resolve()
    if not upload_dir.is_dir():
        raise FileNotFoundError(f"上传目录不存在：{upload_dir}")

    uploaded_paths = []

    def register(disk_name):
        if not disk_name or Path(disk_name).name != disk_name:
            raise ValueError(f"服务端返回的 disk_name 不安全：{disk_name!r}")

        target = (upload_dir / disk_name).resolve()
        try:
            target.relative_to(upload_dir)
        except ValueError as exc:
            raise ValueError(f"上传文件超出配置目录：{target}") from exc
        uploaded_paths.append(target)

    yield register

    for target in reversed(uploaded_paths):
        target.unlink(missing_ok=True)
