# Clean Stability 与 Cactus 结果

本文档汇总优化后二进制下的 3SAT-300/350/400 干净运行结果。该脚本只使用已有 CSV 文件，不重新运行 solver。

生成产物：

- `figures/fig_clean_cactus_3sat_300_350_400.pdf`
- `figures/fig_clean_cactus_3sat_300.pdf`
- `figures/fig_clean_cactus_3sat_350.pdf`
- `figures/fig_clean_cactus_3sat_400.pdf`
- `runs/analysis/clean_metrics_summary.csv`
- `runs/analysis/clean_stability_vs_oneshot.csv`

## 平均指标

| size | method | n | solved | mean_time | median_time | mean_conflicts | mean_decisions |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 300 | one-shot | 200 | 200 | 7.4380 | 6.1297 | 256867.9900 | 290940.2800 |
| 300 | fixed-rho | 200 | 200 | 7.1805 | 5.4250 | 249771.6450 | 282893.7750 |
| 300 | polarity-gate-min095 | 200 | 200 | 7.1771 | 5.5808 | 249783.9350 | 282922.8100 |
| 300 | conservative SBE polarity | 200 | 200 | 7.2238 | 6.2364 | 251714.7200 | 285098.3800 |
| 350 | one-shot | 200 | 109 | 34.5387 | 47.7813 | 986915.0100 | 1119395.0800 |
| 350 | fixed-rho | 200 | 106 | 34.4262 | 46.4001 | 991704.2900 | 1125014.8700 |
| 350 | polarity-gate-min095 | 200 | 106 | 34.4484 | 46.8055 | 991098.0150 | 1124313.6800 |
| 350 | conservative SBE polarity | 200 | 110 | 33.7428 | 36.7334 | 969920.3150 | 1099996.9700 |
| 400 | one-shot | 200 | 51 | 47.7787 | 60.8190 | 1386665.3100 | 1583231.1600 |
| 400 | fixed-rho | 200 | 52 | 47.7746 | 60.8098 | 1392520.6100 | 1589403.9400 |
| 400 | polarity-gate-min095 | 200 | 53 | 47.8890 | 60.9701 | 1395525.3750 | 1592746.5200 |
| 400 | conservative SBE polarity | 200 | 48 | 47.9535 | 60.8347 | 1396852.4000 | 1594269.0800 |

## 相对 One-Shot 的稳定性

`delta_mean_time < 0` 表示快于 one-shot。bootstrap 是按实例配对的；split columns 反复采样 100-instance held-out subsets，用于模拟 split-level robustness。

| size | method | delta_mean_time | bootstrap_delta_time_ci_low | bootstrap_delta_time_ci_high | bootstrap_time_improve_prob | delta_solved | split_time_improve_rate | split_solved_improve_rate |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 300 | fixed-rho | -0.2575 | -0.5681 | -0.0108 | 0.9815 | 0 | 0.9585 | 0.0000 |
| 300 | polarity-gate-min095 | -0.2608 | -0.5798 | -0.0136 | 0.9840 | 0 | 0.9615 | 0.0000 |
| 300 | conservative SBE polarity | -0.2142 | -0.5251 | 0.0082 | 0.9695 | 0 | 0.9485 | 0.0000 |
| 350 | fixed-rho | -0.1125 | -0.9961 | 0.7386 | 0.6180 | -3 | 0.5800 | 0.0695 |
| 350 | polarity-gate-min095 | -0.0902 | -0.9756 | 0.7793 | 0.5880 | -3 | 0.5750 | 0.0670 |
| 350 | conservative SBE polarity | -0.7959 | -1.9679 | 0.2163 | 0.9325 | 1 | 0.9265 | 0.4980 |
| 400 | fixed-rho | -0.0040 | -1.1780 | 1.1268 | 0.5210 | 1 | 0.4920 | 0.5065 |
| 400 | polarity-gate-min095 | 0.1103 | -1.0292 | 1.2202 | 0.4135 | 2 | 0.4405 | 0.6685 |
| 400 | conservative SBE polarity | 0.1748 | -0.8241 | 1.3025 | 0.3615 | -3 | 0.3880 | 0.0295 |

## 解读

- fixed-rho 是稳定的 300 改善，但在 350/400 上较弱。
- polarity-gate-min095 是安全的，但基本跟随 fixed-rho。
- conservative SBE polarity 在 350 上有有用信号，但 400 结果为负；它应被视为假设，不应作为主 claim。

## 离线 Repeated Selector Split

这个额外检查在 3SAT-300/350 上随机抽取 50 次 100-per-size training splits，重新训练单特征线性 selector，然后在 held-out halves 上评估。它使用已有 `base_rho_mean` selector feature，但把 labels/times 替换成当前干净 one-shot 和 fixed-rho CSV。

| heldout | selector delta vs base | selector delta vs fixed-rho | better than base | better than fixed-rho | selected fraction |
|---|---:|---:|---:|---:|---:|
| 300+350 | -0.2203 [-0.5829, 0.0659] | -0.0216 [-0.3207, 0.4292] | 0.880 | 0.640 | 0.357 |
| 300 | -0.2276 [-0.4163, 0.0313] | 0.0240 [-0.0468, 0.3559] | 0.900 | 0.520 | 0.364 |
| 350 | -0.2130 [-0.7685, 0.3740] | -0.0672 [-0.6767, 0.7962] | 0.800 | 0.600 | 0.350 |

selector 在 held-out splits 上不能稳定超过 fixed-rho，因此应保留为消融/开放方向，而不是主方法。
