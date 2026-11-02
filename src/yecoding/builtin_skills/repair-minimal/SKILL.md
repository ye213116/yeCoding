---
name: repair-minimal
description: Implement a minimal Python bug fix using a disposable workspace and test feedback.
version: 1.0.0
tags: [python, repair, patch, 修复, 补丁]
---

1. Read the relevant implementation before editing.
2. Change production code to address the reproduced cause; preserve existing APIs and test files.
3. Run the relevant command in the sandbox when it helps discriminate between repair hypotheses.
4. Use new failure evidence to revise the hypothesis before another edit.

Complete when the candidate implementation is written and the change summary names affected behavior.
The independent executor establishes acceptance; the summary itself is not test evidence.
