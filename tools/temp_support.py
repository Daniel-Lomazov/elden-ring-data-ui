from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from uuid import uuid4


ROOT = Path(__file__).resolve().parent.parent


def ensure_temp_root(name: str) -> Path:
    root = ROOT / ".cache" / str(name or "temp")
    root.mkdir(parents=True, exist_ok=True)
    return root


@contextmanager
def temporary_env_root(root: Path | str) -> Iterator[Path]:
    target = Path(root)
    target.mkdir(parents=True, exist_ok=True)

    previous_tmp = os.environ.get("TMP")
    previous_temp = os.environ.get("TEMP")
    previous_tempdir = tempfile.tempdir

    os.environ["TMP"] = str(target)
    os.environ["TEMP"] = str(target)
    tempfile.tempdir = str(target)
    try:
        yield target
    finally:
        if previous_tmp is None:
            os.environ.pop("TMP", None)
        else:
            os.environ["TMP"] = previous_tmp
        if previous_temp is None:
            os.environ.pop("TEMP", None)
        else:
            os.environ["TEMP"] = previous_temp
        tempfile.tempdir = previous_tempdir


@contextmanager
def patched_temporary_directory_cleanup() -> Iterator[None]:
    original_cleanup = tempfile.TemporaryDirectory._cleanup.__func__

    def _patched_temp_cleanup(cls, name, warn_message, ignore_errors=False):
        try:
            return original_cleanup(cls, name, warn_message, True)
        except PermissionError:
            return None

    tempfile.TemporaryDirectory._cleanup = classmethod(_patched_temp_cleanup)
    try:
        yield
    finally:
        tempfile.TemporaryDirectory._cleanup = classmethod(original_cleanup)


def make_temp_workspace(name: str, *, prefix: str = "tmp") -> Path:
    root = ensure_temp_root(name)
    while True:
        candidate = root / f"{prefix}{uuid4().hex}"
        try:
            candidate.mkdir(parents=True, exist_ok=False)
            return candidate
        except FileExistsError:
            continue


def cleanup_tree(path: Path | str) -> None:
    shutil.rmtree(Path(path), ignore_errors=True)
