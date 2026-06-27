# Two-Stage Stage-Scope 消融

本轮目标是验证一个更符合 risk-controller 直觉的训练方式：

- `easy-risk gate` 只在 base-solved / easy-medium 样本上学习翻车风险；
- `hard-recovery detector` 只在 medium / hard / timeout 样本上学习恢复能力；
- 最终策略仍是 `use_adapter = recovery_detector && !risk_gate`。

## 实现

`train_two_stage_risk_controller.py` 新增 `--stage-scope`：

- `all`：两个 head 都在全部 eligible 样本上训练；
- `focused`：risk 只看 easy/medium base-solved，recovery 只看 medium/hard/timeout；
- `risk_all_recovery_focused`：risk 全量，recovery focused；
- `risk_focused_recovery_all`：risk focused，recovery 全量。

focused 训练样本计数：

| stage | n | positive | negative |
| --- | ---: | ---: | ---: |
| risk | 122 | 45 | 77 |
| recovery | 92 | 8 | 84 |

## Repeated-Split 结果

| 方法 | selected | delta solved | lost | recovered | delta time |
| --- | ---: | ---: | ---: | ---: | ---: |
| TwoStage all | 0.1013 | +0.44 | 0.12 | 0.56 | -0.0271 |
| TwoStage focused | 0.1038 | +0.22 | 0.16 | 0.38 | +0.1034 |
| risk_all + recovery_focused | 0.1024 | +0.42 | 0.08 | 0.50 | +0.0091 |
| risk_focused + recovery_all | 0.1038 | +0.38 | 0.10 | 0.48 | -0.0193 |
| DriftStats single-stage | 0.1013 | +0.68 | 0.04 | 0.72 | -0.1837 |

## 结论

硬切训练子集没有改善结果：

- `focused` 明显压弱 recovery；
- 两个 hybrid 版本虽然降低了一些 lost，但 recovery 和 solved delta 都低于 `TwoStage all`；
- 所有 two-stage stage-scope 变体都没有超过 `DriftStats single-stage` 的 repeated-split 指标。

因此当前不继续跑这些 stage-scope 变体的 heldout/400。保留结论：

1. two-stage 结构本身可部署，且 heldout 上比普通 multipoint selector 稳；
2. 但简单按 easy/hard 切训练子集会造成样本更少、recovery detector 更弱；
3. 下一步如果继续 two-stage，应改模型容量或目标函数，而不是继续手工切子集。

更合理的下一步是：

- 使用小 MLP selector 替代线性 head；
- 或对 recovery detector 做 pairwise/ranking loss，让它学习“恢复 timeout 的候选排序”，而不是二分类。
