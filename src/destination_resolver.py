"""Find where a photo belongs when its folder may live in a later month.

Archive layout:   {root}/{YYYY}/{MM}/{site_code}/photos/

A site's folder is created when its inspection record is written up, which is
the month of the visit OR LATER, never earlier. Looking the folder up only in
the photo's own month sent late write-ups to the error folder while the run
reported "0 errors".

Resolution order for one photo:
    1. the folder in the photo's own month, if it exists
    2. the EARLIEST folder of that site at or after the photo's month
    3. {root}/{YYYY}/{MM}/_ERRORS of the photo's month: a genuine signal that
       the write-up does not exist yet

Same site, visits months apart: each photo finds its own visit, because
rule 2 takes the first folder after the photo, not the newest.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

PHOTOS = "photos"
ERRORS = "_ERRORS"

Month = tuple[int, int]


@dataclass(frozen=True)
class Resolution:
    folder: Path
    reason: str  # "same_month" | "later_month" | "errors"


def build_index(root: str | Path) -> dict[str, list[tuple[Month, Path]]]:
    """One scan of the archive: site code -> every (year, month) folder it has, ascending."""
    root = Path(root)
    index: dict[str, list[tuple[Month, Path]]] = {}
    for year_dir in root.iterdir():
        if not (year_dir.is_dir() and year_dir.name.isdigit() and len(year_dir.name) == 4):
            continue
        for month_dir in year_dir.iterdir():
            if not (month_dir.is_dir() and month_dir.name[:2].isdigit()):
                continue
            month = (int(year_dir.name), int(month_dir.name[:2]))
            for site_dir in month_dir.iterdir():
                photos = site_dir / PHOTOS
                if site_dir.name != ERRORS and photos.is_dir():
                    index.setdefault(site_dir.name, []).append((month, photos))
    for entries in index.values():
        entries.sort()
    return index


def resolve(index: dict[str, list[tuple[Month, Path]]], root: str | Path,
            site_code: str, photo_date: date) -> Resolution:
    target: Month = (photo_date.year, photo_date.month)
    for month, folder in index.get(site_code, []):
        if month == target:
            return Resolution(folder, "same_month")
        if month > target:
            return Resolution(folder, "later_month")
    errors = Path(root) / f"{photo_date.year:04d}" / f"{photo_date.month:02d}" / ERRORS
    return Resolution(errors, "errors")
