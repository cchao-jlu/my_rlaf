# Compact Stable Full400 正式评估

本次使用 `runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactStableRecovery300350400/best.pt` 在 `data/test/3sat/400/*.cnf` 上重新跑正式 wall-clock。

结论：stable checkpoint 相比 one-shot 仍然有收益，但没有超过旧 compact full400；offline repeated-split 的改善没有转化为更好的正式 full400 wall-clock。

## 方法汇总

| method | n | solved | mean_time | median_time | mean_cpu_time | mean_gpu_time | mean_conflicts |
| --- | --- | --- | --- | --- | --- | --- | --- |
| oneshot | 200 | 50 | 47.7517 | 60.7660 | 46.9441 | 0.8076 | 1360590.1800 |
| old_compact | 200 | 56 | 46.3484 | 60.8806 | 45.4296 | 0.8468 | 1310319.7850 |
| compact_stable | 200 | 54 | 46.6911 | 60.9922 | 45.6297 | 0.9890 | 1251788.9600 |

## 成对对比

| comparison | ref_solved | stable_solved | delta_solved | ref_mean_time | stable_mean_time | delta_mean_time | stable_faster | stable_slower | stable_recovered | stable_lost | both_timeout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| compact_stable_vs_oneshot | 50 | 54 | 4 | 47.7517 | 46.6911 | -1.0606 | 6 | 43 | 5 | 1 | 145 |
| compact_stable_vs_old_compact | 56 | 54 | -2 | 46.3484 | 46.6911 | 0.3427 | 4 | 42 | 0 | 2 | 144 |

## 关键判断

- 相比 one-shot：解出数 `+4`，平均时间 `-1.0606s`。
- 相比旧 compact：解出数 `-2`，平均时间 `0.3427s`。
- 因此当前 compact stable checkpoint 不能替代旧 compact 主线作为正式 full400 最优结果。
- 主要负面差异来自 `3sat_163.cnf` 和 `3sat_122.cnf` 这两个旧 compact 已解、stable 未解的样本，以及若干 easy/medium 已解样本的小幅慢化。

## Stable 相比旧 compact 的最大变化

| change_type | file_key | old_compact_result | compact_stable_result | old_compact_time | compact_stable_time | compact_stable_delta_time_vs_old_compact | outcome_vs_old_compact |
| --- | --- | --- | --- | --- | --- | --- | --- |
| largest_win | 3sat_140.cnf | SATISFIABLE | SATISFIABLE | 41.0826 | 5.2727 | -35.8099 | stable_faster |
| largest_win | 3sat_82.cnf | SATISFIABLE | SATISFIABLE | 36.0880 | 22.4765 | -13.6115 | stable_faster |
| largest_win | 3sat_93.cnf | SATISFIABLE | SATISFIABLE | 21.5550 | 19.5275 | -2.0274 | stable_faster |
| largest_win | 3sat_19.cnf | SATISFIABLE | SATISFIABLE | 3.9099 | 1.9352 | -1.9747 | stable_faster |
| largest_win | 3sat_23.cnf | INDETERMINATE | INDETERMINATE | 61.0240 | 60.9288 | -0.0953 | both_timeout |
| largest_win | 3sat_192.cnf | INDETERMINATE | INDETERMINATE | 61.0219 | 60.9333 | -0.0886 | both_timeout |
| largest_win | 3sat_26.cnf | INDETERMINATE | INDETERMINATE | 61.0387 | 60.9505 | -0.0882 | both_timeout |
| largest_win | 3sat_191.cnf | INDETERMINATE | INDETERMINATE | 61.0474 | 60.9654 | -0.0821 | both_timeout |
| largest_win | 3sat_2.cnf | INDETERMINATE | INDETERMINATE | 61.0112 | 60.9311 | -0.0801 | both_timeout |
| largest_win | 3sat_21.cnf | INDETERMINATE | INDETERMINATE | 61.0384 | 60.9619 | -0.0764 | both_timeout |
| largest_win | 3sat_194.cnf | INDETERMINATE | INDETERMINATE | 61.0406 | 60.9681 | -0.0726 | both_timeout |
| largest_win | 3sat_199.cnf | INDETERMINATE | INDETERMINATE | 61.0240 | 60.9586 | -0.0655 | both_timeout |
| largest_loss | 3sat_163.cnf | SATISFIABLE | INDETERMINATE | 29.2935 | 61.0179 | 31.7244 | stable_lost |
| largest_loss | 3sat_88.cnf | SATISFIABLE | SATISFIABLE | 1.0170 | 30.7041 | 29.6872 | stable_slower |
| largest_loss | 3sat_25.cnf | SATISFIABLE | SATISFIABLE | 1.9812 | 20.1904 | 18.2093 | stable_slower |
| largest_loss | 3sat_138.cnf | SATISFIABLE | SATISFIABLE | 52.3750 | 58.5870 | 6.2120 | stable_slower |
| largest_loss | 3sat_147.cnf | SATISFIABLE | SATISFIABLE | 11.7653 | 13.3861 | 1.6209 | stable_slower |
| largest_loss | 3sat_122.cnf | SATISFIABLE | INDETERMINATE | 59.4942 | 61.0111 | 1.5169 | stable_lost |
| largest_loss | 3sat_157.cnf | SATISFIABLE | SATISFIABLE | 27.9502 | 29.3851 | 1.4349 | stable_slower |
| largest_loss | 3sat_180.cnf | SATISFIABLE | SATISFIABLE | 14.3728 | 15.8051 | 1.4322 | stable_slower |
| largest_loss | 3sat_167.cnf | SATISFIABLE | SATISFIABLE | 11.1047 | 12.4773 | 1.3727 | stable_slower |
| largest_loss | 3sat_63.cnf | SATISFIABLE | SATISFIABLE | 4.9898 | 5.8440 | 0.8542 | stable_slower |
| largest_loss | 3sat_188.cnf | SATISFIABLE | SATISFIABLE | 26.3512 | 27.2002 | 0.8490 | stable_slower |
| largest_loss | 3sat_20.cnf | SATISFIABLE | SATISFIABLE | 10.8629 | 11.6017 | 0.7388 | stable_slower |

## 输出文件

- `runs/GNN_Glucose_3SAT_TwoStageRiskControllerCompactStableRecovery300350400/eval_compact_stable_full400.csv`
- `runs/analysis/compact_stable_full400_per_instance.csv`
- `runs/analysis/compact_stable_full400_summary.csv`
- `runs/analysis/compact_stable_full400_comparison.csv`
- `runs/analysis/compact_stable_full400_largest_changes.csv`
- `figures/fig_compact_stable_full400_cactus.pdf`
