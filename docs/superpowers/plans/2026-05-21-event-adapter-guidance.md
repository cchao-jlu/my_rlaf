# Event Adapter Guidance 实施计划

> **给 agentic worker 的说明：** 实现该计划时应按任务逐步执行。每一步使用 checkbox（`- [ ]`）跟踪状态。

**目标：** 增加第一版可工作的 slow-fast event adapter SAT guidance 路径，并同时修复 refinement time accounting。

**架构：** GNN 仍作为慢结构编码器。第一次 guidance pass 时，评估流程会在每个 graph 上缓存 per-variable GNN embeddings 和 logits。后续 feedback rounds 会附加带 EMA memory 的 solver event state，可选 lightweight adapter 使用 cached embeddings 加 event state/global state 生成 weight 和 polarity logits 的 residual updates，而不重新运行 message passing。

**技术栈：** Python、PyTorch、PyTorch Geometric、Hydra/OmegaConf、已有 Glucose event traces。

---

### Task 1：测试 Enhanced Event State

**文件：**

- 新增：`tests/test_event_state.py`
- 修改：`src/solving/state.py`

- [ ] **Step 1：编写失败测试**

测试 cumulative event state 兼容性、enhanced delta/rate/rank features，以及 attached graph state 上的 EMA memory。

- [ ] **Step 2：实现 state helpers**

新增 `EVENT_VAR_STATE_DIM_ENHANCED`、`event_state_dim()`、enhanced encoder，并把 EMA 存在 `data["var"].event_memory` 下。

### Task 2：测试 Adapter Fast Path

**文件：**

- 新增：`tests/test_event_adapter.py`
- 修改：`src/model/model.py`
- 修改：`src/policy/evaluate.py`

- [ ] **Step 1：编写失败测试**

测试 `event_adapter.enabled=True` 的模型在第一次 pass 缓存 base embeddings，并在第二次 pass 使用 cached embeddings 加 event state。

- [ ] **Step 2：实现 adapter**

在 `GNN` 中新增 zero-initialized residual MLP，`forward` 可选返回 cache，并在 `sample_var_params` 中附加 cache。

### Task 3：测试严格时间统计

**文件：**

- 新增：`tests/test_time_accounting.py`
- 修改：`evaluate_guided_solver.py`

- [ ] **Step 1：编写失败测试**

测试 final time 包含 final solver CPU、final guidance GPU、所有 warmup solver CPU 和所有 refinement guidance GPU。

- [ ] **Step 2：实现 helper**

新增小型纯函数用于按 CNF 累加 guidance time，并在 evaluation 中使用。

### Task 4：新增配置

**文件：**

- 修改：`configs/config_train_rlaf.yaml`
- 修改：`configs/config_eval_guided_solver.yaml`
- 修改：`configs/config_train_rlaf_event_var.yaml`
- 修改：`configs/config_eval_guided_solver_event_var.yaml`

- [ ] **Step 1：新增 adapter 和 enhanced-state switches**

新增 `model.event_adapter.enabled`、`model.event_adapter.hidden_dim`、`feedback_refinement.event_state_features`，以及面向 adapter 的 event-var config 默认值。

### Task 5：验证

**文件：**

- 不改 production files。

- [ ] **Step 1：运行聚焦测试**

运行：

```bash
pytest tests/test_event_state.py tests/test_event_adapter.py tests/test_time_accounting.py -q
```

- [ ] **Step 2：运行 import smoke test**

运行：

```bash
python3 -m py_compile src/solving/state.py src/model/model.py src/policy/evaluate.py evaluate_guided_solver.py train_rlaf.py
```
