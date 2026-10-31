# Go / MCTS experiment analysis

This package analyses James Ward-Phillips's 650 unique completed Go games.
It contains the original uploaded game records, a research report, six figures
in PNG and vector PDF formats, summary tables, and reproducible analysis code.
The game engine and Pygame app were not included in the upload and are not
included in this analysis package.

## Start here

- `Go_MCTS_Report.pdf`: illustrated research report for review.
- `Go_MCTS_Report.md`: editable text of the same report.
- `analysis/figures/`: six figures, each in PNG and PDF.
- `analysis/experiment_summary.csv`: results for all eight settings.
- `analysis/games.csv`: one row per unique completed game.
- `analysis/analysis.json`: estimates, intervals, model details and audit results.
- `analysis/source_inventory.csv`: original-file counts and SHA-256 hashes.
- `analysis/duplicate_records.csv`: the two excluded repeat records.
- `analysis/failed_records.csv`: the two search-error records and recovery status.
- `raw/`: all 11 original JSONL files, unchanged.
- `reference/overnight_summary_original.csv`: the earlier, incomplete summary;
  it is retained for reference and is not treated as additional game data.

## Main findings

The 100-versus-100 baseline contains 100 games at each size from 5 x 5 through
9 x 9. Mean lengths are 32.14, 47.36, 64.03, 89.33 and 107.65 turns.
The weighted quadratic fit is approximately E[T] = 1.325 n^2 over these sizes.
This is a finite-range result for these agents and rules, not a universal law.

On 5 x 5, the 1,000-iteration agent won 48 of 50 games against the
100-iteration agent, with 25 games in each colour assignment. At equal
budgets the 100-each and 1,000-each mean lengths were 32.14 and 32.60 turns.
There is no clear mean-length difference at the available precision and
no resolved odd/even effect after an exploratory linear size adjustment.

## Reproduce the analysis

Use Python 3.10 or newer. From this directory:

```bash
python -m pip install -r requirements.txt
python analyse_go.py
python make_report.py
```

To choose different directories:

```bash
python analyse_go.py --input raw --output analysis
python make_report.py --analysis analysis --output Go_MCTS_Report.pdf
```

The report builder uses the DejaVu Sans fonts distributed with Matplotlib.
Exact versions used for this analysis are recorded in `analysis/analysis.json`.
The bootstrap uses 20,000 within-size resamples and seed 20261019. Rebuilding
may change PDF metadata or rendering slightly across software versions, but
the input records and statistical definitions are preserved.

## How to understand the figures

1. **Board size:** the left panel shows average turns and a fitted quadratic;
   the right divides the averages by n^2. Bars describe uncertainty in means.
2. **Distributions:** every game's length is divided by n^2. The histogram
   height is the fraction of games in a common-width bin, not a probability
   density. The last panel shows cumulative fractions.
3. **Strength:** the higher-budget win rate is reported separately by colour,
   with Wilson confidence intervals for 25 games in each condition.
4. **Equal budgets:** raising both agents' budgets is compared with the
   baseline on 5 x 5, with 100 games in each condition.
5. **Parity:** odd and even sizes are highlighted, with a reference of 50%
   for Black. The report also gives a model-dependent size-adjusted estimate.
6. **Turn components:** from an empty board, turns equal stones remaining
   plus stones captured plus passes. Each component is divided by board area.

## Statistical methods

- Mean intervals: Student t intervals using the sample standard error.
- Equal-budget mean difference: independent-batch Welch interval.
- Within-colour win rates: 95% Wilson intervals, including endpoint cases.
- Quadratic fit: weighted least squares through the origin on n^2, with
  inverse estimated variances of the board-size means.
- Power-law fit: weighted regression of log(group mean) on log(n), using
  estimated inverse variances on the log scale. This is not a fit of each
  individual game's logged length.
- Parity fit: mean(T)/n^2 = alpha + beta*(n-7) + gamma*I(even), weighted by
  inverse variances of the normalised group means. This assumes a linear
  residual size trend and has only five board-size levels.
- Model intervals: percentile bootstrap, resampling games within board size
  while keeping original fit weights fixed. They describe sampling uncertainty
  conditional on the models, not model or algorithm uncertainty.

The same 25 seed labels occur in both unequal-budget colour conditions.
They are different settings, not duplicate games. Their pooled 48/50 rate is
descriptive; no independent-binomial pooled interval is reported.

## Data reconciliation and limitations

Original files contain 654 records: 650 unique completed games, two duplicated
finished records and two search errors. A duplicate is identified by board
size, both search budgets, komi and seed; game_id alone is not globally unique.
Matching duplicates must agree on moves, boards, scores and settings. The
later copy is retained; timings and source-local game IDs can differ.

The failed 8 x 8 seed 18061 is recovered in the later batch. The failed
9 x 9 seed 19007 remains unfinished; its later batch instead includes seed
19101. The report discloses this departure from the original seed plan.
Failed games are not counted as wins, draws or short finished games.

All completed games and failed partial logs are independently replayed.
This checks moves, captures, suicide, positional superko, final passes,
recorded board states and final scores. It does not validate the MCTS source.
Very short completed games remain in the analysis; they are legitimate
outputs of the agents and rules and are relevant to their limitations.

Scoring is the project's simplified area-scoring variant: remaining stones
plus exclusively bordered empty regions, with 7.5 added to White. There is
no automatic dead-stone removal or agreement phase. The report should not
be presented as a study of full Chinese tournament rules or optimal Go.

Runtime was not controlled for computer load. Search was budgeted by
iterations per move. The real-game 500-turn cap is recorded in each JSONL
record; the rollout cap and its development change are not encoded there.
Check those details against the original game and MCTS source before
finalising the implementation description.

## Authorship and assistance
Deepseek helped in creating this Report,README and compiling the data but none of the game or MCTS code.
