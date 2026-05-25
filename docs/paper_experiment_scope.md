# 论文实验口径表

> 这份文档用于冻结论文叙事和图表口径。后续所有结果只按这里定义的主线、补丁和负结果解释，不再扩展主模型。

## 口径

| 角色 | 口径 | 证据来源 | 论文定位 |
| --- | --- | --- | --- |
| 基础 selector 主线 | `online_consistent_boundary400` / Online-Consistent Selector | `docs/online_consistent_boundary400_full400_eval.md` | 主线结果 |
| 稳定参考 baseline | `old_compact` | `docs/compact_risk_full400_eval.md`、`docs/online_consistent_boundary400_full400_eval.md`、`docs/compact_stable_full400_eval.md` | 对照基线；`docs/compact_stable_full400_eval.md` 只用于说明 stable 分支不如 old compact，不作为 old_compact 的主要证据 |
| 边界修正补丁 | `local_reopen_guarded` | `docs/local_reopen_guarded_full400_eval.md`、`docs/local_boundary_correction_ablation.md` | ablation / boundary correction |
| 负结果分支 | `pairwise_veto`、`compact_stable`、`polarity / SBE` | `docs/online_consistent_boundary400_full400_eval.md`、`docs/compact_stable_full400_eval.md`、`docs/literal_polarity_sbe_adapter.md` | 负结果，不进主线 |

## 冻结结论

- `local_reopen_guarded` 不是新的全局主模型，只是对 conservative selector 的局部边界修正。
- full400 上，`local_reopen_guarded` 没有增加 solved count，但把 mean time 压低了，所以应写成 ablation。
- `online_consistent_boundary400` 是代码和结果文件中的固定名称；论文正文中统一简称为 Online-Consistent Selector。
- Online-Consistent Selector 和 `old_compact` 是当前论文里应该保留的基础 selector 对照。
- `old_compact` 的直接数字来源是 `docs/compact_risk_full400_eval.md`；`compact_stable` 只作为 stable 分支失败的参照。
- 正式 `local_reopen_guarded` full400 patch 仍是 750-feature 版本；no750 只作为诊断性消融，不能替代最终 full400 结果。
- `pairwise_veto`、`compact_stable`、`polarity / SBE` 只作为负结果或补充诊断，不作为主叙事升级方向。

## 当前核心数字

| method | solved / 200 | mean_time |
| --- | --- | --- |
| `old_compact` | 56 | 46.3484s |
| `online_consistent_boundary400` | 56 | 46.2217s |
| `local_reopen_guarded` | 56 | 45.4976s |
| `one_shot` | 50 | 47.7517s |

## 后续验证约束

后续只做稳定性验证和论文补图，不再动主模型：

- 只看最终 online cache，不复用旧 cache。
- repeated split / repeated seed 只用于稳定性确认。
- threshold sweep 只在最终 cache 上做。
- 保留 per-instance win/loss、cactus plot、ablation matrix。
- no750 结果只能写成诊断性消融；除非重跑 no750 full400，否则正式 patch 仍按含 750 特征的 `local_reopen_guarded` 解释。
- 不再增加 polarity / SBE / 更复杂 selector 分支。

## 固定引用文件

- `docs/local_boundary_correction_ablation.md`
- `docs/paper_ablation_matrix.md`
- `docs/local_reopen_guarded_full400_eval.md`
- `docs/compact_risk_full400_eval.md`
- `docs/online_consistent_boundary400_full400_eval.md`
- `docs/compact_stable_full400_eval.md`
- `runs/analysis/local_reopen_guarded_full400_summary.csv`
- `runs/analysis/local_reopen_guarded_full400_per_instance.csv`
- `runs/analysis/local_reopen_guarded_full400_bucket_summary.csv`
- `runs/analysis/local_reopen_guarded_full400_open_set.csv`
- `runs/analysis/online_consistent_boundary400_stability.csv`
- `figures/fig_local_reopen_guarded_full400_cactus.pdf`
