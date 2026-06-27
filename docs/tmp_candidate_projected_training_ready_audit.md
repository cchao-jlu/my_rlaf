# Residual Training Readiness Audit

| check | status | detail |
| --- | --- | --- |
| split_manifest_exists | pass | runs/analysis/tmp_candidate_projected_split_smoke/manifest.csv |
| split_manifest_has_required_columns | pass | missing=[] |
| residual_train_nonempty | pass | count=25 |
| residual_dev_nonempty | pass | count=11 |
| manifest_cnf_paths_exist | pass | missing_files=0 |
| train_glob_nonempty | fail | count=0 pattern=runs/analysis/tmp_candidate_projected_split_smoke/cnf/residual_train/*/*.cnf |
| train_glob_paths_exist | pass | broken_paths=0 |
| dev_glob_nonempty | fail | count=0 pattern=runs/analysis/tmp_candidate_projected_split_smoke/cnf/residual_dev/*/*.cnf |
| dev_glob_paths_exist | pass | broken_paths=0 |
| source_checkpoint_exists | pass | runs/GNN_March_3SAT/best.pt |
