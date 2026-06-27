# Residual Elite Replay Manifest Audit

This audit checks training/dev elite manifest readiness without running solvers.

| check | status | detail |
| --- | --- | --- |
| manifest_exists | pass | /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_coverage_diverse_best_iter2.csv |
| split_csv_exists | pass | /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_split_seed1729/residual_train.csv |
| checkpoint_exists | pass | /home/sunshixin/chenchao/my_rlaf/runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt |
| manifest_has_required_columns | pass | missing=[] |
| split_csv_has_required_columns | pass | missing=[] |
| manifest_positive_instances_meet_floor | pass | positive_instances=30 min=8 |
| manifest_split_matches_expected | pass | observed=['residual_train'] expected=residual_train |
| split_csv_matches_expected_split | pass | observed=['residual_train'] expected=residual_train |
| manifest_instances_subset_of_split | pass | manifest_instances=30 split_instances=168 |
| manifest_row_ids_subset_of_split | pass | manifest_row_ids=30 split_row_ids=168 |
| manifest_cnf_paths_exist | pass | missing_cnf_paths=0 |
| manifest_checkpoint_path_matches | pass | expected=/home/sunshixin/chenchao/my_rlaf/runs/GNN_March_3SAT_ResidualCoverageDiverseBestIter2/best.pt |
| manifest_checkpoint_hash_matches | pass | expected=c2b1b7d543e311f48bba393d81e9cf41d9615949426552e1ad5fc13b377e9f5f |
| manifest_raw_sources_exist | pass | missing=[] |
| manifest_raw_hashes_match | pass | mismatches=[] |
| manifest_respects_max_per_instance | pass | instances_over_limit=0 max_per_instance=4 |
| manifest_sample_ids_in_range | pass | invalid=0 |
| manifest_rows_are_solved | pass | unsolved_rows=0 |
| manifest_raw_sources_load | pass | raw_rows=2688 |
| manifest_raw_sources_have_sampling_columns | pass | missing=[] |
| manifest_raw_sources_sampling_values_numeric | pass | invalid_rows=0 |
| manifest_raw_sources_sample_seeds_match_expected | pass | observed=(1729,) expected=(1729,) |
| manifest_raw_sources_num_samples_match_expected | pass | observed=(16,) expected=16 |
| manifest_raw_sources_checkpoint_hash_matches_when_recorded | pass | source_checkpoint_sha256 not recorded in raw sources |
| manifest_raw_sources_cover_split_exactly | pass | missing_instances=0 extra_instances=0 |
| manifest_raw_sources_have_complete_sample_grid | pass | issues=[] total_issues=0 |
| manifest_rows_match_solved_raw_samples | pass | missing_raw_samples=0 |
