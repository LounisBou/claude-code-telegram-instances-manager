from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Project:
    name: str
    path: str


def scan_projects(root: str, depth: int = 1) -> list[Project]:
    root_path = Path(root)
    if not root_path.is_dir():
        return []

    projects = []
    for entry in root_path.iterdir():
        if not entry.is_dir() or entry.name.startswith("."):
            continue
        if (entry / ".git").exists() or (entry / ".claude").exists():
            projects.append(Project(name=entry.name, path=str(entry.resolve())))

    projects.sort(key=lambda p: p.name)
    return projects
