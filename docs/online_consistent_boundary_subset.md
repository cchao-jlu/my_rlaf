# Online-Consistent Boundary 子集

该子集从 full400 的真实 online selector feature cache 和当前 pairwise+veto 审计表中构造。
目的不是覆盖全部 200 个实例，而是优先覆盖 recovery、lost、slowdown 和阈值边界样本，
用于生成与线上决策一致的 counterfactual trace。

- 输出 CNF 目录：`data/online_consistent_boundary/3sat/400`
- manifest：`data/online_consistent_boundary/manifest.csv`
- 子集大小：`50`

## 选择标签计数

| selection_tags | count |
| --- | --- |
| near_threshold | 24 |
| selected_slowdown | 24 |
| focus | 8 |
| timeout_boundary | 8 |
| current_recovered | 3 |
| current_lost | 1 |

## 重点样本

| file_key | selection_tags | use_adapter | base_solved | selected_solved | lost_solution_est | recovered_timeout_est | base_time | current_time | risk_prob | recovery_prob | slowdown_prob |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_122.cnf | focus,current_lost,selected_slowdown,near_threshold | 0 | 1 | 0 | 1 | 0 | 60.049018 | 61.091410 | 0.796813 | 0.130861 | 0.287896 |
| 3sat_82.cnf | focus,selected_slowdown,near_threshold | 1 | 1 | 1 | 0 | 0 | 21.471006 | 35.180332 | 0.779136 | 0.624469 | 0.125604 |
| 3sat_88.cnf | focus,selected_slowdown | 1 | 1 | 1 | 0 | 0 | 0.982300 | 1.183464 | 0.593232 | 0.641168 | 0.162272 |
| 3sat_89.cnf | focus,selected_slowdown | 1 | 0 | 0 | 0 | 0 | 60.763306 | 60.985450 | 0.593619 | 0.459462 | 0.086555 |
| 3sat_163.cnf | focus,current_recovered | 1 | 0 | 1 | 0 | 1 | 60.819696 | 30.950278 | 0.699415 | 0.798261 | 0.039995 |
| 3sat_140.cnf | focus | 0 | 1 | 1 | 0 | 0 | 39.781212 | 4.469628 | 0.292693 | 0.263543 | 0.199412 |
| 3sat_46.cnf | focus | 0 | 1 | 1 | 0 | 0 | 30.742547 | 30.631111 | 0.556280 | 0.467229 | 0.282557 |
| 3sat_25.cnf | focus | 0 | 1 | 1 | 0 | 0 | 1.691112 | 1.864128 | 0.525899 | 0.166484 | 0.422137 |

## 全部样本

| file_key | selection_tags | use_adapter | base_solved | selected_solved | lost_solution_est | recovered_timeout_est | base_time | current_time | risk_prob | recovery_prob | slowdown_prob |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3sat_122.cnf | focus,current_lost,selected_slowdown,near_threshold | 0 | 1 | 0 | 1 | 0 | 60.049018 | 61.091410 | 0.796813 | 0.130861 | 0.287896 |
| 3sat_82.cnf | focus,selected_slowdown,near_threshold | 1 | 1 | 1 | 0 | 0 | 21.471006 | 35.180332 | 0.779136 | 0.624469 | 0.125604 |
| 3sat_27.cnf | selected_slowdown,near_threshold | 0 | 1 | 1 | 0 | 0 | 0.941564 | 1.242278 | 0.261708 | 0.389782 | 0.233403 |
| 3sat_126.cnf | near_threshold,timeout_boundary | 0 | 0 | 0 | 0 | 0 | 60.760118 | 61.084707 | 0.773777 | 0.386181 | 0.378142 |
| 3sat_72.cnf | near_threshold,timeout_boundary | 0 | 0 | 0 | 0 | 0 | 60.822690 | 60.979145 | 0.398985 | 0.386865 | 0.342809 |
| 3sat_199.cnf | near_threshold,timeout_boundary | 0 | 0 | 0 | 0 | 0 | 60.763978 | 60.878035 | 0.818595 | 0.669755 | 0.236504 |
| 3sat_160.cnf | near_threshold,timeout_boundary | 1 | 0 | 0 | 0 | 0 | 60.811496 | 61.069528 | 0.732011 | 0.388599 | 0.213813 |
| 3sat_198.cnf | near_threshold,timeout_boundary | 0 | 0 | 0 | 0 | 0 | 60.743178 | 60.882150 | 0.581051 | 0.212985 | 0.228611 |
| 3sat_119.cnf | near_threshold,timeout_boundary | 0 | 0 | 0 | 0 | 0 | 60.763718 | 61.079941 | 0.748684 | 0.391205 | 0.472632 |
| 3sat_60.cnf | near_threshold,timeout_boundary | 0 | 0 | 0 | 0 | 0 | 60.771047 | 60.944690 | 0.788324 | 0.439859 | 0.257373 |
| 3sat_156.cnf | near_threshold,timeout_boundary | 0 | 0 | 0 | 0 | 0 | 60.828696 | 61.106238 | 0.787671 | 0.357503 | 0.454796 |
| 3sat_1.cnf | selected_slowdown,near_threshold | 0 | 1 | 1 | 0 | 0 | 3.223461 | 3.594112 | 0.766840 | 0.371434 | 0.429053 |
| 3sat_88.cnf | focus,selected_slowdown | 1 | 1 | 1 | 0 | 0 | 0.982300 | 1.183464 | 0.593232 | 0.641168 | 0.162272 |
| 3sat_89.cnf | focus,selected_slowdown | 1 | 0 | 0 | 0 | 0 | 60.763306 | 60.985450 | 0.593619 | 0.459462 | 0.086555 |
| 3sat_163.cnf | focus,current_recovered | 1 | 0 | 1 | 0 | 1 | 60.819696 | 30.950278 | 0.699415 | 0.798261 | 0.039995 |
| 3sat_54.cnf | near_threshold | 0 | 1 | 1 | 0 | 0 | 18.035747 | 18.702093 | 0.794743 | 0.393614 | 0.345890 |
| 3sat_86.cnf | near_threshold | 0 | 1 | 1 | 0 | 0 | 3.391166 | 3.556001 | 0.690801 | 0.388708 | 0.526153 |
| 3sat_51.cnf | near_threshold | 0 | 0 | 0 | 0 | 0 | 60.797147 | 60.360421 | 0.786252 | 0.104739 | 0.806366 |
| 3sat_153.cnf | near_threshold | 0 | 0 | 0 | 0 | 0 | 60.836696 | 61.106839 | 0.270267 | 0.374147 | 0.167675 |
| 3sat_28.cnf | near_threshold | 0 | 0 | 0 | 0 | 0 | 60.740906 | 61.065915 | 0.805951 | 0.441107 | 0.199664 |
| 3sat_185.cnf | near_threshold | 1 | 0 | 0 | 0 | 0 | 60.819720 | 60.376033 | 0.783589 | 0.775367 | 0.055742 |
| 3sat_65.cnf | near_threshold | 0 | 1 | 1 | 0 | 0 | 0.854346 | 0.949614 | 0.012507 | 0.000000 | 0.247746 |
| 3sat_141.cnf | near_threshold | 0 | 1 | 1 | 0 | 0 | 3.076242 | 2.845744 | 0.919760 | 0.123163 | 0.247847 |
| 3sat_136.cnf | near_threshold | 1 | 0 | 0 | 0 | 0 | 60.775312 | 60.426175 | 0.595742 | 0.413525 | 0.217175 |
| 3sat_170.cnf | near_threshold | 1 | 0 | 0 | 0 | 0 | 60.801620 | 61.074263 | 0.333672 | 0.400664 | 0.143654 |
| 3sat_8.cnf | near_threshold | 0 | 0 | 0 | 0 | 0 | 60.816890 | 60.966093 | 0.662016 | 0.401008 | 0.630683 |
| 3sat_59.cnf | near_threshold | 0 | 0 | 0 | 0 | 0 | 60.787547 | 60.961845 | 0.778348 | 0.007751 | 0.809803 |
| 3sat_121.cnf | selected_slowdown | 0 | 1 | 1 | 0 | 0 | 1.919488 | 2.258107 | 0.768378 | 0.134049 | 0.470475 |
| 3sat_150.cnf | selected_slowdown | 0 | 1 | 1 | 0 | 0 | 1.095003 | 1.419087 | 0.822424 | 0.129124 | 0.708192 |
| 3sat_176.cnf | selected_slowdown | 0 | 1 | 1 | 0 | 0 | 2.002860 | 2.313457 | 0.825210 | 0.028793 | 0.892195 |
| 3sat_140.cnf | focus | 0 | 1 | 1 | 0 | 0 | 39.781212 | 4.469628 | 0.292693 | 0.263543 | 0.199412 |
| 3sat_167.cnf | selected_slowdown | 0 | 1 | 1 | 0 | 0 | 11.113596 | 11.939513 | 0.832455 | 0.430372 | 0.409595 |
| 3sat_93.cnf | selected_slowdown | 1 | 1 | 1 | 0 | 0 | 18.832906 | 20.869061 | 0.752000 | 0.642634 | 0.179767 |
| 3sat_46.cnf | focus | 0 | 1 | 1 | 0 | 0 | 30.742547 | 30.631111 | 0.556280 | 0.467229 | 0.282557 |
| 3sat_189.cnf | selected_slowdown | 0 | 0 | 0 | 0 | 0 | 60.753178 | 60.890516 | 0.588801 | 0.548521 | 0.292203 |
| 3sat_154.cnf | selected_slowdown | 0 | 1 | 1 | 0 | 0 | 2.007116 | 2.341509 | 0.697116 | 0.310205 | 0.404230 |
| 3sat_147.cnf | selected_slowdown | 0 | 1 | 1 | 0 | 0 | 11.728012 | 12.310626 | 0.881492 | 0.063059 | 0.729399 |
| 3sat_132.cnf | selected_slowdown | 1 | 1 | 1 | 0 | 0 | 0.863559 | 1.161009 | 0.190343 | 0.473276 | 0.021464 |
| 3sat_124.cnf | selected_slowdown | 0 | 1 | 1 | 0 | 0 | 0.797719 | 1.104080 | 0.912855 | 0.000000 | 0.630654 |
| 3sat_130.cnf | selected_slowdown | 0 | 1 | 1 | 0 | 0 | 4.386588 | 4.814119 | 0.915890 | 0.042536 | 0.903893 |
| 3sat_149.cnf | selected_slowdown | 0 | 1 | 1 | 0 | 0 | 3.763332 | 4.217133 | 0.600409 | 0.253181 | 0.592478 |
| 3sat_131.cnf | selected_slowdown | 0 | 1 | 1 | 0 | 0 | 3.378868 | 3.792572 | 0.621691 | 0.007516 | 0.393856 |
| 3sat_97.cnf | current_recovered | 1 | 0 | 1 | 0 | 1 | 60.760506 | 11.735712 | 0.529829 | 0.679921 | 0.071946 |
| 3sat_85.cnf | current_recovered | 1 | 0 | 1 | 0 | 1 | 60.771706 | 1.632257 | 0.405947 | 0.648606 | 0.052731 |
| 3sat_129.cnf | selected_slowdown | 0 | 1 | 1 | 0 | 0 | 1.438345 | 1.768406 | 0.606396 | 0.032586 | 0.797367 |
| 3sat_25.cnf | focus | 0 | 1 | 1 | 0 | 0 | 1.691112 | 1.864128 | 0.525899 | 0.166484 | 0.422137 |
| 3sat_100.cnf | selected_slowdown | 0 | 1 | 1 | 0 | 0 | 0.903403 | 1.195486 | 0.566058 | 0.179751 | 0.558235 |
| 3sat_22.cnf | selected_slowdown | 1 | 1 | 1 | 0 | 0 | 1.792588 | 2.061179 | 0.393290 | 0.628033 | 0.024321 |
| 3sat_165.cnf | selected_slowdown | 0 | 1 | 1 | 0 | 0 | 0.964214 | 1.224281 | 0.533527 | 0.143694 | 0.770303 |
| 3sat_11.cnf | selected_slowdown | 0 | 1 | 1 | 0 | 0 | 1.948571 | 2.241860 | 0.415907 | 0.123729 | 0.629408 |

