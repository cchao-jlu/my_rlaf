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
| 26.0000 | 3.0000 | 2.0000 | 21.0000 | 1.0000 | 2.0000 | 2.0000 | 1.0000 | -2.5130 |

## 焦点样本

| file_key | counterfactual_class | counterfactual_reason | base_pipeline_time | adapter_pipeline_time | adapter_minus_base_time | manifest_label | manifest_reason | trace_reopen_label | trace_reopen_reason | feature_profile |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_46.cnf | positive | hard_speedup | 31.0406 | 0.5349 | -30.5057 | 1.0000 | reopen_old_adapter | 1 | reopen_by_current_trace | rho_mean=-0.1668; delta=0.0352; entropy=0.8879; top10=0.4557; corr=0.0859; overlap=0.4500; d_top10=-0.0006; d_corr=0.0140 |
| 3sat_196.cnf | positive | hard_speedup | 25.7612 | 9.9529 | -15.8083 | 1.0000 | reopen_old_adapter | 1 | reopen_by_current_trace | rho_mean=-0.2710; delta=0.0346; entropy=0.8966; top10=0.4277; corr=0.0365; overlap=0.4500; d_top10=0.0101; d_corr=-0.0088 |
| 3sat_188.cnf | positive | recovered_timeout | 60.3508 | 25.5378 | -34.8130 | 0.0000 | keep_closed | 1 | reopen_by_current_trace | rho_mean=-0.0389; delta=0.0336; entropy=0.8783; top10=0.4770; corr=0.2096; overlap=0.5000; d_top10=-0.0094; d_corr=0.0157 |
| 3sat_82.cnf | negative | slowdown | 21.0723 | 35.0792 | 14.0069 | 0.0000 | keep_closed | 0 | keep_closed_by_current_trace | rho_mean=-0.2225; delta=0.0347; entropy=0.8877; top10=0.4502; corr=-0.0351; overlap=0.4500; d_top10=0.0163; d_corr=-0.0139 |
| 3sat_93.cnf | negative | slowdown | 18.8376 | 20.6025 | 1.7649 | 0.0000 | keep_closed | 0 | keep_closed_by_current_trace | rho_mean=-0.1590; delta=0.0354; entropy=0.8929; top10=0.4269; corr=0.0630; overlap=0.3750; d_top10=0.0090; d_corr=0.0095 |

## 特征均值差异

下表只比较 positive/negative 强标签样本。由于样本极少，该表用于定位下一轮 trace 增强方向，而不是统计显著性证明。

| feature | positive_mean | negative_mean | pos_minus_neg | positive_min | positive_max | negative_min | negative_max |
| --- | --- | --- | --- | --- | --- | --- | --- |
| warmup_c1000_minus_warmup_c500_decisions | 613.0000 | 580.5000 | 32.5000 | 611.0000 | 615.0000 | 580.0000 | 581.0000 |
| warmup_c2000_minus_warmup_c1000_decisions | 1219.3333 | 1212.0000 | 7.3333 | 1198.0000 | 1231.0000 | 1197.0000 | 1227.0000 |
| warmup_c2000_base_rho_std | 2.3911 | 2.5490 | -0.1579 | 2.3579 | 2.4155 | 2.5437 | 2.5543 |
| warmup_c2000_rho_event_corr | 0.1107 | 0.0140 | 0.0967 | 0.0365 | 0.2096 | -0.0351 | 0.0630 |
| warmup_c2000_base_rho_range | 29.3827 | 29.3184 | 0.0643 | 26.7961 | 31.6909 | 28.2807 | 30.3560 |
| warmup_c2000_event_conf_learnt_log_max | 7.0985 | 7.1539 | -0.0554 | 7.0519 | 7.1824 | 7.1285 | 7.1793 |
| warmup_c2000_rho_event_top10_overlap | 0.4667 | 0.4125 | 0.0542 | 0.4500 | 0.5000 | 0.3750 | 0.4500 |
| warmup_c2000_base_rho_mean | -0.1589 | -0.1908 | 0.0319 | -0.2710 | -0.0389 | -0.2225 | -0.1590 |
| warmup_c1000_minus_warmup_c500_rho_event_corr | -0.0067 | 0.0100 | -0.0167 | -0.0086 | -0.0052 | -0.0044 | 0.0244 |
| warmup_c2000_event_top10_mass | 0.4535 | 0.4385 | 0.0149 | 0.4277 | 0.4770 | 0.4269 | 0.4502 |
| warmup_c2000_minus_warmup_c1000_event_top10_mass | 0.0000 | 0.0126 | -0.0126 | -0.0094 | 0.0101 | 0.0090 | 0.0163 |
| warmup_c2000_minus_warmup_c1000_rho_event_corr | 0.0070 | -0.0022 | 0.0092 | -0.0088 | 0.0157 | -0.0139 | 0.0095 |
| warmup_c1000_minus_warmup_c500_event_top10_mass | -0.0047 | -0.0003 | -0.0044 | -0.0205 | 0.0138 | -0.0024 | 0.0018 |
| warmup_c2000_event_entropy_norm | 0.8876 | 0.8903 | -0.0027 | 0.8783 | 0.8966 | 0.8877 | 0.8929 |
| warmup_c2000_delta_abs_mean | 0.0345 | 0.0350 | -0.0005 | 0.0336 | 0.0352 | 0.0347 | 0.0354 |

