# Supporting Details and Project Records

## Per-task results

TableA-1 supplements the aggregate results in Chapter6. Each cell pairs the recorded workflow status with the post-run check outcome. Budget means token-budget termination; not checked means no exported patch.

TableA-1 Workflow and additional-test outcomes for the eight held-out injected defects.

| Task | `single` | `team` | `verified` |
| --- | --- | --- | --- |
| `none-value` | Success/pass | Success/pass | Success/pass |
| `trailing-literal` | Success/pass | Budget/not checked | Budget/pass |
| `variable-cursor` | Success/pass | Success/pass | Success/pass |
| `unquoted-whitespace` | Success/pass | Success/pass | Success/pass |
| `escape-decoding` | Success/pass | Success/pass | Success/pass |
| `line-tracking` | Success/pass | Success/pass | Budget/not checked |
| `override-environment` | Success/pass | Budget/not checked | Budget/not checked |
| `disable-interpolation` | Success/pass | Budget/not checked | Budget/not checked |

## Functional traceability

TableA-2 expands the essential acceptance conditions specified in Chapter3. Functional checks do not establish an independent repair-quality gain.

TableA-2 Functional acceptance scenarios and their requirement mappings.

| ID | Scenario | Expected condition | Requirements |
| --- | --- | --- | --- |
| AC-01 | Missing commands | Reject before model repair | FR-03, FR-04 |
| AC-02 | Passing baseline | No new-repair claim | FR-04, FR-06 |
| AC-03 | Failed then valid candidate | Feedback, patch/report, source unchanged | FR-05 to FR-08 |
| AC-04 | Positive review, failing tests | Preserve failure and bounded retry | FR-06, FR-07 |
| AC-05 | Protected or out-of-scope edit | Reject operation or candidate | FR-01, FR-06 |
| AC-06 | Budget/no progress | Explicit stop and available evidence | FR-07, FR-08 |
| AC-07 | Timeout, cancellation, missing image | Cleanup; no host fallback | NFR-02, NFR-04 |
| AC-08 | Skills/memory | Attributable input; filtering; disabled mode | FR-09, FR-10 |
| AC-09 | Entry change/late result | Shared acceptance; cancelled state retained | FR-03, NFR-05 |

## Execution parameters

TableA-3 lists container arguments supporting the boundary described in Chapters4 and5. These are implemented settings, not proof of universal isolation.

TableA-3 Container arguments and their intended execution constraints.

| Mechanism | Setting | Effect |
| --- | --- | --- |
| Image/lifecycle | `--pull=never`, `--rm`, unique name | Prepared image; cleanup |
| Network/root | `--network=none`, `--read-only` | No network; restricted writes |
| Privileges | `--cap-drop=ALL`, `no-new-privileges` | Reduced authority |
| Resources | `--cpus=1`, `--memory=512m`, `--pids-limit=128` | Per-command bounds |
| Identity | Host UID and GID | Deployment-dependent identity |
| Temporary files | Approximately 64 MiB tmpfs at `/tmp` | Bounded writes |
| Workspace | Selected copy at `/workspace` | Task source mount |
| Environment/logs | Explicit variables; Docker logging disabled | Limited forwarding/storage |

TableA-4 specifies bounded source handling. The source fingerprint covers supported files only.

TableA-4 Snapshot and candidate limits used by the repair workspace.

| Check | Limit or rule | Purpose |
| --- | --- | --- |
| Individual file | 2,000,000 bytes | Bound reads |
| Total bytes | 100,000,000 | Bound memory |
| Snapshot files | 10,000 | Bound scope |
| Safety traversal | 20,000 entries | Bound generated tree |
| Types/names | No links, special files or unsupported path characters | Avoid traversal/diff ambiguity |
| Protected files | Tests and selected configuration | Preserve acceptance |

## Artefact locations

- Repair orchestration: `src/yecoding/agent/repair.py`.
- Workspace and command execution: `src/yecoding/sandbox/`.
- Functional tests: `tests/test_repair.py`.
- Evaluation harness and tasks: `eval/run_repair_eval.py`, `eval/repair_tasks.json`.
- Implementation fingerprints: `eval/evidence/repair-implementation.json`.
- Held-out results: `eval/evidence/repair-heldout-live.json`.
- Per-run evidence: `eval/evidence/repair-runs/`.
- Statistics: `docs/thesis/notes/ch06-statistics.json`.
- Fresh retrieval sweep and Docker fixture checks: `eval/evidence/visual-refresh-20261026/`.
- Figure inputs, role reconciliation and derived data: `docs/thesis/notes/visual-evidence-statistics.json`.
- Empirical figure generator: `docs/thesis/figures/plot_evidence_figures.py`.

## Project records and plan status

Records identify experiment evidence on 20 October, Chinese typesetting on 23 October and English adaptation/model-free supplementation on 26 October 2026. The supplement adds 240 retrieval contexts and 12 Docker checks, not repeated model runs. These are milestones, not an approved schedule. An approved original plan and submitted interim reports were not supplied; genuine acknowledgements remain the responsibility of the author.
