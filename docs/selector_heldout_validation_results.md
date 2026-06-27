# Held-Out Validation Selector 结果

本文档记录一套干净 selector 协议：在 `data/validation/3sat/*/*.cnf` 上训练 graph-level slow-fast selector，只在 held-out 的 `data/test/3sat/300` 和 `data/test/3sat/350` 上评估。

## 协议

validation selector 训练数据：

```bash
python evaluate_guided_solver.py --config-name config_eval_guided_solver \
  checkpoint=runs/GNN_Glucose_3SAT_V1/best.pt \
  dataset.eval_path='data/validation/3sat/*/*.cnf' \
  dataset.lazy=True \
  solver.params.cpu-lim=60 \
  solver.num_workers=8 \
  loader.batch_size=20 \
  save_file=eval_oneshot_validation.csv

python evaluate_guided_solver.py --config-name config_eval_guided_solver_event_var \
  checkpoint=runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt \
  dataset.eval_path='data/validation/3sat/*/*.cnf' \
  dataset.lazy=True \
  solver.params.cpu-lim=60 \
  solver.num_workers=8 \
  loader.batch_size=20 \
  save_file=eval_trace_adapter_validation_round1_conf500.csv

python train_adapter_selector.py \
  --checkpoint runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/best.pt \
  --dataset 'data/validation/3sat/*/*.cnf' \
  --base-eval-csv runs/GNN_Glucose_3SAT_V1/eval_oneshot_validation.csv \
  --adapter-eval-csv runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05/eval_trace_adapter_validation_round1_conf500.csv \
  --output-dir runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_LinearSelectorVal \
  --features base_rho_mean \
  --epochs 1000 --lr 0.05 --l2 0.001
```

held-out test 评估：

```bash
python evaluate_guided_solver.py --config-name config_eval_guided_solver_event_var \
  checkpoint=runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_LinearSelectorVal/best.pt \
  dataset.eval_path='data/test/3sat/300/*.cnf' \
  dataset.lazy=True \
  solver.params.cpu-lim=60 \
  solver.num_workers=8 \
  loader.batch_size=20 \
  save_file=eval_trace_adapter_300_round1_conf500.csv

python evaluate_guided_solver.py --config-name config_eval_guided_solver_event_var \
  checkpoint=runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_LinearSelectorVal/best.pt \
  dataset.eval_path='data/test/3sat/350/*.cnf' \
  dataset.lazy=True \
  solver.params.cpu-lim=60 \
  solver.num_workers=8 \
  loader.batch_size=20 \
  save_file=eval_trace_adapter_350_round1_conf500.csv
```

## Validation Selector 拟合结果

现有 validation set 是 200-variable formulas，而目标 test set 是 300 和 350 variables。validation 上 always-adapter 信号很弱：

- baseline mean time：`0.3887`
- always-adapter mean time：`0.3944`
- selector offline mean time：`0.3880`
- selected fraction：`0.0800`

因此训练出的是非常保守的 selector。

## Held-Out 测试结果

由下面命令生成：

```bash
python summarize_selector_ablation.py \
  --selector-dir runs/GNN_Glucose_3SAT_TraceAdapter_GatedConflict_Scale025Clip05_LinearSelectorVal
```

| method | size | n | solved | mean time | median time | mean conflicts | mean decisions |
|---|---:|---:|---:|---:|---:|---:|---:|
| one-shot baseline | 300 | 200 | 200 | 7.5060 | 6.3091 | 256867.99 | 290940.28 |
| always adapter | 300 | 200 | 200 | 7.3572 | 5.4163 | 254877.58 | 288553.17 |
| fixed rho gate | 300 | 200 | 200 | 7.1407 | 5.4279 | 249771.64 | 282893.78 |
| validation-trained selector | 300 | 200 | 200 | 7.3884 | 6.0623 | 254407.90 | 288164.55 |
| one-shot baseline | 350 | 200 | 108 | 34.5932 | 47.5073 | 977654.07 | 1108964.57 |
| always adapter | 350 | 200 | 103 | 35.5161 | 54.2078 | 1020833.04 | 1157525.74 |
| fixed rho gate | 350 | 200 | 106 | 34.4200 | 46.4910 | 984417.39 | 1116791.11 |
| validation-trained selector | 350 | 200 | 110 | 34.5179 | 47.2808 | 982061.12 | 1113952.98 |

## 结论

这个 validation-trained selector 还不足以替代 fixed rho gate 或更早的 test-trained selector。它相对 one-shot 在 300 上有小幅平均时间改善，但 350 中位时间退回到 one-shot 区间。

主要原因可能是分布不匹配：`data/validation/3sat` 包含 200-variable formulas，没有暴露 300/350 上 selector 最关键的 hard long-tail 行为。更干净的协议应从更难的 training/validation formulas 中构造 selector-validation split，或者把 300/350 test-like pool 划分成 selector-validation 和 final-test partitions，再声明最终论文结果。
