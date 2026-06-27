# March Sample-Portfolio Focused Gate

Scope: focused repeat of stochastic guidance samples from the existing
`runs/GNN_March_3SAT/best.pt` checkpoint. This is a model-side diagnostic,
not a trained selector and not a paper-ready method.

Input instances are transition-band cases unsolved by the March/CaDiCaL
strong-solver union. The gate focuses on instances where the earlier 16-sample
run showed nonzero sampled-guidance complementarity.

## Focused Summary

| size | instance | sample seeds | samples/seed | returned solved | strict-60 solved | strict-60 solved seeds | best strict-60 time |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 410 | 3sat_2.cnf | 3 | 16 | 37/48 | 35/48 | 3/3 | 1.329s |
| 440 | 3sat_8.cnf | 3 | 16 | 5/48 | 4/48 | 2/3 | 32.001s |

Negative focused controls at size 410 remain unsolved:

| size | instance | sample seeds | samples/seed | strict-60 solved |
| --- | --- | --- | --- | --- |
| 410 | 3sat_3.cnf | 3 | 16 | 0/48 |
| 410 | 3sat_8.cnf | 3 | 16 | 0/48 |

## Interpretation

- The current March-trained policy has nonzero complementarity against the
  March/CaDiCaL union under stochastic sampling.
- `410/3sat_2.cnf` is a stable high-probability complement point: all three
  sample seeds solve it under strict 60s.
- `440/3sat_8.cnf` is a stable but low-probability complement point: strict-60
  solves appear in two of three sample seeds, and solver-returned solves appear
  in all three sample seeds.
- This supports a neural portfolio / sample-selection research direction.
  It does not yet support a deployable performance claim, because the oracle
  sampling budget is expensive and many sampled runs still timeout.

## Next Model-Side Gate

The next top-conference-relevant step is to turn oracle sampling into a method:

1. Train or derive a cheap sample selector / stopping rule from sampled
   guidances.
2. Evaluate under a fixed wall-clock portfolio budget against March and
   CaDiCaL, not only oracle solved-any.
3. Expand beyond these focused positives only after the selector can recover
   them without spending the full 16-sample budget on every hard instance.

## Artifacts

```text
runs/analysis/benchmark_march_sample_portfolio_multiseed/focused_sample_portfolio_raw.csv
runs/analysis/benchmark_march_sample_portfolio_multiseed/focused_sample_portfolio_summary.csv
runs/analysis/benchmark_march_sample_portfolio_multiseed/raw/seed1729_size410_samples16.csv
runs/analysis/benchmark_march_sample_portfolio_multiseed/raw/seed1730_size410_samples16.csv
runs/analysis/benchmark_march_sample_portfolio_multiseed/raw/seed1731_size410_samples16.csv
runs/analysis/benchmark_march_sample_portfolio_multiseed/raw/seed1730_size440_3sat_8_samples16.csv
runs/analysis/benchmark_march_sample_portfolio_multiseed/raw/seed1731_size440_3sat_8_samples16.csv
```

The earlier broad seed-1729 raw file also contains the 440/3sat_8.cnf seed-1729
samples:

```text
runs/analysis/benchmark_march_sample_portfolio_multiseed/raw/seed1729_samples16.csv
```
