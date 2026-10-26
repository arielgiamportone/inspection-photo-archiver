import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from relative_links import (  # noqa: E402
    SuspiciousRepair,
    relative_link,
    repair,
    resolve_link,
    verify,
)


def touch(p: Path) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\xff\xd8 synthetic jpeg")
    return p


class TestRelativeLinks(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.line = self.base / "archive" / "LINE_A"
        self.ledger = self.line / "ledger.csv"
        self.photos = [touch(self.line / "202609" / "photos" / f"S{i:03d}_20260915.jpeg")
                       for i in range(10)]

    def tearDown(self):
        self.tmp.cleanup()

    def test_link_is_relative_to_the_ledger(self):
        self.assertEqual(relative_link(self.ledger, self.photos[0]),
                         "202609/photos/S000_20260915.jpeg")

    def test_relative_links_survive_moving_the_whole_tree(self):
        links = [relative_link(self.ledger, p) for p in self.photos]
        absolute = [str(p.resolve()) for p in self.photos]

        moved = self.base / "reorganised" / "reports" / "LINE_A"
        moved.parent.mkdir(parents=True)
        shutil.move(str(self.line), str(moved))
        new_ledger = moved / "ledger.csv"

        self.assertTrue(verify(new_ledger, links).ok)
        self.assertFalse(any(Path(a).is_file() for a in absolute))  # what used to happen

    def test_verify_resolves_instead_of_counting(self):
        links = [relative_link(self.ledger, p) for p in self.photos]
        self.photos[3].unlink()
        report = verify(self.ledger, links)
        self.assertEqual(report.resolved, 9)
        self.assertEqual(report.broken, [3])

    def test_repair_repoints_a_moved_file(self):
        links = [relative_link(self.ledger, p) for p in self.photos]
        flat = self.line / "202609" / "photos_flat"
        flat.mkdir()
        shutil.move(str(self.photos[2]), str(flat / self.photos[2].name))

        out = repair(self.ledger, links, self.line)
        self.assertEqual(out.repaired, [2])
        self.assertEqual(resolve_link(self.ledger, out.links[2]),
                         (flat / self.photos[2].name).resolve())
        self.assertTrue(verify(self.ledger, out.links).ok)

    def test_repair_does_not_guess_between_two_candidates(self):
        links = [relative_link(self.ledger, p) for p in self.photos]
        name = self.photos[1].name
        self.photos[1].unlink()
        touch(self.line / "x" / name)
        touch(self.line / "y" / name)
        out = repair(self.ledger, links, self.line)
        self.assertEqual(out.ambiguous, [1])
        self.assertEqual(out.links[1], links[1])

    def test_many_broken_links_abort_instead_of_rewriting(self):
        links = [relative_link(self.ledger, p) for p in self.photos]
        for p in self.photos[:5]:
            p.unlink()
        with self.assertRaises(SuspiciousRepair):
            repair(self.ledger, links, self.line)


if __name__ == "__main__":
    unittest.main()
