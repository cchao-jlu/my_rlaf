# SAT Symmetry Solver Protocol Preflight

This is a protocol and accounting preflight for event-conditioned SAT symmetry guidance.
It is not a solver speedup claim. The purpose is to verify that the solver-level
pipeline can run while explicitly accounting for warmup rollout, event extraction/attach,
adapter inference, and the final solve.

## Inputs

- checkpoint: `/home/sunshixin/chenchao/my_rlaf/runs/GNN_Glucose_3SAT_SymmetryTraceAdapter_NegGatePermConsVC_W05/best.pt`
- manifest: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/symmetry_runtime_benchmark_v2_manifest_labeled.csv`
- event-role rows: `105` distinct CNFs
- repeats: `3`
- solver seed base: `1`
- warmup seed base: `1`
- final seed base: `1`
- static-only rows included: `False`
- final CPU limit: `5.0` seconds
- warmup CPU limit: `5.0` seconds
- warmup conflict limit: `20`
- trace LBD threshold: `2`
- neutral weighted baseline: phase `1.0`, weight `1.0`
- weighted solver no-pre: `False`
- solver path role: `patched_pretrue_main`

## Method Semantics

- `plain_unguided_glucose`: plain Glucose final solve, no weighted input path and no model inference.
- `neutral_weighted_glucose`: weighted Glucose binary with all variables assigned the same phase/weight.
- `static_weighted_glucose`: W0.5 checkpoint static/base guidance, then weighted Glucose final solve.
- `cached_trace_no_adapter_final`: pays static inference, event-collecting warmup, and event attach; the final solve reuses the static guidance and does not run adapter inference.
- `event_adapter_final`: pays static inference, event-collecting warmup, event attach, adapter inference, and weighted Glucose final solve.

`neutral_weighted_glucose` is not bit-identical to plain Glucose. It isolates the
weighted binary / weighted input parsing path from the learned static and event weights.

`cached_trace_no_adapter_final` is the required ablation for separating event collection cost
from the adapter's effect on final variable weights.

`patched_pretrue_main` is the main patched weighted Glucose path. `weighted_no_pre_diagnostic` is only a diagnostic path for isolating preprocessing effects; do not merge it with the main runtime protocol.

Permutation variants are not treated as independent evidence in the attribution tables;
those summaries are grouped by `base_instance_id`.

## Artifacts

- per-instance CSV: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/symmetry_runtime_benchmark_v2_per_instance.csv`
- phase accounting CSV: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/symmetry_runtime_benchmark_v2_phases.csv`
- family summary CSV: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/symmetry_runtime_benchmark_v2_by_family.csv`
- base-instance paired summary CSV: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/symmetry_runtime_benchmark_v2_by_base_instance.csv`
- attribution CSV: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/symmetry_runtime_benchmark_v2_attribution.csv`
- base-instance attribution CSV: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/symmetry_runtime_benchmark_v2_attribution_by_base.csv`
- guided-loss diagnostics CSV: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/symmetry_runtime_benchmark_v2_guided_loss_diagnostics.csv`
- timeout/correctness CSV: `/home/sunshixin/chenchao/my_rlaf/runs/analysis/symmetry_runtime_benchmark_v2_timeout_correctness.csv`

## Coverage

| family | instances | base_instances | control_types | scales | benchmark_roles | symmetry_strengths |
| --- | --- | --- | --- | --- | --- | --- |
| complete_coloring | 6 | 2 | strong_symmetry | small | main | strong |
| dominating_set_hex | 12 | 4 | weak_symmetry | large,medium,stress | main | weak |
| even_colouring | 9 | 3 | weak_symmetry | large | main | weak |
| php | 6 | 2 | strong_symmetry | small | main | strong |
| php_exit_all | 6 | 2 | weak_symmetry | medium | main | weak |
| php_exit_single | 9 | 3 | weak_symmetry | large,medium | main | weak |
| random_3sat_control | 21 | 7 | non_symmetric_control | large,medium,small | control | none |
| subset_cardinality | 9 | 3 | weak_symmetry | large,medium | main | weak |
| tseitin_complete | 6 | 2 | strong_symmetry | small | main | strong |
| vertex_cover_torus | 21 | 7 | strong_symmetry | large,medium,stress | main | strong |

## Overall Method Accounting

`known_expected_instances` excludes rows whose manifest `expected_result` is `UNKNOWN`;
`known_expected_match_instances` is the correctness count on the remaining SAT/UNSAT-labelled rows.

| method | rows | solved_instances | known_expected_instances | known_expected_match_instances | protocol_supported_instances | events_available_instances | mean_protocol_accounted_time | median_protocol_accounted_time | mean_final_cpu_time | mean_warmup_cpu_time | mean_adapter_inference_wall_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| plain_unguided_glucose | 315 | 315 | 279 | 279 | 315 | 0 | 0.6486 | 0.002295 | 0.6486 | 0 | 0 |
| neutral_weighted_glucose | 315 | 315 | 279 | 279 | 315 | 0 | 0.7775 | 0.003119 | 0.7775 | 0 | 0 |
| static_weighted_glucose | 315 | 315 | 279 | 279 | 315 | 0 | 1.25 | 0.02249 | 0.7787 | 0 | 0 |
| cached_trace_no_adapter_final | 315 | 315 | 279 | 279 | 315 | 315 | 2.028 | 0.02634 | 0.7787 | 0.7775 | 0 |
| event_adapter_final | 315 | 315 | 279 | 279 | 315 | 315 | 2.028 | 0.0275 | 0.7773 | 0.7775 | 0.00129 |

## Event Accounting

| event_method_rows | events_available_rows | protocol_supported_rows | mean_warmup_cpu_time | mean_event_attach_wall_time | mean_adapter_inference_wall_time |
| --- | --- | --- | --- | --- | --- |
| 630 | 630 | 630 | 0.7775 | 0.0007109 | 0.0006451 |

## Attribution Modes

| primary_attribution | rows | base_instances | variants |
| --- | --- | --- | --- |
| event_collection_overhead_only | 315 | 35 | 3 |

## Fixed Attribution Matrix

The runtime v1 deltas are paired within `(repeat_id, base_instance_id, variant, instance_id)`:

- `weighted_binary_input_delta = neutral_weighted_glucose - plain_unguided_glucose`
- `static_weights_delta = static_weighted_glucose - neutral_weighted_glucose`
- `event_collection_overhead_delta = cached_trace_no_adapter_final - static_weighted_glucose`
- `adapter_delta_inference_delta = event_adapter_final - cached_trace_no_adapter_final`

| attribution_delta | mean_delta |
| --- | --- |
| weighted_binary_input_delta_final_cpu | 0.1289 |
| weighted_binary_input_delta_protocol_time | 0.1289 |
| static_weights_delta_final_cpu | 0.001125 |
| static_weights_delta_protocol_time | 0.4724 |
| event_collection_overhead_delta_final_cpu | 0 |
| event_collection_overhead_delta_protocol_time | 0.7782 |
| adapter_delta_inference_delta_final_cpu | -0.001313 |
| adapter_delta_inference_delta_protocol_time | -2.311e-05 |
| adapter_inference_wall_time | 0.00129 |

## Attribution Matrix By Stratum

| control_type | scale | weighted_binary_input_delta_final_cpu | weighted_binary_input_delta_protocol_time | static_weights_delta_final_cpu | static_weights_delta_protocol_time | event_collection_overhead_delta_final_cpu | event_collection_overhead_delta_protocol_time | adapter_delta_inference_delta_final_cpu | adapter_delta_inference_delta_protocol_time | adapter_inference_wall_time |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| non_symmetric_control | large | 0.0005355 | 0.0005355 | -0.00019 | 0.02523 | 0 | 0.005165 | 0.0006174 | 0.001978 | 0.001361 |
| non_symmetric_control | medium | 0.0006795 | 0.0006795 | -0.0003514 | 0.01736 | 0 | 0.002182 | 0.0006309 | 0.001861 | 0.00123 |
| non_symmetric_control | small | 0.0006851 | 0.0006851 | 0.0003226 | 0.01492 | 0 | 0.002035 | -0.0003752 | 0.0008255 | 0.001201 |
| strong_symmetry | large | 0.2663 | 0.2663 | 0.006528 | 0.6464 | 0 | 1.976 | -0.002391 | -0.001199 | 0.001193 |
| strong_symmetry | medium | 0.01407 | 0.01407 | -0.0001076 | 0.02815 | 0 | 0.02084 | -0.0008017 | 0.0003811 | 0.001183 |
| strong_symmetry | small | 0.0002905 | 0.0002905 | 0.0002672 | 0.01467 | 0 | 0.002335 | -0.000583 | 0.000802 | 0.001385 |
| strong_symmetry | stress | 0.006334 | 0.006334 | -0.002909 | 3.138 | 0 | 5.008 | -4.934e-17 | 0.001315 | 0.001315 |
| weak_symmetry | large | 0.4518 | 0.4518 | 0.002815 | 0.1215 | 0 | 0.7686 | -0.002929 | -0.001664 | 0.001264 |
| weak_symmetry | medium | 0.007062 | 0.007062 | -0.000301 | 0.01875 | 0 | 0.01039 | -0.001201 | 5.767e-05 | 0.001259 |
| weak_symmetry | stress | 0.009411 | 0.009411 | 0.004819 | 6.948 | 0 | 5 | -0.006419 | -0.00479 | 0.001629 |

## Base-Instance Attribution

| family | base_instance_id | repeats | variants | plain_solved_rows | neutral_lost_rows | static_lost_rows | adapter_lost_rows | weighted_binary_input_delta_protocol_time_mean | static_weights_delta_protocol_time_mean | event_collection_overhead_delta_protocol_time_mean | adapter_delta_inference_delta_protocol_time_mean | warmup_decisions_mean | warmup_conflicts_mean | graph_gate_open_rows | primary_attribution_modes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| complete_coloring | k4_color3 | 3 | 3 | 9 | 0 | 0 | 0 | 0.001508 | 0.02171 | 0.002561 | 0.002143 | 0 | 0 | 0 | event_collection_overhead_only |
| complete_coloring | k5_color4 | 3 | 3 | 9 | 0 | 0 | 0 | 0.0002891 | 0.01608 | 0.002787 | 0.0005017 | 32.33 | 28.67 | 9 | event_collection_overhead_only |
| dominating_set_hex | dominating_set_hex_3x5_s3 | 3 | 3 | 9 | 0 | 0 | 0 | 0.03725 | 0.03418 | 0.04797 | -0.006209 | 7.667 | 4 | 9 | event_collection_overhead_only |
| dominating_set_hex | dominating_set_hex_3x6_s4 | 3 | 3 | 9 | 0 | 0 | 0 | 0.9891 | 0.1139 | 1.132 | -0.02192 | 12.67 | 7.667 | 9 | event_collection_overhead_only |
| dominating_set_hex | dominating_set_hex_4x5_s5 | 3 | 3 | 9 | 0 | 0 | 0 | 2.619 | 0.7374 | 4.996 | 0.001626 | 28 | 15 | 9 | event_collection_overhead_only |
| dominating_set_hex | dominating_set_hex_4x6_s6 | 3 | 3 | 9 | 0 | 0 | 0 | 0.009411 | 6.948 | 5 | -0.00479 | 32.33 | 16.67 | 9 | event_collection_overhead_only |
| even_colouring | even_colouring_torus_4x5_split | 3 | 3 | 9 | 0 | 0 | 0 | 0.0005964 | 0.02301 | 0.00277 | 0.001744 | 22 | 0 | 9 | event_collection_overhead_only |
| even_colouring | even_colouring_torus_4x6_split | 3 | 3 | 9 | 0 | 0 | 0 | 0.001466 | 0.02077 | 0.003141 | 0.0005155 | 27 | 0 | 9 | event_collection_overhead_only |
| even_colouring | even_colouring_torus_5x5_split | 3 | 3 | 9 | 0 | 0 | 0 | 0.001864 | 0.02077 | 0.003879 | 0.001955 | 28 | 0 | 9 | event_collection_overhead_only |
| php | php_p4_h3 | 3 | 3 | 9 | 0 | 0 | 0 | -0.000204 | 0.01118 | 0.002281 | 0.000904 | 0 | 0 | 0 | event_collection_overhead_only |
| php | php_p5_h4 | 3 | 3 | 9 | 0 | 0 | 0 | 0.0007524 | 0.01456 | 0.001918 | 5.226e-05 | 28.67 | 28 | 9 | event_collection_overhead_only |
| php_exit_all | php_exit_all_p5_h4 | 3 | 3 | 9 | 0 | 0 | 0 | 0.00135 | 0.01449 | 0.002563 | 0.00171 | 13.33 | 0.3333 | 9 | event_collection_overhead_only |
| php_exit_all | php_exit_all_p6_h5 | 3 | 3 | 9 | 0 | 0 | 0 | 0.0006462 | 0.01809 | 0.003113 | 0.00136 | 6 | 0 | 9 | event_collection_overhead_only |
| php_exit_single | php_exit_single_p5_h4 | 3 | 3 | 9 | 0 | 0 | 0 | 0.0008036 | 0.01422 | 0.003003 | 0.001059 | 1 | 0 | 0 | event_collection_overhead_only |
| php_exit_single | php_exit_single_p6_h5 | 3 | 3 | 9 | 0 | 0 | 0 | 0.001694 | 0.01677 | 0.002786 | 0.001042 | 5 | 0 | 9 | event_collection_overhead_only |
| php_exit_single | php_exit_single_p7_h6 | 3 | 3 | 9 | 0 | 0 | 0 | 0.0007023 | 0.02128 | 0.003766 | 0.001905 | 6 | 0 | 9 | event_collection_overhead_only |
| random_3sat_control | random_3sat_control_v100_c600_seed1914 | 3 | 3 | 9 | 0 | 0 | 0 | 0.00125 | 0.02855 | 0.007422 | 0.002427 | 180.3 | 158.3 | 9 | event_collection_overhead_only |
| random_3sat_control | random_3sat_control_v20_c85_seed1901 | 3 | 3 | 9 | 0 | 0 | 0 | 0.0006851 | 0.01492 | 0.002035 | 0.0008255 | 9 | 0 | 9 | event_collection_overhead_only |
| random_3sat_control | random_3sat_control_v30_c128_seed1902 | 3 | 3 | 9 | 0 | 0 | 0 | 0.0002036 | 0.01719 | 0.001936 | 0.001669 | 15.33 | 14.33 | 9 | event_collection_overhead_only |
| random_3sat_control | random_3sat_control_v35_c149_seed1911 | 3 | 3 | 9 | 0 | 0 | 0 | 0.001017 | 0.01725 | 0.001826 | 0.00212 | 14 | 7 | 9 | event_collection_overhead_only |
| random_3sat_control | random_3sat_control_v40_c170_seed1903 | 3 | 3 | 9 | 0 | 0 | 0 | 0.0008179 | 0.01764 | 0.002785 | 0.001793 | 10 | 0 | 9 | event_collection_overhead_only |
| random_3sat_control | random_3sat_control_v60_c180_seed1912 | 3 | 3 | 9 | 0 | 0 | 0 | -0.00019 | 0.02221 | 0.003337 | 0.001366 | 19 | 6 | 9 | event_collection_overhead_only |
| random_3sat_control | random_3sat_control_v80_c340_seed1913 | 3 | 3 | 9 | 0 | 0 | 0 | 0.0005462 | 0.02492 | 0.004736 | 0.002141 | 23 | 2 | 9 | event_collection_overhead_only |
| subset_cardinality | subset_cardinality_bw10 | 3 | 3 | 9 | 0 | 0 | 0 | 0.001145 | 0.01713 | 0.003135 | 0.0002937 | 167.7 | 143 | 9 | event_collection_overhead_only |
| subset_cardinality | subset_cardinality_bw12 | 3 | 3 | 9 | 0 | 0 | 0 | 0.0004823 | 0.01757 | 0.003596 | 0.0005684 | 360.3 | 296.3 | 9 | event_collection_overhead_only |
| subset_cardinality | subset_cardinality_bw8 | 3 | 3 | 9 | 0 | 0 | 0 | 0.0006339 | 0.01473 | 0.002892 | 0.001384 | 90.67 | 72.67 | 9 | event_collection_overhead_only |
| tseitin_complete | tseitin_k5_even | 3 | 3 | 9 | 0 | 0 | 0 | 0.0002316 | 0.01216 | 0.001609 | 0.0004101 | 7 | 0 | 9 | event_collection_overhead_only |
| tseitin_complete | tseitin_k5_odd | 3 | 3 | 9 | 0 | 0 | 0 | -0.0008342 | 0.01232 | 0.002857 | 0.0008012 | 63 | 64 | 9 | event_collection_overhead_only |
| vertex_cover_torus | vertex_cover_torus_3x4_k4_event | 3 | 3 | 9 | 0 | 0 | 0 | 0.01232 | 0.02804 | 0.01871 | -0.002383 | 4 | 5 | 9 | event_collection_overhead_only |
| vertex_cover_torus | vertex_cover_torus_3x4_k5_event | 3 | 3 | 9 | 0 | 0 | 0 | 0.01581 | 0.02826 | 0.02298 | 0.003146 | 6.667 | 7.333 | 9 | event_collection_overhead_only |
| vertex_cover_torus | vertex_cover_torus_3x5_k5_event | 3 | 3 | 9 | 0 | 0 | 0 | 0.272 | 0.07674 | 0.3266 | 0.002506 | 6.333 | 7.333 | 9 | event_collection_overhead_only |
| vertex_cover_torus | vertex_cover_torus_3x5_k6_event | 3 | 3 | 9 | 0 | 0 | 0 | 0.5242 | 0.09721 | 0.6078 | -0.007385 | 12 | 12 | 9 | event_collection_overhead_only |
| vertex_cover_torus | vertex_cover_torus_4x5_k6_event | 3 | 3 | 9 | 0 | 0 | 0 | 0.002659 | 1.765 | 4.994 | 0.001283 | 10 | 11 | 9 | event_collection_overhead_only |
| vertex_cover_torus | vertex_cover_torus_4x5_k8_event | 3 | 3 | 9 | 0 | 0 | 0 | 0.0115 | 3.569 | 5.01 | -0.0003935 | 23.33 | 24 | 9 | event_collection_overhead_only |
| vertex_cover_torus | vertex_cover_torus_4x5_norat | 3 | 3 | 9 | 0 | 0 | 0 | 0.001164 | 2.707 | 5.007 | 0.003024 | 16.33 | 16.33 | 9 | event_collection_overhead_only |

## Guided Loss Diagnostics

_None._

## Family Breakdown

| family | method | rows | solved_instances | mean_protocol_accounted_time | mean_final_cpu_time | mean_warmup_cpu_time | events_available_instances |
| --- | --- | --- | --- | --- | --- | --- | --- |
| complete_coloring | plain_unguided_glucose | 18 | 18 | 0.001248 | 0.001248 | 0 | 0 |
| complete_coloring | neutral_weighted_glucose | 18 | 18 | 0.002147 | 0.002147 | 0 | 0 |
| complete_coloring | static_weighted_glucose | 18 | 18 | 0.02104 | 0.001788 | 0 | 0 |
| complete_coloring | cached_trace_no_adapter_final | 18 | 18 | 0.02371 | 0.001788 | 0.001877 | 18 |
| complete_coloring | event_adapter_final | 18 | 18 | 0.02504 | 0.001313 | 0.001877 | 18 |
| dominating_set_hex | plain_unguided_glucose | 36 | 36 | 1.881 | 1.881 | 0 | 0 |
| dominating_set_hex | neutral_weighted_glucose | 36 | 36 | 2.795 | 2.795 | 0 | 0 |
| dominating_set_hex | static_weighted_glucose | 36 | 36 | 4.753 | 2.802 | 0 | 0 |
| dominating_set_hex | cached_trace_no_adapter_final | 36 | 36 | 7.548 | 2.802 | 2.793 | 36 |
| dominating_set_hex | event_adapter_final | 36 | 36 | 7.54 | 2.792 | 2.793 | 36 |
| even_colouring | plain_unguided_glucose | 27 | 27 | 0.001358 | 0.001358 | 0 | 0 |
| even_colouring | neutral_weighted_glucose | 27 | 27 | 0.002666 | 0.002666 | 0 | 0 |
| even_colouring | static_weighted_glucose | 27 | 27 | 0.02418 | 0.002834 | 0 | 0 |
| even_colouring | cached_trace_no_adapter_final | 27 | 27 | 0.02745 | 0.002834 | 0.002586 | 27 |
| even_colouring | event_adapter_final | 27 | 27 | 0.02885 | 0.002924 | 0.002586 | 27 |
| php | plain_unguided_glucose | 18 | 18 | 0.001388 | 0.001388 | 0 | 0 |
| php | neutral_weighted_glucose | 18 | 18 | 0.001662 | 0.001662 | 0 | 0 |
| php | static_weighted_glucose | 18 | 18 | 0.01453 | 0.002082 | 0 | 0 |
| php | cached_trace_no_adapter_final | 18 | 18 | 0.01663 | 0.002082 | 0.001478 | 18 |
| php | event_adapter_final | 18 | 18 | 0.01711 | 0.001371 | 0.001478 | 18 |
| php_exit_all | plain_unguided_glucose | 18 | 18 | 0.00133 | 0.00133 | 0 | 0 |
| php_exit_all | neutral_weighted_glucose | 18 | 18 | 0.002328 | 0.002328 | 0 | 0 |
| php_exit_all | static_weighted_glucose | 18 | 18 | 0.01862 | 0.002144 | 0 | 0 |
| php_exit_all | cached_trace_no_adapter_final | 18 | 18 | 0.02146 | 0.002144 | 0.002173 | 18 |
| php_exit_all | event_adapter_final | 18 | 18 | 0.02299 | 0.002454 | 0.002173 | 18 |
| php_exit_single | plain_unguided_glucose | 27 | 27 | 0.001379 | 0.001379 | 0 | 0 |
| php_exit_single | neutral_weighted_glucose | 27 | 27 | 0.002445 | 0.002445 | 0 | 0 |
| php_exit_single | static_weighted_glucose | 27 | 27 | 0.01987 | 0.002402 | 0 | 0 |
| php_exit_single | cached_trace_no_adapter_final | 27 | 27 | 0.02305 | 0.002402 | 0.002554 | 27 |
| php_exit_single | event_adapter_final | 27 | 27 | 0.02439 | 0.002427 | 0.002554 | 27 |
| random_3sat_control | plain_unguided_glucose | 63 | 63 | 0.002175 | 0.002175 | 0 | 0 |
| random_3sat_control | neutral_weighted_glucose | 63 | 63 | 0.002794 | 0.002794 | 0 | 0 |
| random_3sat_control | static_weighted_glucose | 63 | 63 | 0.02318 | 0.002608 | 0 | 0 |
| random_3sat_control | cached_trace_no_adapter_final | 63 | 63 | 0.02662 | 0.002608 | 0.002707 | 63 |
| random_3sat_control | event_adapter_final | 63 | 63 | 0.02838 | 0.003089 | 0.002707 | 63 |
| subset_cardinality | plain_unguided_glucose | 27 | 27 | 0.0022 | 0.0022 | 0 | 0 |
| subset_cardinality | neutral_weighted_glucose | 27 | 27 | 0.002954 | 0.002954 | 0 | 0 |
| subset_cardinality | static_weighted_glucose | 27 | 27 | 0.01943 | 0.002867 | 0 | 0 |
| subset_cardinality | cached_trace_no_adapter_final | 27 | 27 | 0.02264 | 0.002867 | 0.002464 | 27 |
| subset_cardinality | event_adapter_final | 27 | 27 | 0.02339 | 0.002365 | 0.002464 | 27 |
| tseitin_complete | plain_unguided_glucose | 18 | 18 | 0.001379 | 0.001379 | 0 | 0 |
| tseitin_complete | neutral_weighted_glucose | 18 | 18 | 0.001078 | 0.001078 | 0 | 0 |
| tseitin_complete | static_weighted_glucose | 18 | 18 | 0.01332 | 0.001818 | 0 | 0 |
| tseitin_complete | cached_trace_no_adapter_final | 18 | 18 | 0.01555 | 0.001818 | 0.001593 | 18 |
| tseitin_complete | event_adapter_final | 18 | 18 | 0.01616 | 0.001255 | 0.001593 | 18 |
| vertex_cover_torus | plain_unguided_glucose | 63 | 63 | 2.162 | 2.162 | 0 | 0 |
| vertex_cover_torus | neutral_weighted_glucose | 63 | 63 | 2.282 | 2.282 | 0 | 0 |
| vertex_cover_torus | static_weighted_glucose | 63 | 63 | 3.464 | 2.284 | 0 | 0 |
| vertex_cover_torus | cached_trace_no_adapter_final | 63 | 63 | 5.748 | 2.284 | 2.283 | 63 |
| vertex_cover_torus | event_adapter_final | 63 | 63 | 5.748 | 2.283 | 2.283 | 63 |

## Interpretation

This run is a repeated paired runtime preflight and attribution ledger, not a
solver speedup claim. If the Glucose seed has no measurable effect on these
instances, interpret repeats as runtime stability rather than seed stability.
Any later runtime comparison should keep the neutral weighted baseline and the
cached-trace no-adapter ablation so the weighted path, static weights, event
collection overhead, and adapter delta remain separable.
