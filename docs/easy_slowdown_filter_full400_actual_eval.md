# Full400 Calibrated Slowdown Filter 正式评估

本次重新运行 `runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400_EasySlowdownFilterFull400Calibrated`，不再只使用离线估算。

## 输出文件

- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactRiskEvidence300350400_EasySlowdownFilterFull400Calibrated/eval_easy_slowdown_filter_full400_calibrated.csv`
- `runs/analysis/easy_slowdown_filter_full400_actual_per_instance.csv`
- `runs/analysis/easy_slowdown_filter_full400_actual_summary.csv`
- `runs/analysis/easy_slowdown_filter_full400_actual_bucket_summary.csv`
- `runs/analysis/easy_slowdown_filter_full400_actual_key_cases.csv`

## 总体结果

| n   | base_solved | compact_solved | cal_solved | cal_delta_solved_vs_base | base_mean_time | compact_mean_time | cal_mean_time | cal_delta_vs_base | cal_delta_vs_compact | compact_recovered_timeout | cal_recovered_timeout | compact_slowdown | cal_slowdown | compact_faster | cal_faster | cal_selector_selected |
| --- | ----------- | -------------- | ---------- | ------------------------ | -------------- | ----------------- | ------------- | ----------------- | -------------------- | ------------------------- | --------------------- | ---------------- | ------------ | -------------- | ---------- | --------------------- |
| 200 | 50          | 56             | 56         | 6                        | 47.7517        | 46.3484           | 46.3465       | -1.4051           | -0.0018              | 6                         | 6                     | 33               | 35           | 6              | 5          | 39                    |

## Bucket 结果

| difficulty_bucket | n   | base_solved | compact_solved | cal_solved | compact_delta_mean | cal_delta_mean | compact_slowdown | cal_slowdown | cal_recovered |
| ----------------- | --- | ----------- | -------------- | ---------- | ------------------ | -------------- | ---------------- | ------------ | ------------- |
| easy(<10s)        | 37  | 37          | 37             | 37         | 0.7615             | 0.7928         | 26               | 28           | 0             |
| hard(>=30s)       | 4   | 4           | 4              | 4          | -7.1781            | -7.3562        | 2                | 1            | 0             |
| medium(10-30s)    | 9   | 9           | 9              | 9          | -1.8766            | -2.1632        | 5                | 6            | 0             |
| timeout           | 150 | 0           | 6              | 6          | -1.7549            | -1.7431        | 0                | 0            | 6             |

## 关键实例

| file_key     | difficulty_bucket | base_time | compact_time | cal_time | compact_outcome    | cal_outcome        | compact_delta_time | cal_delta_time | risk_prob | recovery_prob | slowdown_prob | cal_selector_use_adapter |
| ------------ | ----------------- | --------- | ------------ | -------- | ------------------ | ------------------ | ------------------ | -------------- | --------- | ------------- | ------------- | ------------------------ |
| 3sat_49.cnf  | timeout           | 60.7917   | 60.8551      | 60.8573  | both_timeout       | both_timeout       | 0.0634             | 0.0656         | 0.7532    | 0.9421        | 0.2954        | 0                        |
| 3sat_53.cnf  | timeout           | 60.7938   | 60.8565      | 60.8551  | both_timeout       | both_timeout       | 0.0626             | 0.0613         | 0.7146    | 0.6363        | 0.3398        | 0                        |
| 3sat_163.cnf | timeout           | 60.8197   | 29.2935      | 29.5056  | recovered_timeout  | recovered_timeout  | -31.5262           | -31.3141       | 0.6994    | 0.7594        | 0.1361        | 1                        |
| 3sat_188.cnf | timeout           | 60.8011   | 26.3512      | 26.0617  | recovered_timeout  | recovered_timeout  | -34.4499           | -34.7395       | 0.2586    | 0.9113        | 0.0024        | 1                        |
| 3sat_189.cnf | timeout           | 60.7532   | 14.8203      | 14.5831  | recovered_timeout  | recovered_timeout  | -45.9329           | -46.1701       | 0.5888    | 0.7464        | 0.0846        | 1                        |
| 3sat_85.cnf  | timeout           | 60.7717   | 1.4759       | 1.6881   | recovered_timeout  | recovered_timeout  | -59.2958           | -59.0836       | 0.4059    | 0.8527        | 0.0114        | 1                        |
| 3sat_89.cnf  | timeout           | 60.7633   | 0.9720       | 1.2154   | recovered_timeout  | recovered_timeout  | -59.7913           | -59.5479       | 0.5936    | 0.6033        | 0.0943        | 1                        |
| 3sat_97.cnf  | timeout           | 60.7605   | 12.4787      | 12.4590  | recovered_timeout  | recovered_timeout  | -48.2818           | -48.3015       | 0.5298    | 0.6045        | 0.0782        | 1                        |
| 3sat_157.cnf | easy(<10s)        | 3.2106    | 27.9502      | 28.1868  | slower_both_solved | slower_both_solved | 24.7396            | 24.9761        | 0.5241    | 0.6470        | 0.0452        | 1                        |
| 3sat_82.cnf  | medium(10-30s)    | 21.4710   | 36.0880      | 35.8673  | slower_both_solved | slower_both_solved | 14.6170            | 14.3963        | 0.7791    | 0.7432        | 0.2765        | 0                        |
| 3sat_93.cnf  | medium(10-30s)    | 18.8329   | 21.5550      | 19.4732  | slower_both_solved | slower_both_solved | 2.7221             | 0.6403         | 0.7520    | 0.7347        | 0.2880        | 0                        |

## 结论

- 实际 wall-clock 与离线估算在总体均值上基本一致：`46.3465s`，原 compact 为 `46.3484s`。
- solved count 仍为 `56 / 200`，相对 one-shot 保持 `+6`，6 个 recovered timeout 全部保住。
- selector 特征抽取显示 calibrated filter 将 `3sat_82.cnf`、`3sat_93.cnf`、`3sat_49.cnf`、`3sat_53.cnf` 的 adapter residual 关闭。
- 但正式 wall-clock 中 `3sat_82.cnf` 仍保持明显 slowdown，说明 post-warmup veto 只关闭 residual，不跳过 warmup，也不保证回到 one-shot 的搜索轨迹。
- 因此这个 filter 的实际收益主要体现在 `3sat_93.cnf` 从 `+2.72s` 降到 `+0.64s`，总体均值只比原 compact 快约 `0.0018s`。
- 若目标是减少 27 个未开 adapter 的 easy/medium 小幅 slowdown，下一步必须做 pre-warmup skip gate，而不是继续调 post-warmup filter。
