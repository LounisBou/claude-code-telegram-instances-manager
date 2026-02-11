from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.log_setup import TRACE

logger = logging.getLogger(__name__)


@dataclass
class Project:
    """A discovered project with its display name and absolute path."""

    name: str
    path: str


def scan_projects(root: str, depth: int = 1) -> list[Project]:
    """Scan a directory for projects containing .git or .claude markers."""
    root_path = Path(root)
    logger.debug("Scanning projects root=%s depth=%d", root, depth)
    if not root_path.is_dir():
        logger.debug("Root path does not exist: %s", root)
        return []

    projects = []
    for entry in root_path.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            logger.log(TRACE, "Skipping %s (not dir or hidden)", entry.name)
            continue
        if (entry / ".git").exists() or (entry / ".claude").exists():
            resolved = str(entry.resolve())
            logger.log(TRACE, "Found project %s at %s", entry.name, resolved)
            projects.append(Project(name=entry.name, path=resolved))
        else:
            logger.log(TRACE, "Skipping %s (no .git or .claude)", entry.name)

    projects.sort(key=lambda p: p.name)
    logger.debug("Found %d projects in %s", len(projects), root)
    return projects
