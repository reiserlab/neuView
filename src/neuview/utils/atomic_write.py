"""Context manager for atomic file writes."""

import os
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Union


@contextmanager
def atomic_write(
    path: Union[str, Path],
    mode: str = "w",
    encoding: Optional[str] = "utf-8",
):
    """Write a file atomically via tempfile + ``os.replace``.

    Yields a writable file handle pointing at a temp file in the same
    directory as ``path``. On clean exit, the temp file is atomically renamed
    onto ``path`` — concurrent readers either see the previous content or the
    new content, never a partial write. On any exception inside the ``with``
    block (or from ``os.replace`` itself), the temp file is removed and the
    original exception propagates.

    The temp file is created in ``path.parent`` so the rename stays on the
    same filesystem (a precondition for atomicity). Use ``mode="wb"`` and
    pass ``encoding=None`` for binary writes.
    """
    target = Path(path)
    fd, tmp_path = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    try:
        with os.fdopen(fd, mode, encoding=encoding) as f:
            yield f
        os.replace(tmp_path, target)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise
