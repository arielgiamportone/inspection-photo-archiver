import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from safe_ledger import (  # noqa: E402
    COLUMNS,
    LedgerUnreadable,
    append_records,
    load_ledger,
    save_ledger,
)


def record(i):
    return {"source_url": f"https://files.example.test/{i}", "file_name": f"S{i:03d}_20260915.jpeg",
            "path": f"2026/09/S{i:03d}/photos/S{i:03d}_20260915.jpeg", "job_id": str(1000 + i),
            "field": "exterior"}


def no_sleep(_):
    pass


class FlakyReader:
    """Fails like a file held open by a spreadsheet app, then succeeds."""

    def __init__(self, failures, real):
        self.failures, self.real, self.calls = failures, real, 0

    def __call__(self, path):
        self.calls += 1
        if self.calls <= self.failures:
            raise PermissionError(13, "The process cannot access the file", str(path))
        return self.real(path)


class TestSafeLedger(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "ledger.csv"

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_starts_empty_without_writing(self):
        r = load_ledger(self.path)
        self.assertEqual((r.action, r.rows), ("new", []))
        self.assertFalse(self.path.exists())

    def test_history_accumulates_across_runs(self):
        append_records(self.path, [record(1), record(2)])
        n = append_records(self.path, [record(3)])
        self.assertEqual(n, 3)
        self.assertEqual(load_ledger(self.path).action, "loaded")

    def test_transient_lock_is_retried(self):
        save_ledger(self.path, [record(1)])
        from safe_ledger import _read_csv
        reader = FlakyReader(failures=2, real=_read_csv)
        r = load_ledger(self.path, reader=reader, sleep=no_sleep)
        self.assertEqual(len(r.rows), 1)
        self.assertEqual(reader.calls, 3)

    def test_persistent_lock_aborts_and_leaves_file_untouched(self):
        save_ledger(self.path, [record(i) for i in range(50)])
        before = self.path.read_bytes()
        from safe_ledger import _read_csv
        with self.assertRaises(LedgerUnreadable):
            append_records(self.path, [record(99)],
                           reader=FlakyReader(failures=10, real=_read_csv), sleep=no_sleep)
        self.assertEqual(self.path.read_bytes(), before)

    def test_legacy_header_is_migrated_keeping_every_row(self):
        legacy = "Original URL,New Name,Destination,Job,Field\n" + "".join(
            f"https://files.example.test/{i},S{i}.jpeg,2026/09/S{i}.jpeg,{i},door\n"
            for i in range(20))
        self.path.write_text(legacy, encoding="utf-8")
        r = load_ledger(self.path)
        self.assertEqual(r.action, "migrated")
        self.assertEqual(len(r.rows), 20)
        self.assertEqual(r.rows[0]["file_name"], "S0.jpeg")
        self.assertEqual(r.backup.read_text(encoding="utf-8"), legacy)
        self.assertEqual(load_ledger(self.path).action, "loaded")

    def test_unknown_format_with_data_is_backed_up_before_reset(self):
        original = "a,b\n1,2\n3,4\n"
        self.path.write_text(original, encoding="utf-8")
        r = load_ledger(self.path)
        self.assertEqual(r.action, "reset")
        self.assertIsNotNone(r.backup)
        self.assertEqual(r.backup.read_text(encoding="utf-8"), original)

    def test_save_leaves_no_temp_file(self):
        save_ledger(self.path, [record(1)])
        self.assertEqual([p.name for p in Path(self.tmp.name).iterdir()], ["ledger.csv"])
        self.assertEqual(self.path.read_text(encoding="utf-8").splitlines()[0], ",".join(COLUMNS))


if __name__ == "__main__":
    unittest.main()
