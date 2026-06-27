# New-Closed-Old-On 局部 Trace 审计

本报告只分析 `new_closed_old_on` 局部边界：旧 compact 曾开启 adapter，当前 online-consistent selector 关闭 adapter。
这里使用当前 boundary400 checkpoint 的强制 adapter counterfactual trace，避免继续依赖旧 feature cache 或全局阈值扫描。

## 结论

- 当前局部 trace 中，`3sat_46`、`3sat_196` 是 hard_speedup 正例，`3sat_188` 是 recovered_timeout 正例。
- `3sat_82`、`3sat_93` 是 slowdown 负例，应继续关闭 adapter。
- `3sat_188` 与早期 manifest 的 `keep_closed` 标签冲突，后续局部门控应以当前 trace 为准。
- 样本量只有 5 个强标签，适合做局部 reopen override 的诊断，不适合包装成新的全局 selector 结论。

## 标签概览

| n | positive | negative | neutral | recovered_timeout | hard_speedup | slowdown | manifest_trace_disagreement | mean_adapter_minus_base |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 26.0000 | 3.0000 | 2.0000 | 21.0000 | 1.0000 | 2.0000 | 2.0000 | 1.0000 | -2.5190 |

## 焦点样本

| file_key | counterfactual_class | counterfactual_reason | base_pipeline_time | adapter_pipeline_time | adapter_minus_base_time | manifest_label | manifest_reason | trace_reopen_label | trace_reopen_reason | feature_profile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_46.cnf | positive | hard_speedup | 31.5151 | 0.5039 | -31.0112 | 1.0000 | reopen_old_adapter | 1 | reopen_by_current_trace | rho_mean=-0.1668; delta=0.0352; entropy=0.8879; top10=0.4557; corr=0.0859; overlap=0.4500 |
| 3sat_196.cnf | positive | hard_speedup | 28.9109 | 10.2744 | -18.6365 | 1.0000 | reopen_old_adapter | 1 | reopen_by_current_trace | rho_mean=-0.2710; delta=0.0346; entropy=0.8966; top10=0.4277; corr=0.0365; overlap=0.4500 |
| 3sat_188.cnf | positive | recovered_timeout | 60.3026 | 25.8155 | -34.4871 | 0.0000 | keep_closed | 1 | reopen_by_current_trace | rho_mean=-0.0389; delta=0.0336; entropy=0.8783; top10=0.4770; corr=0.2096; overlap=0.5000 |
| 3sat_82.cnf | negative | slowdown | 21.6452 | 37.5681 | 15.9229 | 0.0000 | keep_closed | 0 | keep_closed_by_current_trace | rho_mean=-0.2225; delta=0.0347; entropy=0.8877; top10=0.4502; corr=-0.0351; overlap=0.4500 |
| 3sat_93.cnf | negative | slowdown | 19.3066 | 21.9967 | 2.6901 | 0.0000 | keep_closed | 0 | keep_closed_by_current_trace | rho_mean=-0.1590; delta=0.0354; entropy=0.8929; top10=0.4269; corr=0.0630; overlap=0.3750 |

## 特征均值差异

下表只比较 positive/negative 强标签样本。由于样本极少，该表用于定位下一轮 trace 增强方向，而不是统计显著性证明。

| feature | positive_mean | negative_mean | pos_minus_neg | positive_min | positive_max | negative_min | negative_max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| warmup_c750_minus_warmup_c500_decisions | 305.0000 | 287.5000 | 17.5000 | 293.0000 | 317.0000 | 281.0000 | 294.0000 |
| warmup_c1000_minus_warmup_c750_decisions | 308.0000 | 293.0000 | 15.0000 | 294.0000 | 320.0000 | 286.0000 | 300.0000 |
| warmup_c1500_minus_warmup_c1000_decisions | 620.6667 | 609.5000 | 11.1667 | 606.0000 | 642.0000 | 604.0000 | 615.0000 |
| warmup_c2000_minus_warmup_c1500_decisions | 598.6667 | 602.5000 | -3.8333 | 589.0000 | 615.0000 | 593.0000 | 612.0000 |
| warmup_c500_minus_warmup_c250_decisions | 309.3333 | 305.5000 | 3.8333 | 294.0000 | 318.0000 | 297.0000 | 314.0000 |
| warmup_c2000_base_rho_std | 2.3911 | 2.5490 | -0.1579 | 2.3579 | 2.4155 | 2.5437 | 2.5543 |
| warmup_c2000_rho_event_corr | 0.1107 | 0.0140 | 0.0967 | 0.0365 | 0.2096 | -0.0351 | 0.0630 |
| warmup_c2000_base_rho_range | 29.3827 | 29.3184 | 0.0643 | 26.7961 | 31.6909 | 28.2807 | 30.3560 |
| warmup_c2000_event_conf_learnt_log_max | 7.0985 | 7.1539 | -0.0554 | 7.0519 | 7.1824 | 7.1285 | 7.1793 |
| warmup_c2000_rho_event_top10_overlap | 0.4667 | 0.4125 | 0.0542 | 0.4500 | 0.5000 | 0.3750 | 0.4500 |
| warmup_c2000_base_rho_mean | -0.1589 | -0.1908 | 0.0319 | -0.2710 | -0.0389 | -0.2225 | -0.1590 |
| warmup_c750_minus_warmup_c500_rho_event_corr | -0.0068 | 0.0151 | -0.0218 | -0.0114 | -0.0020 | 0.0109 | 0.0192 |
| warmup_c2000_event_top10_mass | 0.4535 | 0.4385 | 0.0149 | 0.4277 | 0.4770 | 0.4269 | 0.4502 |
| warmup_c1500_minus_warmup_c1000_rho_event_corr | 0.0069 | -0.0051 | 0.0120 | 0.0003 | 0.0151 | -0.0093 | -0.0009 |
| warmup_c1000_minus_warmup_c750_event_top10_mass | -0.0040 | 0.0076 | -0.0116 | -0.0107 | 0.0054 | 0.0026 | 0.0125 |

