---
status: accepted
---

# Write framework code for observed cases

weval's framework handles the cases that Tasks and Trials have produced, not
edge or corner cases anticipated in advance. Reviewers should be able to read
the framework in one sitting and find that every branch exists for a case they
can look up. Speculative handling adds branches that no Trial has exercised.
They cost review effort and may be wrong in ways nothing has shown yet.

When a retained Trial shows a new case, handle it then and name that Trial in
the commit message. For example, if a broken submission crashes the verifier
instead of failing its checks, that Trial justifies the fix.

## Considered options

Handling failure modes up front, for example by guarding every subprocess call
in `verify.py`. Rejected because a missed case is visible and cheap to recover
from: the Trial ends as a `non-result`, its verifier output shows the cause,
and runs are cheap enough to repeat after the fix.
