# Absolute links broke three times

**Symptom.** The ledger has a clickable link per photo, and the operations team opens photos from it.
After a folder reorganisation, every link returned "not found". Then again after the next one. And a
third time.

**Cause.** Each link was stored as an **absolute** URL in the cell. Moving the files does not move the
links. Worse, each time the visible path column looked fine — it was relative — so "the files were
moved correctly" was true and "the links work" was false. The incidents ranged from a few hundred to
~8,000 links.

**Fix, in two parts.**

1. Store the path **relative to the ledger file**, and build the clickable link from it with a
   spreadsheet formula. Move the whole tree, ledger included, and every link still resolves. (The
   older projects kept absolute links on purpose: they worked and nobody asked to change them.)
2. Repair tools **resolve each link against a real file on disk**. A first repair had been approved
   by counting "rows with a link" — with the bug still inside. Counting is not verifying.

**A trap inside the trap.** Deleting rows with a spreadsheet library does **not** rewrite formulas
below them. Formula links carry their row number (`=HYPERLINK(C57)`), so after deleting orphan rows
~110 links silently opened *another* photo. The link works, so it looks right. Whoever deletes rows
rewrites the whole link column against its own row and checks it afterwards.

**Tests.** The key test moves the entire tree and asserts that every link still resolves, which is
the exact scenario that broke three times.

Demo: [`src/relative_links.py`](../../src/relative_links.py).
