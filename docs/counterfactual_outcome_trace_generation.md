# Counterfactual Outcome Trace 生成

这个模块为 slow-fast SAT guidance pipeline 生成 same-evidence base-vs-adapter outcome labels。

早期 contrastive selector 使用已有 one-shot 和 fixed-rho CSV 文件做拼接分析。这个方式适合快速诊断，但两个分支并不是来自同一个 intervention trace。新的生成器修正了这个协议：

1. 慢 GNN 前向一次，并缓存 `base_embedding` / `base_y`。
2. 使用 base guidance 做短 warmup rollout，同时收集 solver events。
3. 把同一份变量级 event state 附加回缓存图。
4. 基于同一份 warmup evidence 生成两个最终分支 guidance：
   - base branch：复用缓存的 `base_y`
   - adapter branch：在缓存的 `base_embedding`、`base_y` 和 `event_state` 上运行 event adapter
5. 两个分支使用相同 final budget 求解，并写入 paired outcome labels。

重要限制：当前 Glucose wrapper 还不能序列化并恢复内部 CDCL trail、learnt clauses、watches 和 activity heap。因此这些标签是 same-evidence branch counterfactuals，不是 in-process CDCL clone continuations。尽管如此，它仍然比拼接无关 evaluation CSV 更干净，因为两个分支使用的是同一份 warmup event evidence。

## 主要文件

- `generate_counterfactual_outcome_traces.py`
- `configs/config_generate_counterfactual_outcome_traces.yaml`
- `tests/test_counterfactual_outcome_traces.py`

## 默认命令

```bash
python3 generate_counterfactual_outcome_traces.py
```

默认输出：

- `data/counterfactual_trace/counterfactual_outcome_traces.pt`
- `data/counterfactual_trace/counterfactual_outcomes.csv`
- `data/counterfactual_trace/warmup_stats.csv`
- `data/counterfactual_trace/base_branch_stats.csv`
- `data/counterfactual_trace/adapter_branch_stats.csv`
- `docs/counterfactual_outcome_trace_run.md`

## Smoke Test 命令

```bash
python3 generate_counterfactual_outcome_traces.py \
  dataset.path='data/test/3sat/300/*.cnf' \
  loader.batch_size=2 \
  counterfactual.max_num_batches=1 \
  counterfactual.warmup_conflicts=1 \
  counterfactual.warmup_cpu_lim=1 \
  counterfactual.final_cpu_lim=1 \
  counterfactual.use_cuda=False \
  solver.num_workers=2 \
  counterfactual.output_path='data/counterfactual_trace/smoke_counterfactual_outcome_traces.pt' \
  counterfactual.output_csv='data/counterfactual_trace/smoke_counterfactual_outcomes.csv' \
  counterfactual.warmup_stats_csv='data/counterfactual_trace/smoke_warmup_stats.csv' \
  counterfactual.base_stats_csv='data/counterfactual_trace/smoke_base_branch_stats.csv' \
  counterfactual.adapter_stats_csv='data/counterfactual_trace/smoke_adapter_branch_stats.csv' \
  counterfactual.doc_path='docs/counterfactual_outcome_trace_generation_smoke.md'
```

## 标签规则

- `positive`：adapter 解出了 base timeout 实例，或 adapter time 不超过 `0.8 * base_time`。
- `negative`：adapter 丢失 base-solved 实例，或 adapter time 至少为 `1.1 * base_time`。
- `neutral`：既不是 positive，也不是 negative。
- `warmup_solved`：warmup 阶段已经解出实例，因此没有有效 intervention label。

`.pt` payload 会保存带标签的 graphs 和所有分支统计。每个 graph 包含：

- `counterfactual_label`
- `counterfactual_weight`
- `counterfactual_class_code`
- `base_branch_time`
- `adapter_branch_time`
- `adapter_minus_base_time`

这些标签应该替代旧 pseudo-label source，用于下一轮 selector 或 adapter 训练实验。
