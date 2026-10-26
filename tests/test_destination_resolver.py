import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from destination_resolver import build_index, resolve  # noqa: E402


class TestDestinationResolver(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        # Synthetic archive: which months each site has a write-up folder in.
        for year, month, site in [
            (2026, 3, "S100"),             # visited and written up in March
            (2026, 4, "S200"),             # visited in March, written up late
            (2026, 3, "S300"), (2026, 8, "S300"),   # two visits, months apart
            (2025, 12, "S400"), (2026, 3, "S400"),  # year boundary
        ]:
            (self.root / f"{year}" / f"{month:02d}" / site / "photos").mkdir(parents=True)
        (self.root / "2026" / "03" / "_ERRORS").mkdir(parents=True)
        self.index = build_index(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def where(self, site, d):
        r = resolve(self.index, self.root, site, d)
        return r.reason, r.folder.relative_to(self.root).as_posix()

    def test_same_month(self):
        self.assertEqual(self.where("S100", date(2026, 3, 10)),
                         ("same_month", "2026/03/S100/photos"))

    def test_late_write_up_goes_to_the_later_month(self):
        self.assertEqual(self.where("S200", date(2026, 3, 28)),
                         ("later_month", "2026/04/S200/photos"))

    def test_each_visit_finds_its_own_folder(self):
        self.assertEqual(self.where("S300", date(2026, 3, 5))[1], "2026/03/S300/photos")
        self.assertEqual(self.where("S300", date(2026, 6, 5))[1], "2026/08/S300/photos")
        self.assertEqual(self.where("S300", date(2026, 8, 5))[1], "2026/08/S300/photos")

    def test_no_later_folder_means_errors_of_the_photo_month(self):
        self.assertEqual(self.where("S100", date(2026, 9, 1)), ("errors", "2026/09/_ERRORS"))

    def test_never_resolves_to_an_earlier_month(self):
        reason, folder = self.where("S300", date(2026, 9, 1))
        self.assertEqual(reason, "errors")

    def test_crosses_year_boundary(self):
        self.assertEqual(self.where("S400", date(2026, 1, 15)),
                         ("later_month", "2026/03/S400/photos"))

    def test_unknown_site_goes_to_errors(self):
        self.assertEqual(self.where("S999", date(2026, 3, 1))[0], "errors")

    def test_errors_folder_is_not_indexed_as_a_site(self):
        self.assertNotIn("_ERRORS", self.index)


if __name__ == "__main__":
    unittest.main()
