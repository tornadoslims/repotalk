"""Walk file tree, filter by extension, respect exclude patterns."""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path

from salt_doc_gen.config import Config

logger = logging.getLogger(__name__)


def crawl(root: Path, config: Config) -> list[Path]:
    """Discover all files matching config filters under root.

    Returns sorted list of absolute paths.
    """
    root = root.resolve()
    if not root.is_dir():
        raise ValueError(f"Not a directory: {root}")

    extensions = set(config.processing.file_extensions)
    exclude = config.processing.exclude_patterns
    skip_tiny = config.processing.skip_tiny_files
    threshold = config.processing.tiny_file_threshold

    matched: list[Path] = []

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        if path.suffix not in extensions:
            continue

        rel = str(path.relative_to(root))
        if _is_excluded(rel, exclude):
            logger.debug("Excluded: %s", rel)
            continue

        if skip_tiny:
            try:
                line_count = path.read_text(errors="replace").count("\n")
                if line_count < threshold:
                    logger.debug("Skipped tiny file (%d lines): %s", line_count, rel)
                    continue
            except OSError:
                continue

        matched.append(path)

    logger.info("Crawled %s: found %d files", root, len(matched))
    return matched


def _is_excluded(relative_path: str, patterns: list[str]) -> bool:
    """Check if a relative path matches any exclude pattern."""
    for pattern in patterns:
        if fnmatch.fnmatch(relative_path, pattern):
            return True
        # Also check each path component for directory-level patterns
        if fnmatch.fnmatch(f"/{relative_path}", pattern):
            return True
        # Handle **/ prefix patterns
        if pattern.startswith("**/"):
            suffix_pattern = pattern[3:]
            if fnmatch.fnmatch(relative_path, suffix_pattern):
                return True
            # Check against each sub-path
            parts = relative_path.split("/")
            for i in range(len(parts)):
                sub = "/".join(parts[i:])
                if fnmatch.fnmatch(sub, suffix_pattern):
                    return True
    return False
