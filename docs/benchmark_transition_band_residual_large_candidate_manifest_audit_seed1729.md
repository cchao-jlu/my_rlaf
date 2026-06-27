# Residual Portfolio Protocol Audit

| check | status | detail |
| --- | --- | --- |
| strong_combined_exists | fail | missing: None |
| candidate_manifest_exists | pass | runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/manifest.csv |
| candidate_manifest_has_required_columns | pass | missing=[] |
| candidate_has_train_dev_heldout | pass | splits=['candidate_dev', 'candidate_heldout', 'candidate_train'] |
| candidate_row_ids_unique | pass | duplicates=0 |
| candidate_total_matches_expected | pass | expected=900 observed=900 |
| candidate_cnf_files_exist | pass | missing_files=0 require_files=True |
| candidate_metadata_exists | pass | runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/candidate_split_metadata.json |
| candidate_metadata_kind | pass | kind=full_candidate_split |
| candidate_metadata_manifest_rows_match | pass | metadata=900 manifest=900 |
| candidate_metadata_manifest_hash_match | pass | metadata=c34d3c4821cc1af15970b8de50dcbfc550d2b8b83ae759cd5cc4ce928a9136dc actual=c34d3c4821cc1af15970b8de50dcbfc550d2b8b83ae759cd5cc4ce928a9136dc |
| candidate_metadata_split_counts_match | pass | metadata={'candidate_dev': 225, 'candidate_heldout': 225, 'candidate_train': 450} manifest={'candidate_dev': 225, 'candidate_heldout': 225, 'candidate_train': 450} |
| candidate_generation_seed_matches_expected | pass | expected=2041 metadata=2041 |
| candidate_split_seed_matches_expected | pass | expected=1729 metadata=1729 |
| candidate_metadata_records_missing_files_at_write | pass | metadata_at_write=300 observed_now=0 |
| split_manifest_not_requested | pass | no split manifest path provided |
| heldout_audit_not_requested | pass | no held-out summary paths provided |
