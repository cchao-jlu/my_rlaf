# Residual Portfolio Protocol Audit

| check | status | detail |
| --- | --- | --- |
| strong_combined_exists | fail | missing: None |
| split_manifest_exists | pass | runs/analysis/tmp_split_metadata_smoke/residual_split_seed1729/manifest.csv |
| split_has_train_dev_heldout | pass | splits=['residual_dev', 'residual_heldout', 'residual_train'] |
| splits_are_disjoint | pass | overlap_rows=0 |
| pilot_excluded_from_split | pass | overlap_rows=0 |
| split_metadata_exists | pass | runs/analysis/tmp_split_metadata_smoke/residual_split_seed1729/split_metadata.json |
| split_metadata_manifest_rows_match | pass | metadata=3 manifest=3 |
| split_metadata_counts_match | pass | metadata={'residual_dev': 1, 'residual_heldout': 1, 'residual_train': 1} manifest={'residual_dev': 1, 'residual_heldout': 1, 'residual_train': 1} |
| split_metadata_input_hash_match | pass | metadata=8ba127c079b4c0fa1927fede2c7feb14c7622eab7dc866603b181bcbc63c5bb7 actual=8ba127c079b4c0fa1927fede2c7feb14c7622eab7dc866603b181bcbc63c5bb7 |
| split_metadata_exclude_hash_match | pass | metadata=5782e10973efed712b2bf4360868cabd047929487740c049716645e95d7ce306 actual=5782e10973efed712b2bf4360868cabd047929487740c049716645e95d7ce306 |
| heldout_audit_not_requested | pass | no held-out summary paths provided |
