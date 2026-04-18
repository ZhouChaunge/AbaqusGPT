"""
Manifest Tracker | 清单追踪
=============================

Track all generated output files.
追踪所有生成的输出文件。
"""

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class ManifestEntry:
    """A single entry in the manifest | 清单中的单条记录"""
    timestamp: str
    skill: str
    file_path: str
    stage: str
    description: str
    checksum: str = ""
    size: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "skill": self.skill,
            "file_path": self.file_path,
            "stage": self.stage,
            "description": self.description,
            "checksum": self.checksum,
            "size": self.size,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ManifestEntry":
        """Create from dictionary."""
        return cls(**data)


class ManifestTracker:
    """
    Track all generated output files.
    追踪所有生成的输出文件。

    Inspired by ARIS output-manifest protocol.
    灵感来自 ARIS 的 output-manifest 协议。

    Creates and maintains MANIFEST.md with:
    | Timestamp | Skill | File | Stage | Description |

    Usage | 用法:
    ```python
    tracker = ManifestTracker("project/")

    # Record an output
    tracker.record(
        skill="converge-doctor",
        file_path="diagnosis-stage/DIAGNOSIS_REPORT.md",
        stage="diagnosis",
        description="收敛问题诊断报告"
    )

    # Query by stage
    entries = tracker.query(stage="diagnosis")

    # Query by skill
    entries = tracker.query(skill="converge-doctor")
    ```
    """

    MANIFEST_FILE = "MANIFEST.md"
    MANIFEST_JSON = ".manifest.json"

    def __init__(self, project_dir: str | Path):
        """
        Initialize manifest tracker.

        Args:
            project_dir: Project root directory
        """
        self.project_dir = Path(project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)

        self._entries: List[ManifestEntry] = []
        self._load()

    @property
    def manifest_md_path(self) -> Path:
        """Path to MANIFEST.md"""
        return self.project_dir / self.MANIFEST_FILE

    @property
    def manifest_json_path(self) -> Path:
        """Path to .manifest.json"""
        return self.project_dir / self.MANIFEST_JSON

    def _load(self) -> None:
        """Load existing manifest."""
        if self.manifest_json_path.exists():
            try:
                data = json.loads(self.manifest_json_path.read_text(encoding="utf-8"))
                self._entries = [ManifestEntry.from_dict(e) for e in data.get("entries", [])]
            except (json.JSONDecodeError, KeyError):
                self._entries = []

    def _save(self) -> None:
        """Save manifest to both JSON and Markdown."""
        # Save JSON (for programmatic access)
        json_data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "entries": [e.to_dict() for e in self._entries],
        }
        self.manifest_json_path.write_text(
            json.dumps(json_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        # Save Markdown (for human reading)
        self._write_markdown()

    def _write_markdown(self) -> None:
        """Write MANIFEST.md file."""
        lines = [
            "# Output Manifest | 输出清单",
            "",
            "Auto-generated tracking of all output files.",
            "所有输出文件的自动生成追踪。",
            "",
            f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "| Timestamp | Skill | File | Stage | Description |",
            "|-----------|-------|------|-------|-------------|",
        ]

        # Add entries (most recent first)
        for entry in sorted(self._entries, key=lambda e: e.timestamp, reverse=True):
            lines.append(
                f"| {entry.timestamp} | {entry.skill} | `{entry.file_path}` | {entry.stage} | {entry.description} |"
            )

        lines.extend([
            "",
            "---",
            "",
            "## Statistics | 统计",
            "",
            f"- Total files: {len(self._entries)}",
            f"- Unique skills: {len(set(e.skill for e in self._entries))}",
            f"- Unique stages: {len(set(e.stage for e in self._entries))}",
        ])

        # Stage breakdown
        stages = {}
        for entry in self._entries:
            stages[entry.stage] = stages.get(entry.stage, 0) + 1

        if stages:
            lines.extend([
                "",
                "### By Stage | 按阶段",
                "",
            ])
            for stage, count in sorted(stages.items()):
                lines.append(f"- {stage}: {count} files")

        self.manifest_md_path.write_text("\n".join(lines), encoding="utf-8")

    def record(
        self,
        skill: str,
        file_path: str,
        stage: str,
        description: str,
    ) -> ManifestEntry:
        """
        Record a new output file.
        记录新的输出文件。

        Args:
            skill: Skill that generated the output
            file_path: Path to the output file (relative to project)
            stage: Workflow stage (e.g., "diagnosis", "modeling")
            description: Brief description of the output

        Returns:
            Created manifest entry
        """
        # Get file info
        full_path = self.project_dir / file_path
        size = full_path.stat().st_size if full_path.exists() else 0

        # Calculate checksum (MD5)
        checksum = ""
        if full_path.exists():
            import hashlib
            checksum = hashlib.md5(full_path.read_bytes(), usedforsecurity=False).hexdigest()[:8]  # nosec B324

        entry = ManifestEntry(
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M"),
            skill=skill,
            file_path=file_path,
            stage=stage,
            description=description,
            checksum=checksum,
            size=size,
        )

        self._entries.append(entry)
        self._save()

        return entry

    def query(
        self,
        skill: Optional[str] = None,
        stage: Optional[str] = None,
        limit: int = 100,
    ) -> List[ManifestEntry]:
        """
        Query manifest entries.
        查询清单条目。

        Args:
            skill: Filter by skill name
            stage: Filter by stage
            limit: Maximum entries to return

        Returns:
            List of matching entries
        """
        results = self._entries

        if skill:
            results = [e for e in results if e.skill == skill]

        if stage:
            results = [e for e in results if e.stage == stage]

        # Sort by timestamp (most recent first)
        results = sorted(results, key=lambda e: e.timestamp, reverse=True)

        return results[:limit]

    def get_by_file(self, file_path: str) -> Optional[ManifestEntry]:
        """Get entry by file path."""
        for entry in self._entries:
            if entry.file_path == file_path:
                return entry
        return None

    def remove(self, file_path: str) -> bool:
        """Remove entry by file path."""
        for i, entry in enumerate(self._entries):
            if entry.file_path == file_path:
                del self._entries[i]
                self._save()
                return True
        return False

    def clear(self) -> None:
        """Clear all entries."""
        self._entries = []
        self._save()

    def get_stats(self) -> dict:
        """Get manifest statistics."""
        skills = {}
        stages = {}
        total_size = 0

        for entry in self._entries:
            skills[entry.skill] = skills.get(entry.skill, 0) + 1
            stages[entry.stage] = stages.get(entry.stage, 0) + 1
            total_size += entry.size

        return {
            "total_files": len(self._entries),
            "total_size_bytes": total_size,
            "skills": skills,
            "stages": stages,
        }
