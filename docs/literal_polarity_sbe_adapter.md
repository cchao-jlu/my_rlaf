# Literal-Polarity Event State 与 SBE Adapter

本文档记录阅读 `参考.md` 后新增的 literal-level polarity event state 与 SBE adapter 实现。

## Literal-Polarity 事件

当启用 `collect-events` 时，`glucose_weighted` 现在会额外输出 per-variable positive/negative literal event counters：

- `event_var_pos_decisions`
- `event_var_neg_decisions`
- `event_var_pos_propagations`
- `event_var_neg_propagations`
- `event_var_pos_conflict_lits`
- `event_var_neg_conflict_lits`
- `event_var_pos_assignments`
- `event_var_neg_assignments`

Python event encoder 新增 `feature_mode="polarity"`，把 20 维 enhanced state 扩展到 29 维：

- 原始 enhanced 20 个特征
- positive conflict rate
- negative conflict rate
- conflict polarity bias
- positive propagation rate
- negative propagation rate
- propagation polarity bias
- positive assignment rate
- negative assignment rate
- assignment polarity bias

polarity bias 定义为：

```text
(positive_count - negative_count) / (positive_count + negative_count + eps)
```

其取值保持在 `[-1, 1]`。

## SBE Gated-Fusion Adapter 结构

`model.event_adapter.fusion` 现在支持两种模式：

- `residual`：已有 adapter，`MLP(concat(h_x, e_t, g_t)) -> delta`
- `sbe`：static embedding 与 dynamic embedding 的 gated fusion

SBE adapter 计算：

```text
f_dynamic = LeakyReLU(W_event [e_t(x) || g_t])
gate = sigmoid(W_gate [h_x || f_dynamic])
m_x = gate * h_x + (1 - gate) * f_dynamic
delta = W_head m_x
```

residual 输出仍使用已有 adapter controls 做 clip/scale，并且原有 per-variable/graph-level gates 仍可继续叠加。

## 配置

生成 polarity trace data：

```bash
python generate_trace_distillation_data.py --config-name config_generate_trace_distillation_polarity \
  from_checkpoint=runs/GNN_Glucose_3SAT_V1/best.pt \
  dataset.path='data/training/3sat/*/*.cnf'
```

训练 SBE polarity adapter：

```bash
python train_trace_distill.py --config-name config_train_trace_distill_sbe_polarity \
  from_checkpoint=runs/GNN_Glucose_3SAT_V1/best.pt \
  trace.data_path=data/trace_distill/train_trace_polarity.pt
```

评估：

```bash
python evaluate_guided_solver.py --config-name config_eval_guided_solver_sbe_polarity \
  dataset.eval_path='data/test/3sat/350/*.cnf'
```

## 意义

当前 fixed rho gate 在 300/350 上有帮助，但没有解决 400 长尾。literal polarity events 直接告诉 adapter 正/负文字赋值是否更容易引发冲突；SBE gated fusion 则把 solver events 转成 dynamic embedding，而不是只把 event features 拼到 residual MLP。这个实现最接近 `参考.md` 中的 `Search-induced symmetry breaking` 叙事。

## 初始训练结果

小规模 polarity trace 生成和训练成功完成：

- small trace：`data/trace_distill/train_trace_polarity_small_200.pt`
- small checkpoint：`runs/GNN_Glucose_3SAT_TraceAdapter_SBEPolaritySmall200/best.pt`
- small heldout-300 sanity evaluation：技术上稳定，但 mean time 为 `30.48`，性能上没有价值。

完整 polarity trace 生成和 SBE adapter 训练也成功完成：

- full trace：`data/trace_distill/train_trace_polarity.pt`
- full trace stats：`data/trace_distill/train_trace_polarity_stats.csv`
- full checkpoint：`runs/GNN_Glucose_3SAT_TraceAdapter_SBEPolarity/best.pt`
- training loss：20 epochs 内从 `4.2431` 到 `4.2097`

但第一版 full checkpoint 在 3SAT-300 上评估严重失败：

| method | size | n | solved | mean time | median time | mean conflicts | mean decisions |
|---|---:|---:|---:|---:|---:|---:|---:|
| one-shot baseline | 300 | 200 | 200 | 7.5060 | 6.3091 | 256867.99 | 290940.28 |
| fixed rho gate | 300 | 200 | 200 | 7.1407 | 5.4279 | 249771.64 | 282893.78 |
| SBE polarity | 300 | 200 | 152 | 29.0690 | 28.7944 | 208635.22 | 236518.03 |

由于 3SAT-300 已经从 `200/200` solved 退化到 `152/200`，该 checkpoint 没有继续跑 350/400。

## Solver Drift 修复后的修正诊断

最初 `28-29s` 的 SBEPolarity 结果来自意外未优化的 weighted Glucose binary。该 binary rebuild 时使用命令行 `CFLAGS` 覆盖了 release target 的 `-O3 -D NDEBUG` flags。详情见 `docs/solver_performance_drift_2026_05_22.md`。

重新用显式优化 flags 构建 solver，并把 event collection 放到 `-collect-events` 后，重新运行 3SAT-300：

| method | size | n | solved | mean time | median time |
|---|---:|---:|---:|---:|---:|
| one-shot | 300 | 200 | 200 | 7.4380 | 6.1297 |
| fixed rho gate | 300 | 200 | 200 | 7.1805 | 5.4250 |
| SBE polarity | 300 | 200 | 200 | 7.3222 | 5.8886 |
| conservative SBE polarity | 300 | 200 | 200 | 7.2238 | 6.2364 |
| polarity gate min 0.95 | 300 | 200 | 200 | 7.1771 | 5.5808 |

修正后的结论更窄：

- 正确 solver build 下，direct SBE polarity 不是灾难性错误，但仍没有超过 fixed-rho baseline。
- conservative SBE polarity 接近 fixed-rho，但也没有明确改善。
- polarity-gated fixed-rho 是安全的，基本保留 fixed-rho 行为；3SAT-300 上收益很小。

## 被 Bad Solver Build 推翻的旧诊断

实现路径是稳定的，但训练目标还不够安全。可能问题是：SBE gated fusion 比之前的 residual concat adapter 表达力更强，而当前 trace distillation target 只监督 pseudo `mu` residual。这会让 dynamic embedding 过度覆盖 static RLAF prior。

在重新运行昂贵的 350/400 之前，更安全的变体应把 SBE polarity 与更强 residual controls 结合：

- 保留 fixed `base_rho_gate_threshold=-0.24`
- 将 `delta_scale` 降到 `0.25` 以下，例如 `0.05` 或 `0.1`
- 使用 clipped target deltas 训练，例如 `target_delta_clip=0.5`
- 先禁用 polarity delta，只把 polarity events 用于 weight/rho guidance；等 weight branch 稳定后再重新启用 polarity

## Conservative SBEPolarity 后续实验

conservative checkpoint 使用：

- config：`configs/config_train_trace_distill_sbe_polarity_conservative.yaml`
- checkpoint：`runs/GNN_Glucose_3SAT_TraceAdapter_SBEPolarityConservative/best.pt`
- `delta_scale=0.05`
- `delta_clip=0.5`
- `base_rho_gate_threshold=-0.24`
- trace target：只使用 conflict/learnt/useful-decision，`target_scale=1.0` 且 `target_delta_clip=0.5`

训练 20 epochs 完成：

```text
epoch=0 loss=0.179718
epoch=19 loss=0.178987
```

下面 3SAT-300 评估后来被确认无效，因为它使用了未优化 solver binary：

| method | size | n | solved | mean time | median time | p75 time | p95 time |
|---|---:|---:|---:|---:|---:|---:|---:|
| one-shot baseline | 300 | 200 | 200 | 7.5060 | 6.3091 | 11.4836 | 22.6719 |
| fixed rho gate | 300 | 200 | 200 | 7.1407 | 5.4279 | 11.0972 | 21.2858 |
| SBE polarity | 300 | 200 | 152 | 29.0690 | 28.7944 | 57.9044 | 60.6532 |
| conservative SBE polarity | 300 | 200 | 152 | 28.9273 | 31.1940 | 59.4339 | 60.6329 |

该结果不能作为 SBEPolarity 灾难性失败的证据。

## Polarity-Gated Fixed-Rho Residual 后续实验

下一版实现把 polarity 从 residual predictor 中移出，只作为 gate 作用在已经稳定的 fixed-rho residual branch 上：

- fusion mode：`polarity_gated_residual`
- residual input：只使用前 20 个 enhanced event-state features
- polarity input：9 个 polarity extension features，只用于 `polarity_gate`
- output mask：只允许 `mu/log weight` 改变；`rho/phase` 和 sigma deltas 强制为 0
- checkpoint initialization：`runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_RhoGateM024/best.pt`
- training mode：`adapter_train_mode=polarity_gate`，冻结导入的 fixed-rho residual branch

第一版 polarity-gated 实现误允许 residual branch 继续训练。在 bad solver binary 下，它看起来复现了 SBE-style failure：

| method | size | n | solved | mean time | median time |
|---|---:|---:|---:|---:|---:|
| polarity-gated rho, retrain residual | 300 | 200 | 152 | 29.0588 | 31.5049 |

冻结 residual branch 后，实现才符合预期设计。在 bad solver binary 下，free sigmoid gate 仍然表现较差：

| method | size | n | solved | mean time | median time |
|---|---:|---:|---:|---:|---:|
| polarity gate only | 300 | 200 | 153 | 28.4985 | 28.5021 |

最终 conservative 版本加入 `polarity_gate_min=0.95`，因此 polarity 最多只能调制 fixed-rho branch 5%。bad-binary 结果如下：

| method | size | n | solved | mean time | median time |
|---|---:|---:|---:|---:|---:|
| one-shot baseline, current solver binary | 300 | 200 | 151 | 28.9624 | 31.6965 |
| fixed rho gate, current solver binary | 300 | 200 | 155 | 28.3860 | 28.4110 |
| polarity gate min 0.95 | 300 | 200 | 154 | 28.3497 | 27.8987 |

这些 bad-binary 结果已经被本节顶部的修正表替代。Polarity-as-gate 仍是安全消融，但除非后续 350/400 运行或更好的 gate target 明确超过 fixed-rho，否则不应提升为主改进。
