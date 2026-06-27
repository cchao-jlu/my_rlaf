# Residual Portfolio Protocol Audit

| check | status | detail |
| --- | --- | --- |
| strong_combined_exists | pass | runs/analysis/benchmark_transition_band_expanded/combined.csv |
| strong_uses_strict_solved_column | pass | combined.csv must contain strict solved |
| strong_reports_late_solves | fail | late solved rows must be reported, not folded into strict solved |
| candidate_manifest_exists | pass | runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/manifest.csv |
| candidate_manifest_has_required_columns | pass | missing=[] |
| candidate_has_train_dev_heldout | pass | splits=['candidate_dev', 'candidate_heldout', 'candidate_train'] |
| candidate_row_ids_unique | pass | duplicates=0 |
| candidate_total_matches_expected | pass | expected=900 observed=900 |
| candidate_cnf_files_exist | pass | missing_files=300 require_files=False |
| candidate_metadata_exists | pass | runs/analysis/benchmark_transition_band_residual_large/candidate_split_seed1729/candidate_split_metadata.json |
| candidate_metadata_kind | pass | kind=full_candidate_split |
| candidate_metadata_manifest_rows_match | pass | metadata=900 manifest=900 |
| candidate_metadata_manifest_hash_match | pass | metadata=c34d3c4821cc1af15970b8de50dcbfc550d2b8b83ae759cd5cc4ce928a9136dc actual=c34d3c4821cc1af15970b8de50dcbfc550d2b8b83ae759cd5cc4ce928a9136dc |
| candidate_metadata_split_counts_match | pass | metadata={'candidate_dev': 225, 'candidate_heldout': 225, 'candidate_train': 450} manifest={'candidate_dev': 225, 'candidate_heldout': 225, 'candidate_train': 450} |
| candidate_generation_seed_matches_expected | pass | expected=2041 metadata=2041 |
| candidate_split_seed_matches_expected | pass | expected=1729 metadata=1729 |
| candidate_metadata_records_missing_files_at_write | pass | metadata_at_write=300 observed_now=300 |
| split_manifest_exists | pass | runs/analysis/tmp_candidate_projected_split_smoke/manifest.csv |
| split_has_train_dev_heldout | pass | splits=['residual_dev', 'residual_heldout', 'residual_train'] |
| splits_are_disjoint | pass | overlap_rows=0 |
| pilot_excluded_from_split | fail | missing exclude csv: None |
| residual_split_projects_candidate_split | pass | bad_rows=0 missing_rows=0 |
| split_metadata_exists | pass | runs/analysis/tmp_candidate_projected_split_smoke/split_metadata.json |
| split_metadata_manifest_rows_match | pass | metadata=49 manifest=49 |
| split_metadata_counts_match | pass | metadata={'residual_dev': 11, 'residual_heldout': 13, 'residual_train': 25} manifest={'residual_dev': 11, 'residual_heldout': 13, 'residual_train': 25} |
| split_metadata_input_hash_match | pass | metadata=7291d6c2a148ddf6965cbebb446bc52bfd3a7473d32ae9375f5a8050ab76b15c actual=7291d6c2a148ddf6965cbebb446bc52bfd3a7473d32ae9375f5a8050ab76b15c |
| split_metadata_candidate_manifest_hash_match | pass | metadata=c34d3c4821cc1af15970b8de50dcbfc550d2b8b83ae759cd5cc4ce928a9136dc actual=c34d3c4821cc1af15970b8de50dcbfc550d2b8b83ae759cd5cc4ce928a9136dc |
| split_metadata_uses_candidate_manifest | pass | split_source=candidate_manifest |
| heldout_audit_not_requested | pass | no held-out summary paths provided |
