# Pre-Warmup 极保守 Skip Classifier

本轮实现的是 `pre-warmup skip gate`：在事件 rollout 之前，只根据第一次 one-shot GNN 的静态变量权重分布判断是否跳过 warmup/refinement。
目标不是大幅多跳，而是在不牺牲 `recovered_timeout` 和 `hard_speedup` 的前提下，跳过极少数几乎只会产生 easy slowdown 的样本。

## 训练设置

- 训练数据：`runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400/two_stage_all_data_policy.csv`
- Full400 离线对照：`runs/analysis/easy_slowdown_filter_full400_actual_per_instance.csv`
- 生成评估配置：`configs/config_eval_guided_solver_pre_warmup_skip_classifier_probe.yaml`
- L2：`0.5`
- threshold：`0.155104`
- max skip fraction：`0.03`
- 正例：`base_bucket=easy` 且 `counterfactual_reason` 为 `easy_slowdown` 或 `lost_solution`。
- 强负例：`recovered_timeout` 与 `hard_speedup`，阈值选择阶段要求训练集零误跳。
- 额外约束：默认要求训练集中被 skip 的样本全部来自 easy bucket。

## 静态特征

- base_rho_mean
- base_rho_std
- base_rho_range

## 训练集选择分布

| counterfactual_reason | n   | selected | score_mean |
| --------------------- | --- | -------- | ---------- |
| neutral               | 217 | 6        | 0.134733   |
| easy_slowdown         | 34  | 2        | 0.140815   |
| lost_solution         | 8   | 0        | 0.144950   |
| hard_speedup          | 7   | 0        | 0.142649   |
| recovered_timeout     | 13  | 0        | 0.138507   |
| slowdown              | 19  | 0        | 0.130703   |

## Full400 离线模拟

| n   | skip_count | skip_fraction | base_solved | cal_solved | skip_solved | base_mean | cal_mean  | skip_mean | skip_delta_vs_base | skip_delta_vs_cal | cal_recovered | skip_recovered | skipped_recovered | skipped_hard_speedup |
| --- | ---------- | ------------- | ----------- | ---------- | ----------- | --------- | --------- | --------- | ------------------ | ----------------- | ------------- | -------------- | ----------------- | -------------------- |
| 200 | 6          | 0.030000      | 50          | 56         | 56          | 47.751662 | 46.346545 | 46.341667 | -1.409995          | -0.004878         | 6             | 6              | 0                 | 0                    |

## Bucket 离线结果

| difficulty_bucket | n   | skip_count | cal_delta_mean | skip_delta_mean | skip_vs_cal_mean | skipped_recovered | skipped_hard_speedup |
| ----------------- | --- | ---------- | -------------- | --------------- | ---------------- | ----------------- | -------------------- |
| easy(<10s)        | 37  | 3          | 0.792782       | 0.775175        | -0.017608        | 0                 | 0                    |
| hard(>=30s)       | 4   | 0          | -7.356162      | -7.356162       | 0.000000         | 0                 | 0                    |
| medium(10-30s)    | 9   | 0          | -2.163247      | -2.163247       | 0.000000         | 0                 | 0                    |
| timeout           | 150 | 3          | -1.743084      | -1.745244       | -0.002161        | 0                 | 0                    |

## 离线被 Skip 的样本

| file_key     | difficulty_bucket | base_time | cal_time  | skip_time | skip_vs_cal_time | cal_outcome        | skip_outcome    | pre_warmup_skip_score |
| ------------ | ----------------- | --------- | --------- | --------- | ---------------- | ------------------ | --------------- | --------------------- |
| 3sat_36.cnf  | timeout           | 60.735306 | 60.924560 | 60.735306 | -0.189254        | both_timeout       | both_timeout    | 0.163246              |
| 3sat_141.cnf | easy(<10s)        | 3.076242  | 3.384436  | 3.076242  | -0.308194        | slower_both_solved | tie_both_solved | 0.162128              |
| 3sat_47.cnf  | easy(<10s)        | 2.833277  | 2.896292  | 2.833277  | -0.063015        | tie_both_solved    | tie_both_solved | 0.160500              |
| 3sat_106.cnf | timeout           | 60.836521 | 60.903736 | 60.836521 | -0.067215        | both_timeout       | both_timeout    | 0.158480              |
| 3sat_131.cnf | easy(<10s)        | 3.378868  | 3.659148  | 3.378868  | -0.280280        | slower_both_solved | tie_both_solved | 0.157163              |
| 3sat_105.cnf | timeout           | 60.825321 | 60.892952 | 60.825321 | -0.067631        | both_timeout       | both_timeout    | 0.156273              |

## 正式评估命令

```bash
python3 evaluate_guided_solver.py --config-name config_eval_guided_solver_pre_warmup_skip_classifier_probe
```

注意：离线模拟用既有 full400 结果估算 skip 后时间；正式 wall-clock 仍需要运行上面的配置确认。

