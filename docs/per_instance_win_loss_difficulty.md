# 实例级 Win/Loss 与难度分桶报告

本文档在相同 CNF 实例上，将优化后二进制的干净运行结果与 one-shot baseline 对比。对于两种方法都能解出的实例，win/loss 阈值设为 `0.1s`。timeout recovery 计为 win，lost solution 计为 loss。

生成 CSV：

- `runs/analysis/per_instance_method_deltas.csv`
- `runs/analysis/per_instance_win_loss_summary.csv`
- `runs/analysis/difficulty_bucket_summary.csv`
- `runs/analysis/largest_instance_changes.csv`

## 总体 Win/Loss

| size | method | wins | losses | neutral | recovered_timeout | lost_solution | delta_solved | delta_mean_time | median_delta_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 300 | fixed-rho | 48 | 49 | 103 | 0 | 0 | 0 | -0.2575 | 0.0450 |
| 300 | polarity-gate-min095 | 54 | 63 | 83 | 0 | 0 | 0 | -0.2608 | 0.0509 |
| 300 | conservative SBE polarity | 57 | 60 | 83 | 0 | 0 | 0 | -0.2142 | 0.0439 |
| 350 | fixed-rho | 30 | 30 | 140 | 2 | 5 | -3 | -0.1125 | -0.0084 |
| 350 | polarity-gate-min095 | 32 | 29 | 139 | 2 | 5 | -3 | -0.0902 | 0.0210 |
| 350 | conservative SBE polarity | 28 | 25 | 147 | 4 | 3 | 1 | -0.7959 | 0.0254 |
| 400 | fixed-rho | 17 | 26 | 157 | 4 | 3 | 1 | -0.0040 | -0.0349 |
| 400 | polarity-gate-min095 | 11 | 35 | 154 | 4 | 2 | 2 | 0.1103 | 0.1433 |
| 400 | conservative SBE polarity | 14 | 17 | 169 | 1 | 4 | -3 | 0.1748 | 0.0079 |

## 难度分桶

bucket 按 one-shot baseline 行为定义：`10s` 内解出、`10-30s` 解出、`30s` 后解出，或 timeout。

| size | method | bucket | n | delta_solved | delta_mean_time | wins | losses | recovered_timeout | lost_solution | both_timeout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 300 | fixed-rho | easy(<10s) | 139 | 0 | -0.0156 | 21 | 24 | 0 | 0 | 0 |
| 300 | fixed-rho | medium(10-30s) | 59 | 0 | -0.6033 | 26 | 25 | 0 | 0 | 0 |
| 300 | fixed-rho | hard(>=30s) | 2 | 0 | -6.8682 | 1 | 0 | 0 | 0 | 0 |
| 300 | polarity-gate-min095 | easy(<10s) | 139 | 0 | 0.0082 | 24 | 41 | 0 | 0 | 0 |
| 300 | polarity-gate-min095 | medium(10-30s) | 59 | 0 | -0.6552 | 28 | 22 | 0 | 0 | 0 |
| 300 | polarity-gate-min095 | hard(>=30s) | 2 | 0 | -7.3210 | 2 | 0 | 0 | 0 | 0 |
| 300 | conservative SBE polarity | easy(<10s) | 139 | 0 | 0.0141 | 19 | 43 | 0 | 0 | 0 |
| 300 | conservative SBE polarity | medium(10-30s) | 59 | 0 | -0.3272 | 36 | 17 | 0 | 0 | 0 |
| 300 | conservative SBE polarity | hard(>=30s) | 2 | 0 | -12.7464 | 2 | 0 | 0 | 0 | 0 |
| 350 | fixed-rho | easy(<10s) | 71 | 0 | 0.0200 | 14 | 11 | 0 | 0 | 0 |
| 350 | fixed-rho | medium(10-30s) | 16 | -1 | 2.5460 | 6 | 7 | 0 | 1 | 0 |
| 350 | fixed-rho | hard(>=30s) | 22 | -4 | -0.7645 | 8 | 12 | 0 | 4 | 0 |
| 350 | fixed-rho | timeout | 91 | 2 | -0.5257 | 2 | 0 | 2 | 0 | 89 |
| 350 | polarity-gate-min095 | easy(<10s) | 71 | 0 | 0.0387 | 19 | 9 | 0 | 0 | 0 |
| 350 | polarity-gate-min095 | medium(10-30s) | 16 | -1 | 2.7138 | 5 | 8 | 0 | 1 | 0 |
| 350 | polarity-gate-min095 | hard(>=30s) | 22 | -4 | -0.7103 | 6 | 12 | 0 | 4 | 0 |
| 350 | polarity-gate-min095 | timeout | 91 | 2 | -0.5340 | 2 | 0 | 2 | 0 | 89 |
| 350 | conservative SBE polarity | easy(<10s) | 71 | 0 | 0.5419 | 7 | 6 | 0 | 0 | 0 |
| 350 | conservative SBE polarity | medium(10-30s) | 16 | 0 | -0.6885 | 7 | 8 | 0 | 0 | 0 |
| 350 | conservative SBE polarity | hard(>=30s) | 22 | -3 | -2.1411 | 10 | 11 | 0 | 3 | 0 |
| 350 | conservative SBE polarity | timeout | 91 | 4 | -1.5334 | 4 | 0 | 4 | 0 | 87 |
| 400 | fixed-rho | easy(<10s) | 37 | -1 | 3.9211 | 7 | 20 | 0 | 1 | 0 |
| 400 | fixed-rho | medium(10-30s) | 9 | -1 | 0.7037 | 3 | 5 | 0 | 1 | 0 |
| 400 | fixed-rho | hard(>=30s) | 5 | -1 | -6.0382 | 3 | 1 | 0 | 1 | 0 |
| 400 | fixed-rho | timeout | 149 | 4 | -0.8190 | 4 | 0 | 4 | 0 | 145 |
| 400 | polarity-gate-min095 | easy(<10s) | 37 | -1 | 4.0001 | 2 | 27 | 0 | 1 | 0 |
| 400 | polarity-gate-min095 | medium(10-30s) | 9 | -1 | 0.5778 | 4 | 4 | 0 | 1 | 0 |
| 400 | polarity-gate-min095 | hard(>=30s) | 5 | 0 | -5.0431 | 1 | 4 | 0 | 0 | 0 |
| 400 | polarity-gate-min095 | timeout | 149 | 4 | -0.7109 | 4 | 0 | 4 | 0 | 145 |
| 400 | conservative SBE polarity | easy(<10s) | 37 | -1 | 1.7338 | 4 | 12 | 0 | 1 | 0 |
| 400 | conservative SBE polarity | medium(10-30s) | 9 | -2 | 6.2675 | 5 | 4 | 0 | 2 | 0 |
| 400 | conservative SBE polarity | hard(>=30s) | 5 | -1 | -6.1821 | 4 | 1 | 0 | 1 | 0 |
| 400 | conservative SBE polarity | timeout | 149 | 1 | -0.3670 | 1 | 0 | 1 | 0 | 148 |

## 最大实例级变化

下面例子聚焦最模糊但最重要的信号：3SAT-350 和 3SAT-400 上的 conservative SBE polarity。

| change_type | file_key | difficulty_bucket | base_result | method_result | base_time | method_time | delta_time | outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| largest_win | 3sat_95.cnf | timeout | INDETERMINATE | SATISFIABLE | 60.7077 | 4.1039 | -56.6039 | recovered_timeout |
| largest_win | 3sat_103.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 54.5990 | 5.0339 | -49.5651 | faster_both_solved |
| largest_win | 3sat_12.cnf | timeout | INDETERMINATE | SATISFIABLE | 60.6663 | 21.0081 | -39.6582 | recovered_timeout |
| largest_win | 3sat_6.cnf | timeout | INDETERMINATE | SATISFIABLE | 60.6831 | 21.0606 | -39.6225 | recovered_timeout |
| largest_win | 3sat_51.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 58.3018 | 30.8929 | -27.4089 | faster_both_solved |
| largest_loss | 3sat_1.cnf | hard(>=30s) | SATISFIABLE | INDETERMINATE | 30.2935 | 60.7851 | 30.4916 | lost_solution |
| largest_loss | 3sat_167.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 4.2195 | 33.1971 | 28.9776 | slower_both_solved |
| largest_loss | 3sat_78.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 21.9803 | 30.5716 | 8.5913 | slower_both_solved |
| largest_loss | 3sat_135.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 5.2364 | 13.0866 | 7.8502 | slower_both_solved |
| largest_loss | 3sat_112.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 10.8949 | 17.3852 | 6.4903 | slower_both_solved |
| largest_win | 3sat_90.cnf | timeout | INDETERMINATE | SATISFIABLE | 60.8352 | 6.8552 | -53.9801 | recovered_timeout |
| largest_win | 3sat_46.cnf | hard(>=30s) | SATISFIABLE | SATISFIABLE | 30.0845 | 3.1603 | -26.9242 | faster_both_solved |
| largest_win | 3sat_128.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 28.0889 | 9.0235 | -19.0654 | faster_both_solved |
| largest_win | 3sat_82.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 20.9361 | 8.7233 | -12.2128 | faster_both_solved |
| largest_win | 3sat_93.cnf | medium(10-30s) | SATISFIABLE | SATISFIABLE | 18.9361 | 13.7746 | -5.1616 | faster_both_solved |
| largest_loss | 3sat_86.cnf | easy(<10s) | SATISFIABLE | INDETERMINATE | 3.2547 | 60.8389 | 57.5842 | lost_solution |
| largest_loss | 3sat_167.cnf | medium(10-30s) | SATISFIABLE | INDETERMINATE | 10.8118 | 60.9210 | 50.1092 | lost_solution |
| largest_loss | 3sat_54.cnf | medium(10-30s) | SATISFIABLE | INDETERMINATE | 18.1220 | 60.7670 | 42.6450 | lost_solution |
| largest_loss | 3sat_14.cnf | easy(<10s) | SATISFIABLE | SATISFIABLE | 4.8612 | 10.4625 | 5.6012 | slower_both_solved |
| largest_loss | 3sat_148.cnf | hard(>=30s) | SATISFIABLE | INDETERMINATE | 59.7224 | 60.9161 | 1.1938 | lost_solution |

## 解读

- fixed-rho 主要通过压低已解 easy/medium/hard 实例的时间来帮助 3SAT-300；它没有恢复新的 hard timeouts。
- 在 3SAT-350 上，conservative SBE polarity 的收益主要来自 timeout bucket：它恢复的 one-shot timeouts 多于丢失的 solved instances。
- 在 3SAT-400 上，conservative SBE polarity 丢失 solved instances，且没有足够 timeout recovery 抵消，因此 350 信号不具备 scale robustness。
- 未来 selector 应作为 risk controller 训练：预测 event guidance 何时可能恢复 timeout/hard instances，同时不丢 already-solvable instances，而不是只预测小幅 runtime gain。
