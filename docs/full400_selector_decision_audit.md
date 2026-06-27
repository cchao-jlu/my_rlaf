# Full400 Selector 决策审计

本审计固定 full400 的同一份 warmup/event feature cache，分别套用旧 compact 和 compact stable 的线性 risk/recovery selector。
因此这里看的是 selector 边界差异本身，不重新引入 solver rollout 噪声。

## 结论

- 旧 compact 仍作为当前主线结果保留：`56/200, 46.3484s`。
- compact stable：`54/200, 46.6911s`，不能替换主线。
- stable 的主要问题不是整体模型表达力，而是 full400 上 decision boundary 发生了不稳定位移：risk threshold 更严格会关掉部分旧 compact 的有效 adapter，同时 recovery threshold 更宽松又会打开部分 easy/medium 风险样本。
- `3sat_163.cnf` 是典型漏开样本：old 开启 adapter，stable 关闭 adapter，结果从 SAT 变成 timeout。
- `3sat_88.cnf` 和 `3sat_25.cnf` 是典型误开样本：old 关闭 adapter，stable 打开 adapter，导致明显慢化。

## 决策变化汇总

| decision_change | n | old_solved | stable_solved | delta_solved | delta_mean_time_vs_old | stable_faster | stable_slower | stable_lost | stable_recovered | both_timeout |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| both_off | 139 | 33 | 32 | -1 | 0.2382 | 0 | 28 | 1 | 0 | 106 |
| both_on | 36 | 14 | 14 | 0 | 0.1367 | 1 | 11 | 0 | 0 | 22 |
| stable_closed | 8 | 3 | 2 | -1 | 2.1151 | 2 | 0 | 1 | 0 | 5 |
| stable_opened | 17 | 6 | 6 | 0 | 0.7996 | 1 | 3 | 0 | 0 | 11 |

## 重点实例

| file_key | old_compact_result | compact_stable_result | old_compact_time | compact_stable_time | compact_stable_delta_time_vs_old_compact | old_risk_prob | old_recovery_prob | old_use_adapter | stable_risk_prob | stable_recovery_prob | stable_use_adapter | decision_change | outcome_vs_old_compact | diagnosis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_122.cnf | SATISFIABLE | INDETERMINATE | 59.4942 | 61.0111 | 1.5169 | 0.7968 | 0.3563 | 0 | 0.7968 | 0.4394 | 0 | both_off | stable_lost | 两者都关闭，差异主要来自 one-shot/运行噪声 |
| 3sat_140.cnf | SATISFIABLE | SATISFIABLE | 41.0826 | 5.2727 | -35.8099 | 0.2927 | 0.4226 | 0 | 0.2927 | 0.6932 | 1 | stable_opened | stable_faster | stable 新开 adapter 后加速 |
| 3sat_163.cnf | SATISFIABLE | INDETERMINATE | 29.2935 | 61.0179 | 31.7244 | 0.6994 | 0.7600 | 1 | 0.6994 | 0.6826 | 0 | stable_closed | stable_lost | stable 关掉 adapter 后丢解 |
| 3sat_25.cnf | SATISFIABLE | SATISFIABLE | 1.9812 | 20.1904 | 18.2093 | 0.5259 | 0.5142 | 0 | 0.5259 | 0.7150 | 1 | stable_opened | stable_slower | stable 新开 adapter 后慢化 |
| 3sat_82.cnf | SATISFIABLE | SATISFIABLE | 36.0880 | 22.4765 | -13.6115 | 0.7791 | 0.7452 | 1 | 0.7791 | 0.8254 | 0 | stable_closed | stable_faster | stable 关掉 adapter 后加速 |
| 3sat_88.cnf | SATISFIABLE | SATISFIABLE | 1.0170 | 30.7041 | 29.6872 | 0.5932 | 0.4620 | 0 | 0.5932 | 0.6397 | 1 | stable_opened | stable_slower | stable 新开 adapter 后慢化 |

## 最大负面样本

| file_key | decision_change | outcome_vs_old_compact | old_compact_time | compact_stable_time | compact_stable_delta_time_vs_old_compact | old_risk_prob | old_recovery_prob | old_use_adapter | stable_risk_prob | stable_recovery_prob | stable_use_adapter | diagnosis |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_163.cnf | stable_closed | stable_lost | 29.2935 | 61.0179 | 31.7244 | 0.6994 | 0.7600 | 1 | 0.6994 | 0.6826 | 0 | stable 关掉 adapter 后丢解 |
| 3sat_88.cnf | stable_opened | stable_slower | 1.0170 | 30.7041 | 29.6872 | 0.5932 | 0.4620 | 0 | 0.5932 | 0.6397 | 1 | stable 新开 adapter 后慢化 |
| 3sat_25.cnf | stable_opened | stable_slower | 1.9812 | 20.1904 | 18.2093 | 0.5259 | 0.5142 | 0 | 0.5259 | 0.7150 | 1 | stable 新开 adapter 后慢化 |
| 3sat_138.cnf | both_off | stable_slower | 52.3750 | 58.5870 | 6.2120 | 0.2603 | 0.0381 | 0 | 0.2603 | 0.1421 | 0 | 两者都关闭，差异主要来自 one-shot/运行噪声 |
| 3sat_147.cnf | both_off | stable_slower | 11.7653 | 13.3861 | 1.6209 | 0.8815 | 0.0348 | 0 | 0.8815 | 0.2178 | 0 | 两者都关闭，差异主要来自 one-shot/运行噪声 |
| 3sat_122.cnf | both_off | stable_lost | 59.4942 | 61.0111 | 1.5169 | 0.7968 | 0.3563 | 0 | 0.7968 | 0.4394 | 0 | 两者都关闭，差异主要来自 one-shot/运行噪声 |
| 3sat_157.cnf | both_on | stable_slower | 27.9502 | 29.3851 | 1.4349 | 0.5241 | 0.6128 | 1 | 0.5241 | 0.7275 | 1 | 两者都开启，差异主要来自求解随机/阈值外因素 |
| 3sat_180.cnf | both_off | stable_slower | 14.3728 | 15.8051 | 1.4322 | 0.2196 | 0.0035 | 0 | 0.2196 | 0.0472 | 0 | 两者都关闭，差异主要来自 one-shot/运行噪声 |
| 3sat_167.cnf | both_off | stable_slower | 11.1047 | 12.4773 | 1.3727 | 0.8325 | 0.2137 | 0 | 0.8325 | 0.4722 | 0 | 两者都关闭，差异主要来自 one-shot/运行噪声 |
| 3sat_63.cnf | both_off | stable_slower | 4.9898 | 5.8440 | 0.8542 | 0.7416 | 0.1447 | 0 | 0.7416 | 0.4816 | 0 | 两者都关闭，差异主要来自 one-shot/运行噪声 |
| 3sat_188.cnf | both_on | stable_slower | 26.3512 | 27.2002 | 0.8490 | 0.2586 | 0.9267 | 1 | 0.2586 | 0.9219 | 1 | 两者都开启，差异主要来自求解随机/阈值外因素 |
| 3sat_20.cnf | both_off | stable_slower | 10.8629 | 11.6017 | 0.7388 | 0.4751 | 0.0902 | 0 | 0.4751 | 0.3838 | 0 | 两者都关闭，差异主要来自 one-shot/运行噪声 |

## 输出文件

- `runs/analysis/full400_selector_decision_audit.csv`
- `runs/analysis/full400_selector_decision_audit_focus.csv`
- `runs/analysis/full400_selector_decision_audit_summary.csv`
