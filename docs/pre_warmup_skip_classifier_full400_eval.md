# Pre-Warmup Skip Classifier 正式 Full400 评估

本轮实现并正式评估了极保守 `pre-warmup skip classifier`。它在事件 rollout 前只使用 one-shot GNN 的静态 rho 分布，跳过少量高置信低收益样本，以减少 warmup/refinement 开销。

## 输出文件

- `configs/config_eval_guided_solver_pre_warmup_skip_classifier.yaml`
- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400_EasySlowdownFilterFull400Calibrated/eval_pre_warmup_skip_full400_conservative_classifier.csv`
- `runs/analysis/pre_warmup_skip_classifier_full400_actual_per_instance.csv`
- `runs/analysis/pre_warmup_skip_classifier_full400_actual_summary.csv`
- `runs/analysis/pre_warmup_skip_classifier_full400_actual_bucket_summary.csv`
- `runs/analysis/pre_warmup_skip_classifier_full400_actual_skipped.csv`

## 关键结论

- 工程路径有效：正式评估中实际 `skip 6 / 200`，被 skip 的样本 `refinement CPU/GPU time = 0`，说明 pre-warmup skip 确实绕过了 event rollout 和第二次 adapter GNN。
- 安全性没有直接破坏：6 个被 skip 样本都不是 calibrated 的 `recovered_timeout`，也不是 hard speedup。
- 但 wall-clock 主结果不成立：solved 从 calibrated 的 `56` 降到 `55`，mean time 从 `46.3465s` 升到 `46.5526s`。
- 丢失的恢复样本是 `3sat_89.cnf`，它没有被 skip；单实例复跑 calibrated 也没有 recovered，说明该样本恢复不稳定，当前评估噪声足以淹没 pre-warmup skip 的微小收益。
- 因此这条线目前只能作为“安全开销控制模块/负结果诊断”，不应作为论文主增益。主线仍应放在 risk controller、counterfactual trace 和 recovery 稳定性上。

## 总体结果

| method | solved | mean_time | delta_vs_base | faster_both_solved | slower_both_solved | tie_both_solved | recovered_timeout | lost_solution | both_timeout |
| ------ | ------ | --------- | ------------- | ------------------ | ------------------ | --------------- | ----------------- | ------------- | ------------ |
| cal    | 56     | 46.346545 | -1.405117     | 5                  | 35                 | 10              | 6                 | 0             | 144          |
| skip   | 55     | 46.552618 | -1.199045     | 10                 | 28                 | 12              | 5                 | 0             | 145          |

## Bucket 结果

| difficulty_bucket | n   | skip_count | cal_solved | skip_solved | cal_delta_mean | skip_delta_mean | skip_vs_cal_mean | cal_recovered | skip_recovered |
| ----------------- | --- | ---------- | ---------- | ----------- | -------------- | --------------- | ---------------- | ------------- | -------------- |
| easy(<10s)        | 37  | 3          | 37         | 37          | 0.792782       | 0.707322        | -0.085460        | 0             | 0              |
| hard(>=30s)       | 4   | 0          | 4          | 4           | -7.356162      | -7.426749       | -0.070587        | 0             | 0              |
| medium(10-30s)    | 9   | 0          | 9          | 9           | -2.163247      | -2.221974       | -0.058727        | 0             | 0              |
| timeout           | 150 | 3          | 6          | 5           | -1.743084      | -1.441834       | 0.301250         | 6             | 5              |

## 被 Skip 的 6 个样本

| file_key     | difficulty_bucket | base_time | cal_time  | skip_time | cal_outcome        | skip_outcome       | skip_vs_cal_time | pre_warmup_skip_score |
| ------------ | ----------------- | --------- | --------- | --------- | ------------------ | ------------------ | ---------------- | --------------------- |
| 3sat_36.cnf  | timeout           | 60.735306 | 60.924560 | 60.617313 | both_timeout       | both_timeout       | -0.307248        | 0.163246              |
| 3sat_141.cnf | easy(<10s)        | 3.076242  | 3.384436  | 3.158241  | slower_both_solved | tie_both_solved    | -0.226195        | 0.162128              |
| 3sat_47.cnf  | easy(<10s)        | 2.833277  | 2.896292  | 2.628007  | tie_both_solved    | faster_both_solved | -0.268285        | 0.160500              |
| 3sat_106.cnf | timeout           | 60.836521 | 60.903736 | 60.825350 | both_timeout       | both_timeout       | -0.078386        | 0.158480              |
| 3sat_131.cnf | easy(<10s)        | 3.378868  | 3.659148  | 3.722913  | slower_both_solved | slower_both_solved | 0.063765         | 0.157163              |
| 3sat_105.cnf | timeout           | 60.825321 | 60.892952 | 60.820950 | both_timeout       | both_timeout       | -0.072002        | 0.156273              |

## 丢失的 Recovered Timeout

| file_key    | base_time | cal_time | skip_time | cal_outcome       | skip_outcome | skip_vs_cal_time | pre_warmup_skip | pre_warmup_skip_score |
| ----------- | --------- | -------- | --------- | ----------------- | ------------ | ---------------- | --------------- | --------------------- |
| 3sat_89.cnf | 60.763306 | 1.215437 | 60.717422 | recovered_timeout | both_timeout | 59.501985        | 0               | 0.147674              |

## 单实例稳定性检查：3sat_89.cnf

```text
calibrated single-run: INDETERMINATE, time = 60.1328s
pre-warmup skip single-run: pre_warmup_skip = 0, INDETERMINATE, time = 60.1361s
```

这说明 `3sat_89.cnf` 的 recovered_timeout 不是稳定收益样本。后续如果要让 selector 论文故事站稳，需要重复 seed / 重复运行下的稳定 recovery label，而不是只依赖单次 full400 结果。

## 下一步建议

1. 暂停继续调 pre-warmup skip classifier；当前收益量级小于 solver 运行噪声。
2. 对 6 个 recovered_timeout 做重复运行稳定性标注，把不稳定 recovery 从强正例中降权。
3. 重新训练 recovery detector：正例只保留多次重复中稳定 recovered 的实例，负例加入类似 `3sat_89.cnf` 的不稳定恢复。
4. 后续评估使用 repeated runs 或 bootstrap CI，否则 1 个 recovered 的随机漂移就会改变结论。

