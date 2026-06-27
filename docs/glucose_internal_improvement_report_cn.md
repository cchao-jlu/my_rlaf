# Glucose 内部提升主线汇报

## 0. 一页式摘要

这条主线研究的是：在 **weighted Glucose** 内部，如何把原始 RLAF 的一次性静态 GNN 引导，升级成带真实 CDCL event feedback 的低频闭环神经引导系统。

最终系统不是简单地“让神经网络更强”，而是形成了三个关键机制：

1. **变量级事件反馈**：从 Glucose 预热搜索中抽取每个变量的决策、传播、冲突、学习子句和活动度信息，让变量获得动态搜索状态。
2. **低频闭环引导**：完整图神经网络只负责初始结构判断，轻量模块根据预热搜索事件做小幅修正，或决定是否启用修正。
3. **带风险控制的神经干预**：用成对对比轨迹训练风险控制器，只在预计收益大于风险的实例上打开修正模块，并用候选保护的局部重开规则修补过保守边界。

在 3SAT-400 full400、60 秒协议下，主结果是：

| 方法 | 解出数量 / 200 | 平均时间 |
| --- | ---: | ---: |
| one-shot RLAF-style guidance | 50 / 200 | 47.7517 秒 |
| online-consistent selector | 56 / 200 | 46.2217 秒 |
| local reopen guarded | 56 / 200 | 45.4976 秒 |

因此，这条 Glucose 主线可以稳健地汇报为：

> 真实 CDCL 事件反馈能够提升神经 SAT 引导的自适应性；风险控制是必要模块；candidate-guarded 局部边界修正可以在不增加 lost risk 的情况下进一步降低平均时间。

但它不应该被包装成“强于所有现代 SAT solver”的最终性能主线。它更适合作为 EchoSAT 的机制验证、系统 ablation 和论文中关于 event feedback / risk control 的核心证据。

## 1. 汇报目的

本文档用于说明项目中早期到中期的 **Glucose 内部提升主线**。

这条主线的核心问题是：

> 在 weighted Glucose 工作流内部，能否把原始 RLAF 的一次性静态 GNN 引导，升级成带 solver event feedback、风险控制和局部边界修正的低频闭环神经引导系统。

这条线与当前更严格的 March/CaDiCaL residual 主线不同。它主要证明：

- 神经网络低频引导 SAT solver 是可行的。
- solver warmup feedback 可以改善静态 guidance。
- 变量级 CDCL event state 比图级 global statistics 更细。
- 神经干预必须有 risk controller，否则容易拖慢或丢失原本能解的实例。
- online-consistent selector 与 candidate-guarded local reopen 可以在 Glucose 工作流内部改善稳定性和平均时间。

## 2. 从 RLAF 到 EchoSAT-Glucose 的总体演化

原始 RLAF、Balanced Improver 和当前 Glucose 旧主线的关系如下：

| 阶段 | 核心输入 | 引导方式 | 求解器反馈 | 风险控制 | 主要结论 |
| --- | --- | --- | --- | --- | --- |
| 原始 RLAF | 静态 CNF 图 | 一次性图神经网络引导 | 主要作为训练奖励 / 代价 | 无显式风险控制 | 证明神经引导可行，但难实例覆盖不足 |
| Balanced Improver | CNF 图 + 图级全局反馈 | 预热搜索后二次精化 | 图级统计 | 无显式风险控制 | 证明求解器反馈有用，但反馈粒度较粗 |
| 变量级事件适配器 | CNF 图 + 变量级事件状态 | 原始图神经网络 + 轻量适配器 | 变量级 CDCL 事件 | 初步门控 / 修正幅度限制 | 动态事件有信息，但直接开适配器风险大 |
| 风险控制器 | 静态特征 + 预热搜索事件特征 | 选择是否启用适配器 | 成对对比轨迹 | 保守风险控制 | 能避免部分丢解 / 变慢，但早期离线选择器不稳 |
| 在线一致选择器 | 真实在线预热搜索轨迹 | 低频事件引导干预 | 与测试一致的预热搜索证据 | 风险 / 恢复 / 变慢三段判断 | full400 从 `50/200` 提升到 `56/200` |
| 局部边界修正 | 候选清单 + 局部轨迹规则 | 只在局部边界重新打开适配器 | 多点预热搜索变化量 | 候选保护 | 解出数不变，但平均时间进一步下降 |

## 3. 原始 RLAF 基线

原始 RLAF 的流程可以概括为：

```text
CNF literal-clause graph
  -> GNN
  -> variable-level guidance
  -> weighted Glucose
  -> solver result / cost
  -> RLAF training signal
```

它的关键特点是低频引导：

- 不在每个 branching decision 调用神经网络。
- 只在求解开始前输出一次变量级 guidance。
- 后续搜索主要交给 weighted Glucose 完成。

这种方式的优点是开销低、结构简单；缺点是 guidance 是静态的，进入搜索树深处后容易过期。

历史 60 秒评估结果：

| 规模 | 方法 | 解出数量 / 200 | 平均时间 |
| --- | --- | ---: | ---: |
| 300 | 原始 RLAF，一次性引导 | 200 / 200 | 7.506 秒 |
| 350 | 原始 RLAF，一次性引导 | 108 / 200 | 34.593 秒 |
| 400 | 原始 RLAF，一次性引导 | 50 / 200 | 47.730 秒 |

可以看到，300 规模上一次性引导已经足够，但 350/400 上覆盖率明显不足。

## 4. Balanced Improver：一次 warmup 后的反馈精化

Balanced Improver 在原始 RLAF 基础上引入 warmup feedback：

```text
CNF graph
  -> GNN 得到初始 guidance
  -> Glucose warmup
  -> 收集 global feedback state
  -> GNN 第二次前向
  -> refined guidance
  -> Glucose final solve
```

它的核心思想是：

> 不只看公式本身，还看 solver 在这个公式上早期搜索时暴露出的状态。

Balanced Improver 主要使用图级全局反馈，例如整体冲突数、决策数、传播数和搜索统计。它证明了 solver feedback 是有价值的，但也暴露出两个问题：

- 图级反馈太粗，无法告诉模型哪些变量或文字真正处在冲突核心。
- 仍然缺少风险控制。反馈 refinement 不是单调收益，有些实例会被拖慢。

历史长跑结果：

| 规模 | 方法 | 解出数量 / 200 | 平均时间 | 最大源记录时间 |
| --- | --- | ---: | ---: | ---: |
| 300 | Balanced Improver | 200 / 200 | 4.835 秒 | 23.569 秒 |
| 350 | Balanced Improver | 200 / 200 | 47.006 秒 | 265.413 秒 |
| 400 | Balanced Improver | 200 / 200 | 763.915 秒 | 5449.880 秒 |

如果只做事后 60 秒截断诊断：

| 规模 | 方法 | 事后 60 秒内解出 | 平均时间 |
| --- | --- | ---: | ---: |
| 300 | Balanced Improver | 200 / 200 | 4.684 秒 |
| 350 | Balanced Improver | 132 / 200 | 30.961 秒 |
| 400 | Balanced Improver | 52 / 200 | 45.975 秒 |

这个阶段说明：feedback refinement 有用，尤其在 350 上明显强于原始一次性引导；但 400 严格 60 秒口径下提升仍然有限。

## 5. 变量级事件反馈：从整图状态到每个变量的搜索状态

这里的“变量级事件反馈”指的是：不再只看整道 SAT 公式的总体统计，而是记录 **每个变量在求解器早期搜索中实际经历了什么**。

原来的 Balanced Improver 使用的是整图反馈。例如求解器跑了一小段之后，告诉模型：

```text
这道公式已经发生了多少次冲突
做了多少次决策
产生了多少次传播
整体搜索是否变慢
```

这种信息能说明“这道题整体难不难”，但不能说明“到底是哪些变量在制造困难”。也就是说，模型只知道求解器撞墙了，却不知道撞在了哪一批变量上。

变量级事件反馈把粒度降到每个变量。例如变量 `x` 在预热搜索阶段中：

- 被主动选中做过几次决策；
- 参与过多少次传播；
- 是否经常出现在冲突分析里；
- 是否经常出现在新学到的子句里；
- 当前在 Glucose 内部的活动度是多少。

这些统计就是变量在真实搜索过程中的“行为记录”。它们不是模型凭公式结构猜出来的，而是 Glucose 真正跑出来的。

加权 Glucose 增加了以下变量级事件统计。字段名保留为代码中的真实名字：

| 字段 | 含义 | 作用 |
| --- | --- | --- |
| `event_var_decisions` | 变量被主动决策的次数 | 反映变量是否频繁被求解器拿来分支 |
| `event_var_propagations` | 变量参与传播的次数 | 反映变量是否频繁影响其他变量取值 |
| `event_var_conflict_lits` | 变量出现在冲突分析中的次数 | 反映变量是否处在冲突核心 |
| `event_var_learnt_lits` | 变量出现在学习子句中的次数 | 反映变量是否参与新学到的约束 |
| `event_var_activity` | Glucose 当前变量活动度 | 对齐 Glucose 内部已有的变量重要性估计 |
| `event_var_low_lbd_learnt_lits` | 变量出现在低 LBD 学习子句中的次数 | 反映高质量学习子句中的关键变量 |
| `event_var_useful_decisions` | 变量决策是否带来有用推进 | 作为训练标签或选择器特征的候选信号 |

变量级事件反馈的使用流程是：

```text
1. 先用原始图神经网络根据公式结构给出一份初始引导。
2. Glucose 按这份引导先跑一小段，例如跑到固定冲突数。
3. 在这段搜索中，Glucose 为每个变量累计事件统计。
4. Python 端把这些事件统计归一化，变成每个变量的动态状态。
5. 再把动态状态接到图神经网络或轻量选择器里。
6. 模型据此判断：是否需要修正原来的变量权重，或者直接保持原引导不变。
```

它的核心价值是：**给变量补上动态搜索身份**。

同一个公式里，很多变量在静态图结构上可能非常相似，甚至在消息传递模型看来几乎不可区分。但求解器真正跑起来之后，这些变量的命运会不同：

- 有的变量频繁导致冲突；
- 有的变量只是被传播带过；
- 有的变量出现在高质量学习子句里；
- 有的变量虽然结构上看起来重要，但实际搜索中几乎没有作用。

变量级事件反馈就是利用这些真实差异，让模型不再只依赖静态图结构，从而有机会区分原本看起来对称或相似的变量。

## 6. 低频闭环引导：让求解器跑一段，再反馈给模型

“低频闭环”可以拆成两个词理解：

- **闭环**：求解器不是被模型一次性指挥到底。求解器先运行，产生搜索状态；模型读取这些状态，再反过来调整给求解器的引导。
- **低频**：模型不是每做一次分支都调用，而是隔一段搜索才调用一次。例如跑完 500 次、1000 次或 2000 次冲突后再看一次状态。

为什么要低频？

如果每次变量分支都调用神经网络，开销会非常大。SAT 求解器每秒可能做大量决策和传播，而神经网络前向推理，尤其是完整图神经网络，远比一次普通分支决策慢。这样做会让神经网络的开销吞掉求解收益。

所以旧主线采用的是：

> 让 Glucose 先自己跑一小段，收集真实搜索事件；模型只在少数几个检查点介入。

具体流程如下：

```text
第 0 步：初始引导
  输入 SAT 公式图
  图神经网络输出初始变量权重

第 1 步：短程搜索
  Glucose 使用初始变量权重先跑一小段
  例如跑到 500 次冲突

第 2 步：事件收集
  统计每个变量的决策次数、传播次数、冲突参与次数、学习子句参与次数和活动度

第 3 步：风险判断
  轻量选择器判断此时是否值得启用神经修正
  如果风险大，就保持原引导
  如果收益可能较大，就允许修正变量权重

第 4 步：继续求解
  Glucose 使用最终引导继续求解
```

如果设置多轮，就会重复这个过程：

```text
模型给初始引导
  -> 求解器跑一段
  -> 收集变量事件
  -> 判断是否修正
  -> 求解器再跑一段
  -> 再收集事件
  -> 再判断是否修正
```

这就是“低频闭环”：模型和求解器不是完全分离的，但也不是每一步都强绑定。模型只在关键检查点介入，求解器的大量细节搜索仍然由 Glucose 自己完成。

这套设计带来三个好处：

1. **保留效率**：避免高频调用神经网络，减少推理开销。
2. **利用真实搜索信息**：模型能看到求解器实际在哪里发生冲突，而不是只看公式静态结构。
3. **便于风险控制**：每次介入前都可以先判断风险，不适合修正的实例就不动。

## 7. 事件适配器：只做受控修正，不重写原始引导

事件适配器的目标是在原始引导上做局部修正：

```text
原始引导 = 图神经网络根据公式结构给出的变量权重
事件修正量 = 轻量模型根据变量事件状态给出的调整
最终引导 = 原始引导 + 被限制幅度后的事件修正量
```

这里不是让轻量模型完全推翻原始图神经网络，而是让它回答一个更小的问题：

> 在求解器已经跑出一段真实搜索事件之后，原来的变量权重是否需要小幅调整？

为了避免事件适配器破坏原始图神经网络的结构先验，旧主线引入了多种控制：

- **只输出修正量**：不重新生成完整引导，只在原引导上加一个小改动。
- **缩小更新幅度**：把修正量乘上较小系数，避免一次改得太多。
- **截断极端修正**：超过范围的修正会被裁掉。
- **门控判断**：只有事件证据较强时才允许修正。
- **动量平滑**：多轮事件状态不会完全被最新一轮覆盖，而是平滑更新。
- **优先调整变量权重**：主要改“哪个变量更值得优先处理”，而不是直接改变量真假取值倾向。

一个重要负结果是：**直接调整变量取真或取假的倾向不稳定**。

原因是变量取真还是取假更像一个方向开关。很小的连续改动一旦越过临界点，就可能把变量相位翻转，导致后续传播链条大幅改变。因此后续更保守的做法是：

- 不让模型直接大幅改变取真或取假的倾向。
- 把正负文字相关事件只作为判断上下文或门控信号。
- 主线仍然放在更稳定的变量权重修正上。

这个负结果很重要。它说明神经 SAT 引导里不是所有输出都适合连续修正；变量权重相对平滑，变量相位更敏感，需要更谨慎处理。

## 8. Trace Distillation 与 Counterfactual Labels

最早 adapter 预训练尝试过伪标签，例如：

- 低 LBD 学习子句参与变量。
- useful decision。
- conflict rank。
- propagation rank。

这些标签可以描述“变量是否看起来重要”，但不能直接回答：

> 打开 adapter 后，真实求解是否变好？

因此后续转向 counterfactual outcome labels：

```text
同一个实例、同一个 warmup/intervention 点：
  A: base / no adapter branch
  B: adapter branch

比较真实 solver outcome：
  B 恢复 timeout 或明显加速 -> positive
  B 导致 lost solution 或明显变慢 -> negative
  差异很小 -> neutral
```

这个改变非常关键。训练目标从“模仿局部搜索统计”转成“预测一次神经干预的真实后果”。

## 9. Risk Controller：什么时候启用神经干预

实验中很快发现，event adapter 不是稳定单调收益：

- hard / timeout 实例可能被 adapter 救回来。
- easy / medium 实例可能被 adapter 拖慢。
- 少数 base-solved 实例可能因为神经干预而丢解。

所以旧主线从“让 adapter 更强”转向“什么时候该启用 adapter”。

risk controller 的优先级是：

```text
1. 避免 lost solution
2. 保留 recovered timeout / hard speedup
3. 再优化 mean time
```

使用过的 selector 特征包括：

- `base_rho_mean`
- `base_rho_std`
- `delta_abs_mean`
- `event_gate_mean`
- `event_entropy_norm`
- `event_top10_mass`
- `rho_event_corr`
- `rho_event_top10_overlap`
- 多点 warmup drift features，例如 `warmup_c2000_minus_warmup_c1000_*`

重要经验：

- 复杂 micro features 不一定更好。
- 早期 5 个 micro trace features 反而让 selector 过保守，压掉 timeout recovery。
- MLP selector 有容量收益，但 held-out 不稳定。
- 关键不只是 selector 容量，而是训练时和测试时的 feature evidence 是否一致。

## 10. Online-Consistent Selector

online-consistent selector 的核心原则是：

> 训练和评估必须使用同一类真实 warmup evidence，不能用旧 checkpoint 或旧 selector 语境下的 offline cache 做最终决策。

最终形式是 two-stage risk controller：

```text
warmup event trace
  -> risk detector
  -> recovery detector
  -> optional slowdown veto
  -> use_adapter decision
```

其目标不是激进打开 adapter，而是在真实 online evidence 下保守地选择少数可受益实例。

当前 60 秒协议下的对齐结果：

| 规模 | 方法 | 解出数量 / 200 | 平均时间 |
| --- | --- | ---: | ---: |
| 300 | 当前一次性引导 | 200 / 200 | 15.311 秒 |
| 300 | 在线一致选择器 | 200 / 200 | 7.272 秒 |
| 350 | 当前一次性引导 | 108 / 200 | 43.741 秒 |
| 350 | 在线一致选择器 | 109 / 200 | 33.815 秒 |
| 400 | 当前一次性引导 | 50 / 200 | 47.752 秒 |
| 400 | 在线一致选择器 | 56 / 200 | 46.222 秒 |

完整 full400 结果：

| 方法 | 实例数 | 解出数量 | 平均时间 | 中位时间 | 总时间 |
| --- | ---: | ---: | ---: | ---: | ---: |
| one-shot | 200 | 50 | 47.7517 | 60.7660 | 9550.3325 |
| old compact | 200 | 56 | 46.3484 | 60.8806 | 9269.6778 |
| online-consistent | 200 | 56 | 46.2217 | 60.8820 | 9244.3337 |
| pairwise veto | 200 | 52 | 46.8755 | 60.9593 | 9375.1046 |

结论：

- online-consistent selector 相比 one-shot 多解 6 个实例。
- 相比旧 compact，解出数相同，平均时间略优。
- pairwise veto 分支没有站住，不能作为主线。

## 11. Local Boundary Correction

online-consistent selector 偏保守。它为了降低翻车风险，会关掉一些本来应该打开 adapter 的边界样本。

local boundary correction 的目标不是做新全局 selector，而是修补这类局部边界错误。

最终规则：

```text
local_reopen_candidate >= 1
warmup_c1000_minus_warmup_c750_decisions >= 294
warmup_c2000_rho_event_corr >= 0.0365
```

其中 `local_reopen_candidate` 是强 guard：

- 只有 `data/new_closed_old_on_boundary/manifest.csv` 里的候选样本允许进入 reopen rule。
- full400 其他样本即使满足数值条件，也不允许被局部规则额外打开。
- 这样避免把局部规则扩散成不受控的全局 threshold。

boundary26 子集真实 wall-clock：

| policy | n | solved | mean_time | total_time | mean_conflicts | mean_decisions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| no_override | 26 | 5 | 53.3406 | 1386.8551 | 1526094.1154 | 1745096.4615 |
| local_reopen | 26 | 5 | 51.6751 | 1343.5539 | 1461661.2308 | 1671571.3462 |

boundary26 上：

- 解出数保持 `5/26`。
- total time 降低 `43.3012s`。
- mean time 降低 `1.6654s`。
- 没有新增 lost solution。

实际打开 4 个样本：

| file_key | counterfactual_class | counterfactual_reason | local_reopen_rule_open | delta_time |
| --- | --- | --- | --- | ---: |
| `3sat_188.cnf` | positive | recovered_timeout | True | +1.0735 |
| `3sat_196.cnf` | positive | hard_speedup | True | -15.3528 |
| `3sat_46.cnf` | positive | hard_speedup | True | -29.2290 |
| `3sat_66.cnf` | neutral | neutral | True | +0.0053 |

negative slowdown 样本 `3sat_82.cnf` 和 `3sat_93.cnf` 保持关闭。

## 12. Guarded Local Reopen Full400 正式评估

full400 上接入 candidate guard 后，结果如下：

| 方法 | n | solved | mean_time | median_time | total_time | mean_cpu_time | mean_gpu_time |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| one-shot | 200 | 50 | 47.7517 | 60.7660 | 9550.3325 | 46.9441 | 0.8076 |
| old compact | 200 | 56 | 46.3484 | 60.8806 | 9269.6778 | 45.4296 | 0.8468 |
| online-consistent | 200 | 56 | 46.2217 | 60.8820 | 9244.3337 | 45.3366 | 0.8126 |
| local reopen guarded | 200 | 56 | 45.4976 | 60.3461 | 9099.5283 | 45.1173 | 0.2899 |
| pairwise veto | 200 | 52 | 46.8755 | 60.9593 | 9375.1046 | 45.9563 | 0.8467 |

关键结论：

- `local reopen guarded` 解出数仍为 `56/200`。
- 相比 online-consistent，平均时间降低 `0.7240s`。
- 相比 old compact，平均时间降低 `0.8507s`。
- 相比 one-shot，多解 6 个实例，平均时间降低 `2.2540s`。

full400 中 local reopen 实际触发集合：

| file_key | online_result | local_result | online_time | local_time | delta_time_vs_online | 结论 |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `3sat_188.cnf` | SATISFIABLE | SATISFIABLE | 25.6299 | 25.7315 | +0.1015 | 轻微变慢 |
| `3sat_196.cnf` | SATISFIABLE | SATISFIABLE | 26.1159 | 9.6220 | -16.4939 | 明显加速 |
| `3sat_46.cnf` | SATISFIABLE | SATISFIABLE | 29.8371 | 0.5256 | -29.3115 | 明显加速 |
| `3sat_66.cnf` | INDETERMINATE | INDETERMINATE | 60.8271 | 60.4345 | -0.3925 | timeout 仍未解，时间略降 |

这说明 candidate guard 生效：full400 中只有 4 个 `new_closed_old_on` 候选触发 local reopen。

## 13. 模型与系统实现要点

Glucose 旧主线对应的关键实现包括：

### 13.1 Solver 事件采集

weighted Glucose 增加变量级事件输出：

- `decision_count`
- `propagation_count`
- `conflict_involvement_count`
- `learnt_clause_involvement_count`
- `activity`
- low-LBD learnt involvement
- useful decision signals

这些事件用于构造 `event_var` 状态，并通过 `attach_var_event_state_batch` 挂到图数据上。

### 13.2 多点 warmup

正式 selector 使用多点 conflict budget，例如：

```text
500 conflicts
750 conflicts
1000 conflicts
2000 conflicts
```

多点特征可以形成 drift：

```text
warmup_c1000_minus_warmup_c750_decisions
warmup_c2000_minus_warmup_c1000_*
```

这些 drift 特征比单点 snapshot 更能描述求解器搜索方向是否变化。

### 13.3 Candidate manifest

full400 local reopen 必须通过：

```yaml
feedback_refinement:
  local_reopen_candidate_manifest: data/new_closed_old_on_boundary/manifest.csv
```

没有 manifest 时，`local_reopen_candidate` 默认为 0，局部 reopen 不应触发。

### 13.4 审计字段

审计脚本中区分：

- `use_adapter`：基础 selector 是否打开 adapter。
- `local_reopen_rule_open`：局部 reopen 规则是否命中。
- `use_adapter_with_local_reopen`：叠加 local reopen 后的最终 adapter 使用情况。

不能把 `use_adapter` 直接当成最终开关。

### 13.5 主要代码入口

| 模块 | 文件 | 作用 |
| --- | --- | --- |
| 变量级 event state | `src/solving/state.py` | 定义 event-var 字段，并通过 `attach_var_event_state_batch` 挂到 batch graph |
| GNN / adapter / selector | `src/model/model.py` | 实现 risk selector、recovery selector、slowdown selector、local reopen override |
| trace distillation | `src/training/trace_distill.py`、`train_trace_distill.py` | 用 solver trace 训练 adapter 的早期预训练入口 |
| counterfactual trace | `generate_counterfactual_outcome_traces.py` | 在同一 warmup/intervention 点生成 base vs adapter 成对结果 |
| selector 训练 | `train_counterfactual_risk_selector.py`、`train_two_stage_risk_controller.py`、`train_adapter_selector.py` | 训练 conservative selector、two-stage risk/recovery selector |
| boundary 子集构造 | `build_online_consistent_boundary_subset.py`、`build_new_closed_old_on_trace_subset.py` | 构造 full400 边界样本和 new-closed-old-on 样本 |
| 决策审计 | `audit_online_consistent_boundary400_decisions.py`、`audit_full400_selector_decisions.py` | 对比 selector 开关、risk/recovery 概率和最终 outcome |
| local reopen 导出 | `export_local_reopen_override_checkpoint.py` | 把局部 reopen 规则写入 checkpoint / 配置 |
| 结果汇总 | `summarize_online_consistent_boundary400_eval.py`、`summarize_local_reopen_guarded_full400_eval.py` | 汇总 full400 结果、open set 和 cactus plot |

### 13.6 关键配置文件

| 配置 | 作用 |
| --- | --- |
| `configs/config_eval_guided_solver_event_var.yaml` | event-var feedback 的基础评估配置 |
| `configs/config_train_trace_distill_gated.yaml` | gated trace adapter 训练配置 |
| `configs/config_generate_counterfactual_outcome_traces.yaml` | 基础 counterfactual outcome trace 生成配置 |
| `configs/config_generate_counterfactual_outcome_traces_risk_focused.yaml` | risk-focused multipoint trace 生成配置 |
| `configs/config_generate_counterfactual_outcome_traces_online_consistent_boundary400.yaml` | full400 boundary 子集的 online-consistent trace 配置 |
| `configs/config_eval_guided_solver_online_consistent_new_closed_old_on_boundary400.yaml` | new-closed-old-on boundary 的 online-consistent 评估 |
| `configs/config_eval_guided_solver_local_reopen_guarded_full400.yaml` | 正式 guarded local reopen full400 评估 |

### 13.7 实验协议

当前 Glucose 主线结果采用统一 60 秒求解时间口径：

- 数据集：`data/test/3sat/{300,350,400}`，每个规模 200 个实例。
- 主要指标：solved count、mean wall-clock time、median time、total time、conflicts、decisions。
- 关键 full400 对比：one-shot、old compact、online-consistent、local reopen guarded、pairwise veto。
- 重要审计：per-instance win/loss、open set、candidate manifest 命中、cactus plot。
- 正式 local reopen 必须带 `local_reopen_candidate_manifest`，否则不能把局部规则应用到全体实例。

## 14. 负结果与经验教训

这条主线中有几个重要负结果：

1. **直接调 polarity 不稳定**

   连续 residual 改动 polarity logit 容易造成相位翻转，破坏 implication graph。polarity 更适合作为 context / gate，而不是直接输出强 residual。

2. **堆 micro selector features 不一定提升**

   `event_entropy_norm`、`event_top05_mass`、`event_top10_mass`、`rho_event_corr`、`rho_event_top10_overlap` 等特征曾被加入 risk controller，但 repeated split 上没有稳定改善，反而可能压掉 recovery。

3. **MLP selector 容量不是瓶颈**

   MLP 在部分 diagnostic 上有效，但 held-out 不稳。更关键的是 online evidence 是否一致，以及 counterfactual label 是否健康。

4. **不能用旧 cache 做最终决策**

   用旧 compact / old checkpoint 的 feature cache 做 threshold sweep 会产生虚高。最终必须用当前 checkpoint 在线提取 warmup trace。

5. **local reopen 不能无 guard 扩散**

   局部规则只适合修补 `new_closed_old_on` 边界样本。没有 candidate manifest 的全局 reopen 风险不可控。

## 15. 旧 Glucose 主线的论文价值

这条线可以支撑以下相对稳健的 claim：

1. **Solver event feedback 有价值**

   真实 CDCL warmup event 提供了静态 CNF 图没有的信息。

2. **变量级动态状态比图级 global feedback 更细**

   event-var state 能标识搜索中实际活跃、冲突、传播和学习的变量。

3. **神经 SAT guidance 必须风险控制**

   不是所有实例都适合打开 adapter。risk controller 是必要模块，而不是附加工程技巧。

4. **Online-consistent trace 是关键**

   训练时和测试时 selector 看到的 evidence 必须一致，否则离线结果容易虚高。

5. **局部边界修正能补过保守 selector**

   candidate-guarded local reopen 可以修补少数 hard-speedup 边界样本，但它应作为 ablation，而不是主模型。

## 16. 当前限制

旧 Glucose 主线也有明显限制：

- 它主要是在 Glucose neural workflow 内部比较。
- 与 March / CaDiCaL 这类强 solver 相比，性能 claim 不够硬。
- local reopen 没有增加 full400 solved count，只降低 mean time。
- 多个复杂分支没有稳定站住，例如 polarity residual、SBE polarity、pairwise veto、MLP selector。
- 主要贡献是稳定性和风险控制，不是大幅性能碾压。

因此，若用于顶会论文，建议不要把它包装为“超越强 SAT solver”的最终性能主线。

更稳妥的表述是：

> We show that low-frequency CDCL event feedback can make neural SAT guidance safer and more adaptive inside a Glucose-based workflow. The main empirical gain comes from online-consistent risk control and guarded local boundary correction.

中文表述：

> 我们证明了真实 CDCL 事件反馈可以让神经 SAT 引导更稳、更可控；主要贡献不是无脑增强模型，而是建立低频反馈、风险选择和局部边界修正机制。

## 17. 汇报结论

Glucose 内部提升主线完成了从 RLAF 到 EchoSAT 的关键系统升级：

```text
静态一次性 GNN guidance
  -> warmup 后图级 feedback refinement
  -> 变量级 solver event state
  -> event adapter 残差修正
  -> counterfactual risk controller
  -> online-consistent selector
  -> candidate-guarded local boundary correction
```

最终 full400 结果从：

```text
one-shot: 50/200, mean 47.7517s
```

提升到：

```text
online-consistent: 56/200, mean 46.2217s
local reopen guarded: 56/200, mean 45.4976s
```

这说明该主线在 Glucose 内部确实形成了有效提升：多解 6 个实例，并通过风险控制和局部修正降低平均时间。

但它的最佳定位是：

> 作为 EchoSAT 的机制验证与系统 ablation，证明 event feedback、risk control 和 guarded intervention 的价值；若冲击顶会强性能 claim，仍应把最终主线放在 March/CaDiCaL residual setting 上。

## 18. 相关输出文件

- `docs/local_reopen_guarded_full400_eval.md`
- `docs/local_boundary_correction_ablation.md`
- `runs/analysis/local_reopen_guarded_full400_summary.csv`
- `runs/analysis/local_reopen_guarded_full400_per_instance.csv`
- `runs/analysis/local_reopen_guarded_full400_open_set.csv`
- `runs/analysis/local_reopen_guarded_full400_guidance_audit.csv`
- `figures/fig_local_reopen_guarded_full400_cactus.pdf`

## 19. 汇报时建议强调和回避

建议强调：

- 从 RLAF 到 EchoSAT-Glucose 的核心变化不是单纯换模型，而是把 solver 的真实搜索事件接入神经 guidance。
- event-var state 的意义是给对称或相似变量赋予不同的动态搜索身份，可以作为 search-induced symmetry breaking 的系统证据。
- counterfactual labels 比低 LBD / useful decision 这类伪标签更贴近最终求解收益。
- risk controller 是必要的，因为神经干预存在 lost / slowdown 风险。
- guarded local reopen 是一个边界修正 ablation，说明过保守 selector 可以被局部修补。

需要回避或谨慎表述：

- 不要说 local reopen 提高了 full400 solved count；它保持 `56/200`，主要降低 mean time。
- 不要把 pairwise veto、MLP selector、direct polarity residual 当成成功主线；这些是负结果或不稳定结果。
- 不要用旧 offline cache 的 threshold sweep 作为最终证据；最终证据应来自 online-consistent trace。
- 不要把这条 Glucose 主线宣称为最终强性能主线；更强的顶会性能叙事应放在 March/CaDiCaL residual setting 上。
