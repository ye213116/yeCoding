---
name: repair-reproduce
description: Reproduce a Python defect and inspect a failing acceptance test before choosing a repair.
version: 1.0.0
tags: [python, repair, reproduction, 修复, 复现]
---

1. Read the supplied failing test evidence and identify the affected behavior.
2. Locate the implementation and its callers with file search or code context tools.
3. State the likely cause and a minimal change that preserves surrounding behavior.

Complete when the proposed change explains the observed failure and names concrete implementation files.
Treat environment errors as unresolved execution prerequisites rather than evidence of a code defect.
