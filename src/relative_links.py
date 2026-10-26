"""Ledger links that survive moving the archive, and a repair that resolves.

The ledger stored an ABSOLUTE link per photo. Every reorganisation of the
folder tree moved the files and left the links behind, and nobody noticed
until someone clicked: it broke three times.

Two ideas fix it:

1. Store the path RELATIVE TO THE LEDGER FILE. Move the whole tree, ledger
   included, and every link still resolves.
2. Verify by RESOLVING each link to a file on disk, never by counting rows
   that "have a link". Counting is what approved a broken repair once.

`repair` re-points broken links by finding the file under the archive, and
refuses to guess: a name found twice is reported, not picked. If most links
fail at once it aborts, because that almost always means the archive is not
mounted or not synced, not that the files moved.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath


class SuspiciousRepair(RuntimeError):
    """Too many links failed at once to trust a repair."""


def relative_link(ledger_file: str | Path, photo: str | Path) -> str:
    rel = os.path.relpath(Path(photo).resolve(), Path(ledger_file).resolve().parent)
    return PurePosixPath(*Path(rel).parts).as_posix()


def resolve_link(ledger_file: str | Path, link: str) -> Path:
    return (Path(ledger_file).resolve().parent / Path(*PurePosixPath(link).parts)).resolve()


@dataclass
class VerifyReport:
    resolved: int = 0
    broken: list[int] = field(default_factory=list)  # row indexes

    @property
    def ok(self) -> bool:
        return not self.broken


def verify(ledger_file: str | Path, links: list[str]) -> VerifyReport:
    report = VerifyReport()
    for i, link in enumerate(links):
        if link and resolve_link(ledger_file, link).is_file():
            report.resolved += 1
        else:
            report.broken.append(i)
    return report


@dataclass
class RepairReport:
    links: list[str]
    repaired: list[int] = field(default_factory=list)
    not_found: list[int] = field(default_factory=list)
    ambiguous: list[int] = field(default_factory=list)


def repair(ledger_file: str | Path, links: list[str], archive_root: str | Path,
           max_broken_ratio: float = 0.30) -> RepairReport:
    broken = verify(ledger_file, links).broken
    if links and len(broken) / len(links) > max_broken_ratio:
        raise SuspiciousRepair(
            f"{len(broken)} of {len(links)} links are broken (> {max_broken_ratio:.0%}). "
            "Is the archive mounted and synced? Refusing to rewrite.")

    by_name: dict[str, list[Path]] = {}
    for p in Path(archive_root).rglob("*"):
        if p.is_file():
            by_name.setdefault(p.name, []).append(p)

    out = RepairReport(links=list(links))
    for i in broken:
        name = PurePosixPath(links[i]).name
        found = by_name.get(name, [])
        if len(found) == 1:
            out.links[i] = relative_link(ledger_file, found[0])
            out.repaired.append(i)
        elif found:
            out.ambiguous.append(i)
        else:
            out.not_found.append(i)
    return out
