# Whose photo is it? A rule that two tests must hold at once

**Context.** Each photo is filed under a *subject* — usually the site the inspection belongs to. Some
inspection forms contain a repeating list, one row per item, and each row can reference its own
element.

**Two cases that look the same and need opposite answers.**

| Form | Does the inspection itself have a site? | Correct subject |
|---|---|---|
| A one-off campaign with N items | No — it belongs to no site | the item on each **row** |
| A site with N machines inside it | Yes | the **site** |

The first case was built first, and its rule ("the row's element wins") was right for it. When a team
moved the second kind of form to the same list feature, that rule would have filed the photos of one
site across **~40 per-machine folders instead of 2**, splitting its history in two, with no error.
It was caught by running the real pipeline functions on a real input before deploying.

**Fix.** The discriminant is **data, not a hard-coded list of forms**: if the inspection has its own
site, it wins; otherwise the row's element is the fallback. The file name follows the same rule as
the folder, so names and folders cannot disagree.

**How it stays fixed.** Two tests, one per case, and they must be green **together**: each one alone
can be satisfied by breaking the other. A deploy-time check exercises both halves on the target
machine too — not by reading a version number, which proves nothing if Python imports another copy of
the code.
