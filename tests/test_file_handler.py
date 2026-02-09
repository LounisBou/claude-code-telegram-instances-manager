from __future__ import annotations

import os

import pytest

from src.file_handler import FileHandler


class TestFileHandler:
    def test_get_upload_dir_creates_directory(self, tmp_path):
        handler = FileHandler(base_dir=str(tmp_path))
        upload_dir = handler.get_upload_dir("my-project", 1)
        assert os.path.isdir(upload_dir)
        assert "my-project" in upload_dir
        assert "1" in upload_dir

    def test_get_upload_path(self, tmp_path):
        handler = FileHandler(base_dir=str(tmp_path))
        path = handler.get_upload_path("my-project", 1, "photo.jpg")
        assert path.endswith("photo.jpg")
        assert os.path.isdir(os.path.dirname(path))

    def test_cleanup_session_files(self, tmp_path):
        handler = FileHandler(base_dir=str(tmp_path))
        upload_dir = handler.get_upload_dir("proj", 1)
        test_file = os.path.join(upload_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test")
        assert os.path.exists(test_file)
        handler.cleanup_session(project_name="proj", session_id=1)
        assert not os.path.exists(upload_dir)

    def test_cleanup_nonexistent_session(self, tmp_path):
        handler = FileHandler(base_dir=str(tmp_path))
        # Should not raise
        handler.cleanup_session(project_name="nope", session_id=99)

    def test_unique_filenames(self, tmp_path):
        handler = FileHandler(base_dir=str(tmp_path))
        path1 = handler.get_upload_path("proj", 1, "file.txt")
        with open(path1, "w") as f:
            f.write("first")
        path2 = handler.get_upload_path("proj", 1, "file.txt")
        assert path1 != path2

    def test_file_exists_check(self, tmp_path):
        handler = FileHandler(base_dir=str(tmp_path))
        assert handler.file_exists("/nonexistent/file.txt") is False
        real_file = tmp_path / "real.txt"
        real_file.write_text("content")
        assert handler.file_exists(str(real_file)) is True

    def test_get_file_size(self, tmp_path):
        handler = FileHandler(base_dir=str(tmp_path))
        f = tmp_path / "sized.txt"
        f.write_text("hello")
        assert handler.get_file_size(str(f)) == 5
        assert handler.get_file_size("/nonexistent") is None
