# Pre-Warmup Skip Gate Full400 静态规则评估

本轮实现了真正的 pre-warmup skip：被 skip 的实例直接复用第一次 one-shot GNN 产生的 solver 参数进入最终 solver，不再参与 500/1000/2000 conflicts event rollout，也不再做第二次 adapter GNN。

## 规则

```text
base_rho_mean <= -0.14975730180740354
AND base_rho_range >= 29.008091735839844
```

## 输出文件

- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400_EasySlowdownFilterFull400Calibrated/eval_pre_warmup_skip_full400_static_rule.csv`
- `runs/analysis/pre_warmup_skip_full400_static_rule_per_instance.csv`
- `runs/analysis/pre_warmup_skip_full400_static_rule_summary.csv`
- `runs/analysis/pre_warmup_skip_full400_static_rule_bucket_summary.csv`
- `runs/analysis/pre_warmup_skip_full400_static_rule_harmed.csv`

## 总体结果

| n   | skip_count | base_solved | cal_solved | skip_solved | base_mean | cal_mean | skip_mean | skip_delta_vs_base | skip_delta_vs_cal | cal_recovered | skip_recovered | cal_slowdown | skip_slowdown |
| --- | ---------- | ----------- | ---------- | ----------- | --------- | -------- | --------- | ------------------ | ----------------- | ------------- | -------------- | ------------ | ------------- |
| 200 | 68         | 50          | 56         | 55          | 47.7517   | 46.3465  | 46.5191   | -1.2326            | 0.1725            | 6             | 5              | 35           | 29            |

## Bucket 结果

| difficulty_bucket | n   | skip_count | base_solved | cal_solved | skip_solved | cal_delta_mean | skip_delta_mean | skip_vs_cal_mean | cal_slow | skip_slow | skip_rec |
| ----------------- | --- | ---------- | ----------- | ---------- | ----------- | -------------- | --------------- | ---------------- | -------- | --------- | -------- |
| easy(<10s)        | 37  | 20         | 37          | 37         | 37          | 0.7928         | 0.0738          | -0.7190          | 28       | 22        | 0        |
| hard(>=30s)       | 4   | 2          | 4           | 4          | 4           | -7.3562        | -7.2848         | 0.0714           | 1        | 1         | 0        |
| medium(10-30s)    | 9   | 3          | 9           | 9          | 9           | -2.1632        | -1.9816         | 0.1817           | 6        | 6         | 0        |
| timeout           | 150 | 43         | 0           | 6          | 5           | -1.7431        | -1.3485         | 0.3946           | 0        | 0         | 5        |

## 被 Skip 后受损最大的样本

| file_key     | difficulty_bucket | base_time | cal_time | skip_time | skip_vs_cal | cal_outcome        | skip_outcome       | base_rho_mean | base_rho_range |
| ------------ | ----------------- | --------- | -------- | --------- | ----------- | ------------------ | ------------------ | ------------- | -------------- |
| 3sat_196.cnf | medium(10-30s)    | 25.1129   | 10.2047  | 25.8560   | 15.6512     | faster_both_solved | slower_both_solved | -0.2710       | 31.6909        |
| 3sat_25.cnf  | easy(<10s)        | 1.6911    | 1.7190   | 1.8240    | 0.1050      | tie_both_solved    | slower_both_solved | -0.2504       | 33.9101        |
| 3sat_92.cnf  | easy(<10s)        | 7.6922    | 7.8329   | 7.9371    | 0.1041      | slower_both_solved | slower_both_solved | -0.2097       | 31.7984        |
| 3sat_19.cnf  | easy(<10s)        | 3.6099    | 3.7420   | 3.8294    | 0.0874      | slower_both_solved | slower_both_solved | -0.2291       | 29.8968        |
| 3sat_198.cnf | timeout           | 60.7432   | 60.8128  | 60.8775   | 0.0647      | both_timeout       | both_timeout       | -0.3262       | 31.2079        |
| 3sat_138.cnf | hard(>=30s)       | 52.1488   | 52.1222  | 52.1810   | 0.0588      | tie_both_solved    | tie_both_solved    | -0.3747       | 32.0267        |
| 3sat_21.cnf  | timeout           | 60.7553   | 60.8221  | 60.8733   | 0.0511      | both_timeout       | both_timeout       | -0.4627       | 30.2974        |
| 3sat_197.cnf | timeout           | 60.7539   | 60.8286  | 60.8780   | 0.0493      | both_timeout       | both_timeout       | -0.2450       | 29.3233        |
| 3sat_5.cnf   | timeout           | 60.7839   | 60.8592  | 60.8871   | 0.0279      | both_timeout       | both_timeout       | -0.1591       | 31.1171        |
| 3sat_57.cnf  | timeout           | 60.7854   | 60.8665  | 60.8934   | 0.0268      | both_timeout       | both_timeout       | -0.2625       | 33.3258        |
| 3sat_60.cnf  | timeout           | 60.7710   | 60.8593  | 60.8750   | 0.0157      | both_timeout       | both_timeout       | -0.5206       | 29.9006        |
| 3sat_47.cnf  | easy(<10s)        | 2.8333    | 2.8963   | 2.9088    | 0.0125      | tie_both_solved    | tie_both_solved    | -0.4099       | 29.4815        |

## 结论

- 工程路径有效：本次确实跳过 `68 / 200` 个实例，三段 warmup 只运行了 `132` 个实例。
- 但该静态规则不能作为主线：solved 从 calibrated 的 `56` 降到 `55`，丢了 1 个 recovered timeout。
- 均值从 calibrated 的 `46.3465s` 变为 `46.5191s`，反而慢了 `0.1725s`。
- 主要失败来自误跳过真实收益样本，例如 `3sat_196.cnf` 原 calibrated 为 `10.2047s`，skip 后回到 `25.8560s`。
- 因此 pre-warmup skip 不能只靠粗糙静态 rho 区间。下一步应训练一个极保守的 skip classifier：目标只跳过“几乎不可能 recovered / hard speedup”的 easy 小样本，且把 recovered_timeout 与 hard_speedup 作为强负例。
