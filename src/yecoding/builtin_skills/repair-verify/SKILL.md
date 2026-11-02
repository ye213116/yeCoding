---
name: repair-verify
description: Review a candidate Python repair against its diff and independently executed tests.
version: 1.0.0
tags: [python, repair, regression, 验证, 回归]
---

1. Compare the candidate diff with the original task and inspect affected callers.
2. Read the executor's exit codes and test output, keeping environment errors separate from test failures.
3. Report remaining defects with a concrete location and suggested correction.

Complete when the review explains the observed result and identifies meaningful coverage limits.
A passing acceptance suite supports only the tested behavior. Report additional concerns separately.
