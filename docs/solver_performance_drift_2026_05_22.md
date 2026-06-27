# Solver 性能漂移排查

日期：2026-05-22

## 现象

重新构建 `solvers/glucose_weighted/simp/glucose_release` 后，之前稳定的 3SAT-300 结果从约 `7s` mean time 退化到约 `29s` mean time：

| run | solved | mean time | mean CPU | mean conflicts |
|---|---:|---:|---:|---:|
| one-shot old | 200/200 | 7.5060 | 6.8972 | 256867.99 |
| one-shot bad rerun | 151/200 | 28.9624 | 28.3412 | 206926.56 |
| fixed-rho old | 200/200 | 7.1407 | 6.6095 | 249771.64 |
| fixed-rho bad rerun | 155/200 | 28.3860 | 27.7886 | 204129.90 |

实例级对比显示，已解实例的 decision/conflict counts 相同，但 CPU time 慢了约 `4-5x`。这说明问题来自 binary/runtime cost，而不是 search path 发生变化。

## 根因

weighted Glucose rebuild 时通过命令行传入 `CFLAGS`，意外覆盖了 Makefile release target 的优化 flag。dry run 显示编译命令没有 `-O3 -D NDEBUG`。

错误模式：

```bash
make r CFLAGS='-I/home/sunshixin/anaconda3/include ...'
```

因为 `CFLAGS` 在命令行提供，target-specific release flags 没有按预期应用。

同时修复了第二个问题：event counters 原先在 CDCL hot paths 中无条件更新。现在 solver 只有在传入 `-collect-events` 时才开启 event counting，Python 也只在 `collect-events=True` 时传该 flag。

## 修复后的构建

当前优化 binary 使用显式 release flags 重新构建：

```bash
make -B r \
  CFLAGS='-O3 -g -D NDEBUG -I/home/sunshixin/anaconda3/include -Wall -Wno-parentheses -std=c++11 -I/home/sunshixin/chenchao/my_rlaf/solvers/glucose_weighted -D __STDC_LIMIT_MACROS -D __STDC_FORMAT_MACROS' \
  LFLAGS='-Wall -lpthread -L/home/sunshixin/anaconda3/lib -Wl,-rpath,/home/sunshixin/anaconda3/lib -lz'
```

binary：

```text
solvers/glucose_weighted/simp/glucose_release
sha256: bb9ff6f661aeaa91e0274e09d0977793ff3633846e05617093f9f6e1e2689865
```

## 干净 3SAT-300 Baselines

下面所有行都在优化 rebuild 和 event gating 修复后重新运行。

| method | solved | mean time | median | p75 | p95 | mean CPU | mean conflicts | mean decisions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| one-shot | 200/200 | 7.4380 | 6.1297 | 11.5107 | 22.2161 | 6.9007 | 256867.99 | 290940.28 |
| fixed-rho | 200/200 | 7.1805 | 5.4250 | 10.9844 | 21.9165 | 6.5972 | 249771.64 | 282893.78 |
| polarity gate min 0.95 | 200/200 | 7.1771 | 5.5808 | 11.0736 | 21.1740 | 6.5898 | 249783.93 | 282922.81 |
| SBE polarity | 200/200 | 7.3222 | 5.8886 | 11.0281 | 21.3345 | 6.7443 | 256761.80 | 290753.88 |
| conservative SBE polarity | 200/200 | 7.2238 | 6.2364 | 11.0914 | 21.6906 | 6.6144 | 251714.72 | 285098.38 |

## 干净 3SAT-350/400 Baselines

更大规模 baseline 使用同一个优化 binary hash。运行参数为 `solver.num_workers=8`、`cpu-lim=60`、`rnd-freq=0.0`、`K=0.1`。

| size | method | solved | mean time | median | p75 | p95 | mean CPU | mean conflicts | mean decisions |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 350 | one-shot | 109/200 | 34.5387 | 47.7813 | 60.6804 | 60.7027 | 33.8381 | 986915.01 | 1119395.08 |
| 350 | fixed-rho | 106/200 | 34.4262 | 46.4001 | 60.6631 | 60.7674 | 33.7525 | 991704.29 | 1125014.87 |
| 350 | polarity gate min 0.95 | 106/200 | 34.4484 | 46.8055 | 60.7011 | 60.7434 | 33.7683 | 991098.02 | 1124313.68 |
| 350 | conservative SBE polarity | 110/200 | 33.7428 | 36.7334 | 60.6980 | 60.7486 | 33.0420 | 969920.31 | 1099996.97 |
| 400 | one-shot | 51/200 | 47.7787 | 60.8190 | 60.8589 | 60.9699 | 46.9059 | 1386665.31 | 1583231.16 |
| 400 | fixed-rho | 52/200 | 47.7746 | 60.8098 | 60.9620 | 61.0233 | 46.8679 | 1392520.61 | 1589403.94 |
| 400 | polarity gate min 0.95 | 53/200 | 47.8890 | 60.9701 | 60.9915 | 61.0127 | 46.9079 | 1395525.38 | 1592746.52 |
| 400 | conservative SBE polarity | 48/200 | 47.9535 | 60.8347 | 60.9181 | 60.9579 | 47.0743 | 1396852.40 | 1594269.08 |

CSV 文件：

- `runs/GNN_Glucose_3SAT_V1/eval_oneshot_350_optimized_events_gated.csv`
- `runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_RhoGateM024/eval_trace_adapter_rho_gate_350_optimized_events_gated.csv`
- `runs/GNN_Glucose_3SAT_TraceAdapter_PolarityGateMin095/eval_polarity_gate_min095_350_optimized_events_gated.csv`
- `runs/GNN_Glucose_3SAT_TraceAdapter_SBEPolarityConservative/eval_sbe_polarity_conservative_350_optimized_events_gated.csv`
- `runs/GNN_Glucose_3SAT_V1/eval_oneshot_400_optimized_events_gated.csv`
- `runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_RhoGateM024/eval_trace_adapter_rho_gate_400_optimized_events_gated.csv`
- `runs/GNN_Glucose_3SAT_TraceAdapter_PolarityGateMin095/eval_polarity_gate_min095_400_optimized_events_gated.csv`
- `runs/GNN_Glucose_3SAT_TraceAdapter_SBEPolarityConservative/eval_sbe_polarity_conservative_400_optimized_events_gated.csv`

稳定性和 cactus-plot 后续结果：

- `docs/clean_stability_and_cactus_results.md`
- `figures/fig_clean_cactus_3sat_300_350_400.pdf`
- `runs/analysis/clean_stability_vs_oneshot.csv`

## 结论

灾难性的 `28-29s` polarity/SBE 结果无效，因为它们是在未优化 weighted Glucose binary 上测得的。正确 rebuild 后，主要结论是：

- fixed-rho 仍是 3SAT-300 上最强的干净 baseline。
- polarity-gate-min095 是安全的，但几乎与 fixed-rho 相同。
- SBE polarity 不再是灾难性结果，但在 3SAT-300 上没有超过 fixed-rho。
- 3SAT-350 上，conservative SBE polarity 相比 one-shot（`109/200`，`34.5387s`）和 fixed-rho（`106/200`，`34.4262s`）有小幅正信号（`110/200`，`33.7428s`）。
- 3SAT-400 上该信号没有迁移：conservative SBE polarity 降到 `48/200` solved 和 `47.9535s`；polarity-gate-min095 虽然解出 `53/200`，但平均时间和搜索计数略差于 fixed-rho。
- 总体看，polarity-conditioned variants 已经足够安全，可以评估，但尚未提供稳健的大规模改善。
- 后续实验必须使用上面的 optimized binary hash，或者在结果表中记录新的 binary hash。
