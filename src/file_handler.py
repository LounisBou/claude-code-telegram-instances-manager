from __future__ import annotations

import logging
import os
import shutil


class FileHandler:
    """Manage file uploads and session directories for Claude instances."""

    def __init__(self, base_dir: str = "/tmp/claude") -> None:
        """Initialize the file handler.

        Args:
            base_dir: Root directory under which per-session subdirectories
                are created.
        """
        self._base_dir = base_dir

    def _session_dir(self, project_name: str, session_id: int) -> str:
        """Build the path to a session's directory.

        Args:
            project_name: Name of the project owning the session.
            session_id: Numeric identifier of the session.

        Returns:
            Path to the session directory (may not exist yet).
        """
        return os.path.join(self._base_dir, f"{project_name}_{session_id}")

    def get_upload_dir(self, project_name: str, session_id: int) -> str:
        """Return the upload directory for a session, creating it if needed.

        Args:
            project_name: Name of the project owning the session.
            session_id: Numeric identifier of the session.

        Returns:
            Path to the existing upload directory.
        """
        d = self._session_dir(project_name, session_id)
        os.makedirs(d, exist_ok=True)
        return d

    def get_upload_path(
        self, project_name: str, session_id: int, filename: str
    ) -> str:
        """Return a unique file path for an upload, avoiding collisions.

        If a file with the given name already exists in the session
        directory, a numeric suffix is appended (e.g. ``photo_1.jpg``,
        ``photo_2.jpg``) until a free name is found.

        Args:
            project_name: Name of the project owning the session.
            session_id: Numeric identifier of the session.
            filename: Original name of the file being uploaded.

        Returns:
            Path where the uploaded file should be written.
        """
        upload_dir = self.get_upload_dir(project_name, session_id)
        path = os.path.join(upload_dir, filename)
        # Counter-based collision avoidance for repeated uploads of same filename
        if os.path.exists(path):
            base, ext = os.path.splitext(filename)
            counter = 1
            while os.path.exists(path):
                path = os.path.join(upload_dir, f"{base}_{counter}{ext}")
                counter += 1
        return path

    def cleanup_session(self, project_name: str, session_id: int) -> None:
        """Remove the session directory and all its contents.

        No-op if the directory does not exist.

        Args:
            project_name: Name of the project owning the session.
            session_id: Numeric identifier of the session.
        """
        d = self._session_dir(project_name, session_id)
        if os.path.isdir(d):
            shutil.rmtree(d)

    def file_exists(self, path: str) -> bool:
        """Check whether a regular file exists at the given path.

        Args:
            path: Absolute path to check.

        Returns:
            True if a regular file exists at the path, False otherwise.
        """
        return os.path.isfile(path)

    def get_file_size(self, path: str) -> int | None:
        """Return the size of a file in bytes, or None on failure.

        Args:
            path: Absolute path to the file.

        Returns:
            File size in bytes, or None if the file cannot be stat'd.
        """
        try:
            return os.path.getsize(path)
        except OSError:
            logging.getLogger(__name__).debug("Cannot stat file: %s", path)
            return None
