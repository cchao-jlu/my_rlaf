# 难度匹配 Selector Split 结果

本文档记录一次干净的 difficulty-matched selector split。不同于直接使用 `data/validation/3sat` 的协议，这个 split 使用 300 和 350 变量公式训练 selector，然后只在同规模、互斥的 held-out formulas 上评估。

## 数据划分

生成命令：

```bash
python create_selector_split.py \
  --source-root data/test/3sat \
  --output-root data/selector_splits/3sat \
  --sizes 300,350 \
  --train-per-size 100 \
  --seed 1729
```

输出：

- `data/selector_splits/3sat/selector_train/300`：100 个公式
- `data/selector_splits/3sat/selector_train/350`：100 个公式
- `data/selector_splits/3sat/heldout_test/300`：100 个公式
- `data/selector_splits/3sat/heldout_test/350`：100 个公式
- manifest：`data/selector_splits/3sat/split_manifest.csv`

这些目录使用 symlink 指向原始公式，manifest 记录精确划分。

## Selector 训练

训练标签只在 `selector_train` 上生成：

```bash
python evaluate_guided_solver.py --config-name config_eval_guided_solver \
  checkpoint=runs/GNN_Glucose_3SAT_V1/best.pt \
  dataset.eval_path='data/selector_splits/3sat/selector_train/*/*.cnf' \
  dataset.lazy=True \
  solver.params.cpu-lim=60 \
  solver.num_workers=8 \
  loader.batch_size=20 \
  save_file=eval_oneshot_selector_train_300350.csv

python evaluate_guided_solver.py --config-name config_eval_guided_solver_event_var \
  checkpoint=runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt \
  dataset.eval_path='data/selector_splits/3sat/selector_train/*/*.cnf' \
  dataset.lazy=True \
  solver.params.cpu-lim=60 \
  solver.num_workers=8 \
  loader.batch_size=20 \
  save_file=eval_trace_adapter_selector_train_300350_round1_conf500.csv
```

训练 selector：

```bash
python train_adapter_selector.py \
  --checkpoint runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt \
  --dataset 'data/selector_splits/3sat/selector_train/*/*.cnf' \
  --base-eval-csv runs/GNN_Glucose_3SAT_V1/eval_oneshot_selector_train_300350.csv \
  --adapter-eval-csv runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/eval_trace_adapter_selector_train_300350_round1_conf500.csv \
  --output-dir runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_LinearSelectorMatchedSplit \
  --features base_rho_mean \
  --epochs 1000 --lr 0.05 --l2 0.001
```

训练集拟合：

- baseline mean time：`21.3267`
- always-adapter mean time：`21.1492`
- selector offline mean time：`20.6127`
- selected fraction：`0.3550`

## Held-Out 测试结果

matched selector 只在 `heldout_test` 上评估：

```bash
python evaluate_guided_solver.py --config-name config_eval_guided_solver_event_var \
  checkpoint=runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_LinearSelectorMatchedSplit/best.pt \
  dataset.eval_path='data/selector_splits/3sat/heldout_test/300/*.cnf' \
  dataset.lazy=True \
  solver.params.cpu-lim=60 \
  solver.num_workers=8 \
  loader.batch_size=20 \
  save_file=eval_trace_adapter_heldout_300_round1_conf500.csv

python evaluate_guided_solver.py --config-name config_eval_guided_solver_event_var \
  checkpoint=runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_LinearSelectorMatchedSplit/best.pt \
  dataset.eval_path='data/selector_splits/3sat/heldout_test/350/*.cnf' \
  dataset.lazy=True \
  solver.params.cpu-lim=60 \
  solver.num_workers=8 \
  loader.batch_size=20 \
  save_file=eval_trace_adapter_heldout_350_round1_conf500.csv
```

baseline、always-adapter 和 fixed-rho-gate 的结果来自已有 full 300/350 CSV，并用 manifest 过滤到相同 held-out formulas。

| method | size | n | solved | mean time | median time | mean conflicts | mean decisions |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 300 | 100 | 100 | 7.7920 | 7.1885 | 268855.43 | 304454.56 |
| always adapter | 300 | 100 | 100 | 7.6602 | 6.7053 | 267579.31 | 302854.53 |
| fixed rho gate | 300 | 100 | 100 | 7.5196 | 6.9401 | 264998.83 | 300020.91 |
| matched selector | 300 | 100 | 100 | 7.6317 | 6.9950 | 264908.66 | 299931.05 |
| baseline | 350 | 100 | 55 | 33.9549 | 38.6621 | 957534.05 | 1085914.71 |
| always adapter | 350 | 100 | 51 | 36.1257 | 54.1005 | 1035938.97 | 1174449.16 |
| fixed rho gate | 350 | 100 | 53 | 34.4119 | 42.4090 | 980762.72 | 1112452.98 |
| matched selector | 350 | 100 | 53 | 34.5569 | 43.5169 | 971729.05 | 1102252.96 |

## 多特征 Selector 检查

为了确认 base-rho selector 的失败是否只是因为特征太少，额外训练了一版包含当前已实现图级特征的 selector：

```bash
python train_adapter_selector.py \
  --checkpoint runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt \
  --dataset 'data/selector_splits/3sat/selector_train/*/*.cnf' \
  --base-eval-csv runs/GNN_Glucose_3SAT_V1/eval_oneshot_selector_train_300350.csv \
  --adapter-eval-csv runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/eval_trace_adapter_selector_train_300350_round1_conf500.csv \
  --output-dir runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_LinearSelectorMatchedSplitMulti \
  --features base_rho_mean,base_mu_abs_mean,base_mu_std,delta_mu_abs_mean,event_gate_mean,event_conf_learnt_log_mean,event_conf_learnt_rate_mean,event_conf_learnt_rank_mean \
  --epochs 1000 --lr 0.05 --l2 0.001
```

训练集拟合：

- selected fraction：`0.2950`
- selector offline mean time：`20.7691`
- base-rho selector offline mean time：`20.6127`

held-out 对比：

| method | size | n | solved | mean time | median time | mean conflicts | mean decisions |
|---|---:|---:|---:|---:|---:|---:|---:|
| baseline | 300 | 100 | 100 | 7.7920 | 7.1885 | 268855.43 | 304454.56 |
| fixed rho gate | 300 | 100 | 100 | 7.5196 | 6.9401 | 264998.83 | 300020.91 |
| matched selector base rho | 300 | 100 | 100 | 7.6317 | 6.9950 | 264908.66 | 299931.05 |
| matched selector multi | 300 | 100 | 100 | 7.8065 | 7.2684 | 268800.02 | 304393.58 |
| baseline | 350 | 100 | 55 | 33.9549 | 38.6621 | 957534.05 | 1085914.71 |
| fixed rho gate | 350 | 100 | 53 | 34.4119 | 42.4090 | 980762.72 | 1112452.98 |
| matched selector base rho | 350 | 100 | 53 | 34.5569 | 43.5169 | 971729.05 | 1102252.96 |
| matched selector multi | 350 | 100 | 52 | 35.1927 | 46.3327 | 999956.30 | 1133932.09 |

## 结论

difficulty-matched selector split 证明 selector 可以拟合训练 split，但还不能在 held-out 300/350 上稳定改善。heldout 300 中，base-rho selector 好于 one-shot 和 always-adapter，但弱于 fixed rho gate。heldout 350 中，它弱于 one-shot baseline，接近 fixed rho gate。加入当前已实现的 event/delta 图级特征反而让 held-out 性能变差，因此问题不只是“已有特征太少”。

这说明早期 full-test-trained selector 结果不能作为论文主结果。当时 fixed rho 是更稳的受控基线，而 learned selector 需要更好的目标设计、更强的 split-level 监督或更多训练数据。后续 counterfactual-label 工作把 ultra-conservative risk selector 推为当前主线 selector 候选，同时 fixed rho 继续保留为受控基线。
