# The ledger that emptied itself

**Symptom.** The cumulative ledger (every archived photo → its source URL) suddenly held only the
photos of the last run. Several months of history were gone. No error had ever been shown.

**Cause.** The load routine had two "defensive" branches that were the opposite of defensive:

```python
try:
    df = read(path)
    if not expected_columns <= set(df.columns):
        df = empty(); save(df)       # unfamiliar header -> overwrite with nothing
except Exception:
    df = empty()                     # any read error -> start from nothing
```

Both triggers were everyday events: the file **open in a spreadsheet app** (permission error), or a
cloud-synced file that existed only as a **placeholder not yet downloaded**. A header rename during a
refactor fired the second branch too. Each run then appended its own rows to an empty frame and
saved — silently, and again on the next run.

**Fix.** A load can only end four ways: `new`, `loaded`, `migrated` (legacy header renamed, every row
kept, original backed up) or `reset` (unknown format, **backed up first**). An unreadable file is
retried a few times and then **aborts the run**. It is never treated as empty.

**Why abort and not "best effort".** Skipping the ledger and downloading anyway sounds friendlier, but
that run's photos would never be registered: a hole in the index that nobody sees. Aborting is
self-correcting — the input goes to the error folder, an alert goes out, and the retry leaves
everything consistent. The cost is a delay, not a loss.

**Recovery.** The history was rebuilt (~21k records) from the per-day ledgers, which survived because
they lived in subfolders the bug never touched, plus a disk scan for the rest.

Demo: [`src/safe_ledger.py`](../../src/safe_ledger.py).
