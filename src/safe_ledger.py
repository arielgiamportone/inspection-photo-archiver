"""A cumulative ledger that can never be emptied by a failed read.

The ledger maps every archived photo back to its source URL. It only grows,
so the dangerous moment is loading it: the original code recreated it empty
whenever the read failed or the header looked unfamiliar, and saved that.

Here a load can only end in one of four ways:

    new        no file yet; start empty (nothing is written until save)
    loaded     header matches; use as is
    migrated   legacy header recognised; rename columns, keep every row,
               back up the original first
    reset      unknown format WITH data; back up first, then start empty

and an unreadable file (locked by a spreadsheet app, a cloud placeholder not
yet downloaded) is retried and then ABORTS. It is never treated as empty.
"""
from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

COLUMNS = ("source_url", "file_name", "path", "job_id", "field")

# Header of the previous tool, mapped onto today's columns.
LEGACY_HEADER_MAP = {
    "Original URL": "source_url",
    "New Name": "file_name",
    "Destination": "path",
    "Job": "job_id",
    "Field": "field",
}


class LedgerUnreadable(RuntimeError):
    """The file exists but could not be read. The caller must abort, not reset."""


@dataclass
class LoadResult:
    rows: list[dict]
    action: str
    backup: Path | None = None
    warnings: list[str] = field(default_factory=list)


def _read_csv(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def _read_with_retries(path, reader, attempts, wait, sleep):
    last = None
    for i in range(attempts):
        try:
            return reader(path)
        except (OSError, csv.Error, UnicodeDecodeError) as exc:
            last = exc
            if i < attempts - 1:
                sleep(wait)
    raise LedgerUnreadable(
        f"{path} exists but could not be read after {attempts} attempts: {last!r}. "
        "Refusing to continue: an empty ledger would overwrite the history.")


def _backup(path: Path, tag: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    dest = path.with_name(f"{path.stem}_BACKUP_{tag}_{stamp}{path.suffix}")
    dest.write_bytes(path.read_bytes())
    return dest


def load_ledger(
    path: str | Path,
    columns: tuple[str, ...] = COLUMNS,
    legacy_map: dict[str, str] = LEGACY_HEADER_MAP,
    attempts: int = 4,
    wait: float = 2.0,
    reader: Callable = _read_csv,
    sleep: Callable[[float], None] = time.sleep,
) -> LoadResult:
    path = Path(path)
    if not path.exists():
        return LoadResult(rows=[], action="new")

    header, rows = _read_with_retries(path, reader, attempts, wait, sleep)

    if set(columns) <= set(header):
        return LoadResult(rows=[{c: r.get(c, "") for c in columns} for r in rows],
                          action="loaded")

    renamed = [legacy_map.get(h, h) for h in header]
    if set(columns) <= set(renamed):
        backup = _backup(path, "legacy_format")
        migrated = [{legacy_map.get(k, k): v for k, v in r.items()} for r in rows]
        migrated = [{c: r.get(c, "") for c in columns} for r in migrated]
        save_ledger(path, migrated, columns)
        return LoadResult(rows=migrated, action="migrated", backup=backup)

    if not rows:
        return LoadResult(rows=[], action="reset",
                          warnings=[f"unknown header {header}, file had no rows"])

    backup = _backup(path, "incompatible_format")
    return LoadResult(rows=[], action="reset", backup=backup,
                      warnings=[f"unknown header {header}; {len(rows)} rows kept in {backup.name}"])


def save_ledger(path: str | Path, rows: list[dict], columns: tuple[str, ...] = COLUMNS) -> None:
    """Write atomically: a crash mid-write leaves the previous file intact."""
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(columns))
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def append_records(path: str | Path, new_rows: list[dict], **load_kw) -> int:
    """Load (safely), append, save. Returns the ledger size after the append."""
    result = load_ledger(path, **load_kw)
    rows = result.rows + [{c: r.get(c, "") for c in COLUMNS} for r in new_rows]
    save_ledger(path, rows)
    return len(rows)
