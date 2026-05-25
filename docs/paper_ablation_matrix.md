# 论文消融矩阵

> 只保留能进正文的消融，不再扩主模型。
> 代码/结果名统一用 `online_consistent_boundary400`，论文简称统一写成 `Online-Consistent Selector`。
> `local_reopen_guarded` 只写成 `local boundary correction ablation`。

## 矩阵

| 角色 | 变化点 | 结果 | 结论 | 证据 |
| --- | --- | --- | --- | --- |
| 主线 baseline | `online_consistent_boundary400` | `56/200`, `46.2217s` | 主 selector | `docs/online_consistent_boundary400_full400_eval.md`, `runs/analysis/online_consistent_boundary400_full400_summary.csv` |
| no guard | raw local reopen rule on boundary subset, no candidate manifest | boundary26: `5/26`, `51.6751s` vs `53.3406s`; opens `3` positive + `1` neutral, `0` negative | local correction has signal, but only as boundary patch | `docs/local_boundary_correction_ablation.md`, `docs/local_reopen_override_focus6_eval.md`, `runs/analysis/local_reopen_boundary26_wallclock_summary.csv`, `runs/analysis/local_reopen_boundary26_open_set.csv`, `runs/analysis/local_reopen_boundary26_guidance_audit.csv` |
| candidate guard | same local reopen rule, gated by `local_reopen_candidate_manifest` | full400: only `4` candidates open; `3` positive + `1` neutral, `0` negative; `56/200`, `45.4976s` | guard keeps patch local and safe | `docs/local_reopen_guarded_full400_eval.md`, `runs/analysis/local_reopen_guarded_full400_open_set.csv`, `runs/analysis/local_reopen_guarded_full400_guidance_audit.csv`, `runs/analysis/local_reopen_guarded_full400_summary.csv` |
| no750 diagnostic | drop 750-specific feature from the `new_closed_old_on` gate search only | diagnostic best rule still opens `3` positive, `0` negative, `1` neutral; net gain `81.1450s` vs `84.1359s` with the 750-feature rule; neutral differs: `3sat_183.cnf` vs formal `3sat_66.cnf` | diagnostic only: boundary signal is not entirely dependent on the 750 point, but this does not replace the official full400 750-feature patch | `docs/new_closed_old_on_local_reopen_gate.md`, `docs/new_closed_old_on_local_reopen_gate_no750.md`, `runs/analysis/new_closed_old_on_local_reopen_gate_rules.csv`, `runs/analysis/new_closed_old_on_local_reopen_gate_no750_rules.csv`, `runs/analysis/new_closed_old_on_local_reopen_gate_no750_best_selection.csv` |
| local reopen on/off | `local_reopen_guarded` vs `online_consistent_boundary400` | solved unchanged `56/200`; mean time `46.2217s -> 45.4976s` | final ablation claim | `docs/online_consistent_boundary400_full400_eval.md`, `docs/local_reopen_guarded_full400_eval.md`, `docs/paper_stability_validation.md` |

## 750 / no750 口径

- 正式 `local_reopen_guarded` full400 结果仍是 750-feature 版本：配置使用 `intervention_conflicts: [500, 750, 1000, 2000]`，规则使用 `warmup_c1000_minus_warmup_c750_decisions`。
- 正式 full400 open set 是 `3sat_188.cnf`、`3sat_196.cnf`、`3sat_46.cnf`、`3sat_66.cnf`，对应 `56/200`, `45.4976s`。
- no750 只是在 `new_closed_old_on` trace 上做的诊断性特征消融，open set 中的 neutral 是 `3sat_183.cnf`；它还没有作为 full400 配置重跑。
- 因此论文正文可以把 no750 写成诊断性消融，但不能把最终 full400 patch 写成 `500/1000/2000 only`，除非之后重新跑一版 no750 full400。

## 保留 / 排除

- 保留：`no guard`、`candidate guard`、`no750 diagnostic`、`local reopen on/off`
- 排除：`polarity`、`SBE`、更复杂 selector
- `compact_stable` 只保留为负结果参照，不进主线消融表
