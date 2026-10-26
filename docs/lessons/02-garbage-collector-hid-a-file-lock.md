# The garbage collector was hiding a file lock

**Symptom.** Every photo downloaded, the ledger was written, and then the input spreadsheet could not
be moved to the "processed" folder: `WinError 32, the file is being used by another process`. It
stayed in the inbox — and **a file left in the inbox gets processed again**, downloading everything a
second time. It happened on small inputs and almost never on large ones.

**Cause.** A spreadsheet reader object was opened only to list sheet names and never closed. On
CPython the handle is released when the object is collected, so a long run (minutes) gave the
collector time to free it, and a short one (seconds) did not. Fixed once, it came back: a second
reader in a schema validator had **four exit paths** and none closed it, and schema detection called
it once per candidate schema.

**Fix.** Close in `finally` (or a context manager) everywhere. Plus a safety net on the move: a few
retries with `gc.collect()` between them, which also covers the sync client holding the file briefly.
The safety net does not replace closing handles.

**How it stays fixed.** The test does what production does — it **moves the file** after analysing it
— and runs once with the collector turned off, because the collector is exactly what made the normal
test pass by accident:

```python
gc.disable()
try:
    analyse(path)
    shutil.move(path, processed_dir)   # raises if any handle is still open
finally:
    gc.enable()
```

Before the fix, 2 of 4 real inputs failed this test. Reading the code had not found the second leak.
