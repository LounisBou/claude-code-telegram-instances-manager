from __future__ import annotations

import os
import shutil


class FileHandler:
    def __init__(self, base_dir: str = "/tmp/claude") -> None:
        self._base_dir = base_dir

    def _session_dir(self, project_name: str, session_id: int) -> str:
        return os.path.join(self._base_dir, f"{project_name}_{session_id}")

    def get_upload_dir(self, project_name: str, session_id: int) -> str:
        d = self._session_dir(project_name, session_id)
        os.makedirs(d, exist_ok=True)
        return d

    def get_upload_path(
        self, project_name: str, session_id: int, filename: str
    ) -> str:
        upload_dir = self.get_upload_dir(project_name, session_id)
        path = os.path.join(upload_dir, filename)
        if os.path.exists(path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(path):
                path = os.path.join(upload_dir, f"{base}_{counter}{ext}")
                counter += 1
        return path

    def cleanup_session(self, project_name: str, session_id: int) -> None:
        d = self._session_dir(project_name, session_id)
        if os.path.isdir(d):
            shutil.rmtree(d)

    def file_exists(self, path: str) -> bool:
        return os.path.isfile(path)

    def get_file_size(self, path: str) -> int | None:
        try:
            return os.path.getsize(path)
        except OSError:
            return None
