# Counterfactual Label / Rollout Evidence 下一步

disjoint 300/350 结果说明，当前 ultra-conservative selector 的主要问题不是评估规模不够，而是训练 evidence 与 label target 不够能区分“值得冒险”和“容易翻车”的实例。

## 已修改内容

### 1. Risk-focused counterfactual label

`generate_counterfactual_outcome_traces.py` 中的 `CounterfactualLabelSpec` 新增以下字段：

- `recovery_weight`
- `lost_weight`
- `speedup_weight`
- `slowdown_weight`
- `easy_slowdown_weight`
- `positive_min_base_time`
- `positive_min_delta_time`
- `negative_min_delta_time`
- `easy_base_time_cutoff`
- `easy_negative_delta_time`

旧配置不填这些字段时，行为与之前兼容。

新标签逻辑：

- `recovered_timeout`：base timeout、adapter solved，标为 positive。
- `hard_speedup`：base 和 adapter 都 solved，但要求 base 足够难、加速比例足够大、绝对加速时间足够大，才标为 positive。
- `lost_solution`：base solved、adapter timeout，标为 negative，权重最高。
- `easy_slowdown`：base 是 easy solved，但 adapter 明显变慢，标为 negative。
- `slowdown`：一般 slowdown negative。

输出 CSV 新增：

- `counterfactual_reason`
- `base_minus_adapter_time`

### 2. 更强 rollout evidence 配置

新增配置：

```text
configs/config_generate_counterfactual_outcome_traces_risk_focused.yaml
```

该配置使用：

- dataset：`data/selector_splits/3sat/selector_train/*/*.cnf`
- warmup：`1000` conflicts
- warmup cpu limit：`15`
- final cpu limit：`60`
- risk-focused label thresholds

生成命令：

```bash
python3 generate_counterfactual_outcome_traces.py \
  --config-name config_generate_counterfactual_outcome_traces_risk_focused
```

输出：

- `data/counterfactual_trace/risk_focused_selector_train_300350_traces.pt`
- `data/counterfactual_trace/risk_focused_selector_train_300350_outcomes.csv`
- `docs/counterfactual_outcome_trace_risk_focused_selector_train_300350.md`

## 下一轮实验顺序

1. 先用 risk-focused 配置在 selector_train 300/350 上生成 trace。
2. 检查 `counterfactual_reason` 分布，重点看 `recovered_timeout`、`lost_solution`、`hard_speedup`、`easy_slowdown` 是否比旧标签更清晰。
3. 用这批 trace 训练 ultra-conservative selector。
4. 只在 disjoint heldout 300/350 上评估。
5. 只有当 350 至少不低于 one-shot solved count，且 300 不明显劣化时，再考虑 400。

## 已完成结果

正式 trace 已生成，selector 也已训练并在 disjoint 300/350 上评估。结果记录在：

```text
docs/counterfactual_risk_selector_risk_focused_results.md
```

结论：risk-focused labels 改善了标签可解释性，但没有改善最终 selector 泛化。下一步应改 selector feature/模型，而不是继续调阈值或扩大到 400。
