# Go and Monte Carlo Tree Search

A Python Go project investigating how board size and Monte Carlo Tree Search
(MCTS) search budgets affect game length and playing strength.

## Start here

- [Read the illustrated project report](Go_MCTS_Analysis_Package/go_mcts_analysis/Go_MCTS_Report.pdf)
- [Read the report as Markdown](Go_MCTS_Analysis_Package/go_mcts_analysis/Go_MCTS_Report.md)
- [View the figures](Go_MCTS_Analysis_Package/go_mcts_analysis/analysis/figures/)
- [View the experiment summary](Go_MCTS_Analysis_Package/go_mcts_analysis/analysis/experiment_summary.csv)
- [Read the detailed analysis and methods notes](Go_MCTS_Analysis_Package/go_mcts_analysis/README.md)

## What is included

- `Go_MCTS_Analysis_Package/go_state.py`: game state, legal moves, captures,
  positional repetition checks, passing and simplified area scoring.
- `Go_MCTS_Analysis_Package/MCTS.py`: UCT-based MCTS with random rollouts.
- `Go_MCTS_Analysis_Package/random_agent.py`: random-move helper used by MCTS.
- `Go_MCTS_Analysis_Package/run_match.py`: a console match between two MCTS agents.
- `Go_MCTS_Analysis_Package/gologic.py`: an earlier procedural game-logic version.
- `Go_MCTS_Analysis_Package/go_mcts_analysis/`: raw records, analysis code,
  summary tables, figures and the written report.

The standalone Pygame interface is not included in this repository snapshot.
The engine, console match and analysis can be used without a graphical display.

## Setup

Use Python 3.10 or newer. Download and extract this repository, or clone it.
Open a terminal in the repository's main folder, then run:

```bash
python -m pip install -r requirements.txt
```

On Windows, `py` can be used instead of `python` if that is how Python is installed.

## Run a console match

From the repository's main folder:

```bash
python Go_MCTS_Analysis_Package/run_match.py
```

The script currently uses a 5 x 5 board, 7.5 komi, 100 MCTS iterations per move
for each player, and a 500-turn limit. It prints moves and the final board and
score. This example is not the original batch logger used for the recorded data.

## Reproduce the analysis

From the repository's main folder:

```bash
python Go_MCTS_Analysis_Package/go_mcts_analysis/analyse_go.py
```

This reads the included JSONL records, replays the games, and regenerates the
CSV summaries, `analysis.json`, and six figures in PNG and PDF formats under
`Go_MCTS_Analysis_Package/go_mcts_analysis/analysis/`.
The report PDF and Markdown are supplied as finished documents; a PDF report
builder is not included.

To keep the supplied outputs unchanged, write the reproduced analysis elsewhere:

```bash
python Go_MCTS_Analysis_Package/go_mcts_analysis/analyse_go.py --output reproduced_analysis
```

## Main findings

The dataset contains 650 unique completed games. The 100-versus-100 baseline
has 100 games at each board size from 5 x 5 through 9 x 9. Average game length
was compatible with approximately `1.325 * n^2` over these sizes.

On 5 x 5, the 1,000-iteration agent won 48 of 50 games against the 100-iteration
agent, with 25 games in each colour assignment. Increasing both agents from
100 to 1,000 iterations per move produced little observed change in mean game
length: 32.14 versus 32.60 turns.

These results describe the tested agents and scoring variant. They do not
establish optimal Go play, a human ranking, or a general law of game length.
The [report](Go_MCTS_Analysis_Package/go_mcts_analysis/Go_MCTS_Report.pdf)
discusses early passes, random rollouts, fixed komi, failed records and other
limitations. Its source-audit caveats refer to the material supplied when the
report was prepared; including source code here does not establish that it
matches every earlier experiment version.

## Authorship and assistance

DeepSeek assisted with preparing the report and README and compiling the data.
The game and MCTS code were written without that assistance.
