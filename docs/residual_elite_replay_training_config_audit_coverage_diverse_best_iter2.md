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
| manifest_raw_sources_checkpoint_hash_matches_when_recorded | pass | source_checkpoint_sha256 not recorded in raw sources |
| manifest_raw_sources_cover_split_exactly | pass | missing_instances=0 extra_instances=0 |
| manifest_raw_sources_have_complete_sample_grid | pass | issues=[] total_issues=0 |
| manifest_rows_match_solved_raw_samples | pass | missing_raw_samples=0 |
| training_config_exists | pass | /home/sunshixin/chenchao/my_rlaf/runs/GNN_March_3SAT_ResidualEliteReplayCoverageDiverseBestIter2/config.yaml |
| training_config_has_elite_replay | pass | /home/sunshixin/chenchao/my_rlaf/runs/GNN_March_3SAT_ResidualEliteReplayCoverageDiverseBestIter2/config.yaml |
| training_config_checkpoint_hash_matches | pass | observed=c2b1b7d543e311f48bba393d81e9cf41d9615949426552e1ad5fc13b377e9f5f expected=c2b1b7d543e311f48bba393d81e9cf41d9615949426552e1ad5fc13b377e9f5f |
| training_config_train_manifest_exists | pass | /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_coverage_diverse_best_iter2.csv |
| training_config_train_manifest_path_matches | pass | observed=/home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_coverage_diverse_best_iter2.csv expected=/home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_train_elite_replay_manifest_coverage_diverse_best_iter2.csv |
| training_config_train_manifest_hash_matches | pass | expected=4e4831405e78a91773063ee7f53f3b6912c0a8026e15ed743aa63396ffe24b26 |
| training_config_train_elite_rows_match | pass | observed=109 expected=109 |
| training_config_train_positive_instances_match | pass | observed=30 expected=30 |
| training_config_min_train_positive_floor_matches | pass | observed=8 expected=8 |
| training_config_expected_train_split_matches | pass | observed=residual_train expected=residual_train |
| training_config_expected_train_sample_seeds_match | pass | observed=1729 expected=1729 |
| training_config_expected_train_num_samples_match | pass | observed=16 expected=16 |
| training_config_dev_manifest_exists | pass | /home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_replay_manifest_coverage_diverse_best_iter2.csv |
| training_config_dev_manifest_path_matches | pass | observed=/home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_replay_manifest_coverage_diverse_best_iter2.csv expected=/home/sunshixin/chenchao/my_rlaf/runs/analysis/benchmark_transition_band_residual_large/residual_dev_elite_replay_manifest_coverage_diverse_best_iter2.csv |
| training_config_dev_manifest_hash_matches | pass | expected=e618b65936cdc04094e818693f3436f39bd730ea52901493e81be09a4b68b98f |
| training_config_dev_elite_rows_match | pass | observed=17 expected=17 |
| training_config_dev_positive_instances_match | pass | observed=7 expected=7 |
| training_config_min_dev_positive_floor_matches | pass | observed=4 expected=4 |
| training_config_expected_dev_split_matches | pass | observed=residual_dev expected=residual_dev |
| training_config_expected_dev_sample_seeds_match | pass | observed=1729 expected=1729 |
| training_config_expected_dev_num_samples_match | pass | observed=16 expected=16 |
| training_config_disallows_partial_manifest_training | pass | allow_partial_manifest_training=False |
| training_config_uses_full_manifests | pass | limit_train_rows=0 limit_dev_rows=0 |
