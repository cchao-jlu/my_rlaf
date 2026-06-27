# New-Closed-Old-On 局部 Reopen Gate 诊断

该诊断只面向 `new_closed_old_on` 边界样本：旧 compact 开启 adapter，而当前 online-consistent selector 关闭 adapter。
目标不是再调全局阈值，而是判断是否存在局部 override 证据，能打开 `3sat_46/196/188`，同时挡住 `3sat_82/93`。

## 使用特征

- warmup_c750_minus_warmup_c500_decisions
- warmup_c1000_minus_warmup_c750_decisions
- warmup_c1500_minus_warmup_c1000_decisions
- warmup_c2000_minus_warmup_c1500_decisions
- warmup_c2000_rho_event_corr
- warmup_c2000_rho_event_top10_overlap
- warmup_c2000_base_rho_std
- warmup_c2000_event_top10_mass

## 最优候选规则

| rule | selected | opened_positive | opened_negative | opened_neutral | missed_positive | net_gain_seconds | selected_positive_keys | selected_negative_keys | selected_neutral_keys |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| warmup_c1000_minus_warmup_c750_decisions >= 294 AND warmup_c2000_rho_event_corr >= 0.036501 | 4 | 3 | 0 | 1 | 0 | 84.1359 | 3sat_188.cnf,3sat_196.cnf,3sat_46.cnf |  | 3sat_66.cnf |

## 候选规则 Top 10

| rule | selected | opened_positive | opened_negative | opened_neutral | missed_positive | net_gain_seconds |
| --- | --- | --- | --- | --- | --- | --- |
| warmup_c1000_minus_warmup_c750_decisions >= 294 AND warmup_c2000_rho_event_corr >= 0.036501 | 4 | 3 | 0 | 1 | 0 | 84.1359 |
| warmup_c1000_minus_warmup_c750_decisions >= 294 AND warmup_c2000_rho_event_corr >= 0.0333871 | 5 | 3 | 0 | 2 | 0 | 84.1232 |
| warmup_c1000_minus_warmup_c750_decisions >= 293 AND warmup_c2000_rho_event_corr >= 0.036501 | 6 | 3 | 0 | 3 | 0 | 84.1351 |
| warmup_c1000_minus_warmup_c750_decisions >= 294 AND warmup_c2000_rho_event_corr >= 0.0189217 | 6 | 3 | 0 | 3 | 0 | 84.1269 |
| warmup_c1000_minus_warmup_c750_decisions >= 294 AND warmup_c2000_rho_event_corr >= -0.0195634 | 7 | 3 | 0 | 4 | 0 | 84.1612 |
| warmup_c1000_minus_warmup_c750_decisions >= 292 AND warmup_c2000_rho_event_corr >= 0.036501 | 7 | 3 | 0 | 4 | 0 | 84.1410 |
| warmup_c1000_minus_warmup_c750_decisions >= 293 AND warmup_c2000_rho_event_corr >= 0.0333871 | 7 | 3 | 0 | 4 | 0 | 84.1224 |
| warmup_c1000_minus_warmup_c750_decisions >= 294 AND warmup_c2000_rho_event_corr >= -0.0274373 | 8 | 3 | 0 | 5 | 0 | 84.1541 |
| warmup_c1000_minus_warmup_c750_decisions >= 290 AND warmup_c2000_rho_event_corr >= 0.036501 | 8 | 3 | 0 | 5 | 0 | 84.1406 |
| warmup_c1000_minus_warmup_c750_decisions >= 292 AND warmup_c2000_rho_event_corr >= 0.0333871 | 8 | 3 | 0 | 5 | 0 | 84.1283 |

## 最优规则打开的样本

| file_key | counterfactual_class | counterfactual_reason | adapter_minus_base_time | local_gate_open |
| --- | --- | --- | --- | --- |
| 3sat_66.cnf | neutral | neutral | -0.0011 | 1 |
| 3sat_188.cnf | positive | recovered_timeout | -34.4871 | 1 |
| 3sat_196.cnf | positive | hard_speedup | -18.6365 | 1 |
| 3sat_46.cnf | positive | hard_speedup | -31.0112 | 1 |

## 当前判断

- dense trace 支持一个局部 reopen 方向：中早期 decision drift 较高时，当前 adapter 更可能救回旧 selector 误关样本。
- 但最优规则仍会打开少量 neutral timeout 样本；当前最佳规则只误开 `3sat_66.cnf`，其增益接近 0，需要下一轮重复 seed 或更长 final limit 判断是否真实安全。
- 因此这一步适合进入 `new_closed_old_on` 局部 override 原型，不应替换全局 risk/recovery/slowdown gate。

