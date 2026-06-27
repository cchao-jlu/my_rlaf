# Residual Training Readiness Audit

| check | status | detail |
| --- | --- | --- |
| split_manifest_exists | pass | runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/manifest.csv |
| split_manifest_has_required_columns | pass | missing=[] |
| residual_train_nonempty | pass | count=168 |
| residual_dev_nonempty | pass | count=93 |
| manifest_cnf_paths_exist | pass | missing_files=0 |
| train_glob_nonempty | pass | count=168 pattern=/home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/cnf/residual_train/*/*.cnf |
| train_glob_paths_exist | pass | broken_paths=0 |
| dev_glob_nonempty | pass | count=93 pattern=/home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/cnf/residual_dev/*/*.cnf |
| dev_glob_paths_exist | pass | broken_paths=0 |
| source_checkpoint_exists | pass | runs/GNN_March_3SAT/best.pt |
