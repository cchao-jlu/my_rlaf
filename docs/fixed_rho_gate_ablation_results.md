# Fixed Rho Gate 与 Gated Residual Adapter 消融

本文档记录 EchoSAT slow-fast 受控基线：trace-pretrained gated residual adapter 加 fixed graph-level base-rho gate。

## 配置

运行命令：

```bash
python evaluate_guided_solver.py --config-name config_eval_guided_solver_rho_gate \
  dataset.eval_path='data/test/3sat/300/*.cnf' \
  save_file=eval_trace_adapter_300_round1_conf500.csv

python evaluate_guided_solver.py --config-name config_eval_guided_solver_rho_gate \
  dataset.eval_path='data/test/3sat/350/*.cnf' \
  save_file=eval_trace_adapter_350_round1_conf500.csv

python evaluate_guided_solver.py --config-name config_eval_guided_solver_rho_gate \
  dataset.eval_path='data/test/3sat/400/*.cnf' \
  save_file=eval_trace_adapter_400_round1_conf500.csv
```

checkpoint：

```text
runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_RhoGateM024/best.pt
```

配置要点：

- enhanced variable-level event state
- 一轮 500-conflict rollout
- state momentum：`0.5`
- residual delta clip：`0.5`
- residual delta scale：`0.25`
- per-variable conflict/learnt event gate
- graph-level base-rho gate threshold：`-0.24`

## 系统消融

所有实验都使用每个规模 200 个实例，`cpu-lim=60`、`num_workers=8`、`loader.batch_size=20`。

| method | size | n | solved | mean time | median time | mean CPU | mean GPU | mean conflicts | mean decisions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 300 | 200 | 200 | 7.5060 | 6.3091 | 6.8972 | 0.6088 | 256867.99 | 290940.28 |
| always adapter | 300 | 200 | 200 | 7.3572 | 5.4163 | 6.8172 | 0.5287 | 254877.58 | 288553.17 |
| fixed rho gate | 300 | 200 | 200 | 7.1407 | 5.4279 | 6.6095 | 0.5199 | 249771.64 | 282893.78 |
| baseline | 350 | 200 | 108 | 34.5932 | 47.5073 | 33.9096 | 0.6836 | 977654.07 | 1108964.57 |
| always adapter | 350 | 200 | 103 | 35.5161 | 54.2078 | 34.8027 | 0.7017 | 1020833.04 | 1157525.74 |
| fixed rho gate | 350 | 200 | 106 | 34.4200 | 46.4910 | 33.7749 | 0.6332 | 984417.39 | 1116791.11 |
| baseline | 400 | 200 | 50 | 47.7301 | 60.7777 | 46.9173 | 0.8128 | 1373416.24 | 1568205.28 |
| always adapter | 400 | 200 | 55 | 47.2858 | 60.8537 | 46.3728 | 0.8999 | 1384051.32 | 1579808.94 |
| fixed rho gate | 400 | 200 | 52 | 47.8279 | 60.8435 | 46.9019 | 0.9129 | 1382068.46 | 1577527.77 |

## 解读

fixed rho gate 是 3SAT-300 和 3SAT-350 上较稳的受控变体。它在 300 上相比 one-shot baseline 和 always-adapter 都降低了平均时间、conflicts 和 decisions。在 350 上，它避免了 always-adapter 的明显退化，并相对 one-shot 有轻微平均时间/中位时间改善，但解出数略低于 one-shot。

400 结果并不支持 fixed rho gate 作为长尾难题方案。它在平均时间和中位时间上没有超过 one-shot，只比 one-shot 多解出 2 个实例，而 always-adapter 多解出 5 个。这说明当前 gate 对中等困难区间有效，但不足以解决 400-variable 长尾。

论文中可以把 fixed rho gate 作为保守论证：event-state residual guidance 加 graph-level guard 能稳定 300/350 上的 adapter，并避免 always-adapter 在 350 上的退化。但在没有进一步改进前，不能声称它已经解决 400 长尾问题。

## 下一步方向

下一步应重点面向 400：

- 用 held-out 350/400 split 训练或调优 guard，而不是只依赖 300/350。
- 给 gate 加入 solved-risk objective，因为 400 主要受 timeout 行为支配，而不是小幅平均时间变化。
- 在 400 上评估更长或自适应 rollout budget，因为 500 conflicts 可能太短，难以为很难实例产生可靠 event state。
