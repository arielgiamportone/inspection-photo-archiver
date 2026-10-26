# "Thousands downloaded, 0 errors" — and photos missing

**Symptom.** The run summary said every photo had been downloaded with no errors. The technicians
still could not find some photos.

**Cause.** The destination folder was looked up only in **the month the photo was taken**. But a
site's folder is created when its inspection is written up, which is often the following month. No
folder that month → the photo went to the *error* folder of the wrong month. Download succeeded, so it
was not counted as an error. A site visited twice, months apart, made it worse.

**Fix.** Build an index of every month in which each site has a folder (one scan, well under a second),
then resolve each photo:

1. the folder of its own month, if it exists;
2. otherwise the **earliest** folder at or after that month — a write-up is never created before the
   visit, and "earliest", not "newest", keeps two visits apart;
3. otherwise the error folder, which now means something: the write-up does not exist yet.

**The broader point.** "0 errors" measured the download, not the outcome. The log now marks every
photo filed in a different month than it was taken, so the decision is traceable.

Demo: [`src/destination_resolver.py`](../../src/destination_resolver.py).
