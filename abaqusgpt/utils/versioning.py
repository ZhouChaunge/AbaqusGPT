"""
Output Versioning | 输出版本控制
==================================

Version control for output files.
输出文件的版本控制。
"""

import shutil
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


class OutputVersioner:
    """
    Version control for output files.
    输出文件的版本控制。

    Inspired by ARIS output-versioning protocol.
    灵感来自 ARIS 的 output-versioning 协议。

    Pattern | 模式:
    - Write timestamped: FILENAME_YYYYMMDD_HHmmss.md
    - Also write fixed name: FILENAME.md (latest version)
    - Downstream always reads fixed name

    Usage | 用法:
    ```python
    versioner = OutputVersioner("output/")

    # Write with versioning
    versioner.write("DIAGNOSIS_REPORT.md", content)
    # Creates:
    #   output/DIAGNOSIS_REPORT.md (latest)
    #   output/DIAGNOSIS_REPORT_20260418_143022.md (timestamped)

    # Read latest
    content = versioner.read("DIAGNOSIS_REPORT.md")

    # List versions
    versions = versioner.list_versions("DIAGNOSIS_REPORT.md")
    ```
    """

    def __init__(
        self,
        output_dir: str | Path,
        max_versions: int = 10,
    ):
        """
        Initialize output versioner.

        Args:
            output_dir: Directory for output files
            max_versions: Maximum versions to keep per file
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.max_versions = max_versions

    def write(
        self,
        filename: str,
        content: str,
        encoding: str = "utf-8",
    ) -> Tuple[Path, Path]:
        """
        Write content with versioning.
        写入内容并进行版本控制。

        Args:
            filename: Output filename
            content: Content to write
            encoding: File encoding

        Returns:
            Tuple of (latest_path, versioned_path)
        """
        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Parse filename
        stem = Path(filename).stem
        suffix = Path(filename).suffix

        # Create versioned filename
        versioned_name = f"{stem}_{timestamp}{suffix}"

        # Paths
        latest_path = self.output_dir / filename
        versioned_path = self.output_dir / versioned_name

        # Write both files
        versioned_path.write_text(content, encoding=encoding)
        latest_path.write_text(content, encoding=encoding)

        # Cleanup old versions
        self._cleanup_old_versions(filename)

        return latest_path, versioned_path

    def read(
        self,
        filename: str,
        version: Optional[str] = None,
        encoding: str = "utf-8",
    ) -> str:
        """
        Read file content.
        读取文件内容。

        Args:
            filename: Filename to read
            version: Specific version timestamp (None = latest)
            encoding: File encoding

        Returns:
            File content
        """
        if version:
            stem = Path(filename).stem
            suffix = Path(filename).suffix
            path = self.output_dir / f"{stem}_{version}{suffix}"
        else:
            path = self.output_dir / filename

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        return path.read_text(encoding=encoding)

    def list_versions(self, filename: str) -> List[dict]:
        """
        List all versions of a file.
        列出文件的所有版本。

        Args:
            filename: Base filename

        Returns:
            List of version info dicts
        """
        stem = Path(filename).stem
        suffix = Path(filename).suffix

        versions = []
        pattern = f"{stem}_*{suffix}"

        for path in sorted(self.output_dir.glob(pattern), reverse=True):
            # Extract timestamp from filename
            name = path.stem
            timestamp_str = name.replace(f"{stem}_", "")

            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                versions.append({
                    "path": str(path),
                    "filename": path.name,
                    "timestamp": timestamp.isoformat(),
                    "timestamp_str": timestamp_str,
                    "size": path.stat().st_size,
                })
            except ValueError:
                # Not a valid timestamp format
                continue

        return versions

    def restore(self, filename: str, version: str) -> Path:
        """
        Restore a specific version as the latest.
        将特定版本恢复为最新版本。

        Args:
            filename: Base filename
            version: Version timestamp to restore

        Returns:
            Path to restored file
        """
        stem = Path(filename).stem
        suffix = Path(filename).suffix

        source = self.output_dir / f"{stem}_{version}{suffix}"
        dest = self.output_dir / filename

        if not source.exists():
            raise FileNotFoundError(f"Version not found: {source}")

        shutil.copy2(source, dest)
        return dest

    def _cleanup_old_versions(self, filename: str) -> int:
        """
        Remove old versions exceeding max_versions.
        删除超过 max_versions 的旧版本。

        Returns:
            Number of files removed
        """
        versions = self.list_versions(filename)

        if len(versions) <= self.max_versions:
            return 0

        # Remove oldest versions
        to_remove = versions[self.max_versions:]
        removed = 0

        for version in to_remove:
            path = Path(version["path"])
            if path.exists():
                path.unlink()
                removed += 1

        return removed

    def get_latest_version(self, filename: str) -> Optional[dict]:
        """
        Get the latest version info.
        获取最新版本信息。
        """
        versions = self.list_versions(filename)
        return versions[0] if versions else None

    def diff_versions(
        self,
        filename: str,
        version1: str,
        version2: str,
    ) -> dict:
        """
        Compare two versions of a file.
        比较文件的两个版本。

        Args:
            filename: Base filename
            version1: First version timestamp
            version2: Second version timestamp

        Returns:
            Diff info dictionary
        """
        content1 = self.read(filename, version1)
        content2 = self.read(filename, version2)

        import difflib

        diff = list(difflib.unified_diff(
            content1.splitlines(),
            content2.splitlines(),
            fromfile=f"{filename}@{version1}",
            tofile=f"{filename}@{version2}",
            lineterm="",
        ))

        return {
            "version1": version1,
            "version2": version2,
            "diff": "\n".join(diff),
            "lines_changed": len([line for line in diff if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]),
        }
