"""Reproduce the analysis of James Ward-Phillips's Go experiments.

Run: python analyse_go.py --input raw --output analysis
The script reads the original JSONL files without changing them. It writes
CSV tables, audit information, six figures (PNG and PDF), and analysis.json.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import scipy
from scipy import stats


ANALYSIS_SEED = 20261019
BOOTSTRAP_REPLICATES = 20_000
INK = "#233D4D"
BLUE = "#0072B2"
ORANGE = "#E69F00"
TEAL = "#009E73"
GREY = "#697780"
BOARD_COLOURS = {5: BLUE, 6: TEAL, 7: ORANGE, 8: "#AA69A1", 9: "#D55E00"}
KEY_FIELDS = ("size", "black_iterations", "white_iterations", "komi", "seed")


def game_key(record):
    """A seed is only an identifier within the same experimental settings."""
    return tuple(record[field] for field in KEY_FIELDS)


def experiment_name(key):
    n, black, white, komi = key[:4]
    return f"{n}x{n}_{black}_vs_{white}_komi_{komi:g}"


def write_csv(path, rows):
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def load_records(folder):
    """Deduplicate identical results; reject conflicting results for a key."""
    unique, sources, duplicate_rows, failures, inventory = {}, {}, [], [], []
    for path in sorted(folder.glob("*.jsonl")):
        raw = path.read_bytes()
        records = []
        for number, line in enumerate(raw.decode("utf-8-sig").splitlines(), 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON: {path.name}, line {number}") from error
        counts = Counter(record["status"] for record in records)
        inventory.append({
            "source_file": path.name,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "records": len(records),
            "finished_records": counts["finished"],
            "search_errors": counts["search_error"],
            "turn_limits": counts["turn_limit"],
            "settings": "; ".join(sorted({experiment_name(game_key(r)) for r in records})),
        })
        for record in records:
            key = game_key(record)
            if record["status"] != "finished":
                failures.append({"source_file": path.name, "record": record})
                continue
            if key in unique:
                old = unique[key]
                fields = set(old) | set(record)
                differences = [field for field in fields
                               if field not in {"game_id", "seconds"}
                               and old.get(field) != record.get(field)]
                if differences:
                    raise ValueError(f"Conflicting duplicate {key}: {differences}")
                duplicate_rows.append({
                    "size": key[0], "black_iterations": key[1],
                    "white_iterations": key[2], "komi": key[3], "seed": key[4],
                    "excluded_source": sources[key], "retained_source": path.name,
                    "identical_except_game_id_and_runtime": True,
                })
            # With chronologically named files, retain the later complete batch.
            unique[key], sources[key] = record, path.name
    if not unique:
        raise ValueError(f"No completed games in {folder}")
    return unique, sources, duplicate_rows, failures, inventory


def neighbours(point, size):
    row, col = point
    return [(r, c) for r, c in ((row - 1, col), (row + 1, col),
                               (row, col - 1), (row, col + 1))
            if 0 <= r < size and 0 <= c < size]


def group_and_liberties(board, point, size):
    colour = board[point[0]][point[1]]
    group, todo, liberties = {point}, [point], set()
    while todo:
        for adjacent in neighbours(todo.pop(), size):
            value = board[adjacent[0]][adjacent[1]]
            if value == 0:
                liberties.add(adjacent)
            elif value == colour and adjacent not in group:
                group.add(adjacent)
                todo.append(adjacent)
    return group, liberties


def area_score(board, size, komi):
    """The project's scoring variant: no automatic dead-stone removal."""
    scores = [0, sum(row.count(1) for row in board), sum(row.count(2) for row in board)]
    visited = set()
    for row in range(size):
        for col in range(size):
            point = (row, col)
            if board[row][col] != 0 or point in visited:
                continue
            region, todo, borders = {point}, [point], set()
            visited.add(point)
            while todo:
                for adjacent in neighbours(todo.pop(), size):
                    value = board[adjacent[0]][adjacent[1]]
                    if value:
                        borders.add(value)
                    elif adjacent not in visited:
                        visited.add(adjacent)
                        region.add(adjacent)
                        todo.append(adjacent)
            if len(borders) == 1:
                scores[next(iter(borders))] += len(region)
    return scores[1], scores[2] + komi


def replay_and_measure(record):
    """Independently replay moves and check captures, suicide, superko and score."""
    size = record["size"]
    board = [[0] * size for _ in range(size)]
    history = {tuple([0] * (size * size))}
    consecutive_passes = total_passes = captures = 0
    moves = record["moves"]
    if record["turns"] != len(moves):
        raise ValueError("Move log length differs from recorded turns")
    for number, move_record in enumerate(moves, 1):
        if consecutive_passes == 2:
            raise ValueError("Move after the game ended")
        player = 1 if number % 2 else 2
        if move_record["turn"] != number or move_record["player"] != player:
            raise ValueError("Incorrect turn number or player")
        move = move_record["move"]
        if move is None:
            consecutive_passes += 1
            total_passes += 1
        else:
            row, col = move
            if not (0 <= row < size and 0 <= col < size) or board[row][col] != 0:
                raise ValueError("Out-of-bounds or occupied move")
            board[row][col] = player
            for adjacent in neighbours((row, col), size):
                if board[adjacent[0]][adjacent[1]] == 3 - player:
                    group, liberties = group_and_liberties(board, adjacent, size)
                    if not liberties:
                        captures += len(group)
                        for r, c in group:
                            board[r][c] = 0
            if not group_and_liberties(board, (row, col), size)[1]:
                raise ValueError("Suicide")
            encoded = tuple(stone for board_row in board for stone in board_row)
            if encoded in history:
                raise ValueError("Positional repetition after a placement")
            history.add(encoded)
            consecutive_passes = 0
        if board != move_record["board_after"]:
            raise ValueError("Saved board differs from independently replayed board")
    if board != record["final_board"]:
        raise ValueError("Final board differs from move log")
    if record["status"] == "finished":
        if consecutive_passes != 2:
            raise ValueError("Finished game lacks two consecutive final passes")
        black, white = area_score(board, size, record["komi"])
        if (black, white) != (record["black_score"], record["white_score"]):
            raise ValueError("Recorded score differs from replay scoring")
        winner = "black" if black > white else "white" if white > black else "draw"
        if winner != record["winner"]:
            raise ValueError("Recorded winner differs from scores")
    elif consecutive_passes == 2:
        raise ValueError("Unfinished record already contains an ended game")
    stones = sum(value != 0 for board_row in board for value in board_row)
    if record["turns"] != stones + captures + total_passes:
        raise ValueError("Turns = final stones + captured stones + passes failed")
    return {"passes": total_passes, "captured_stones": captures,
            "final_stones": stones, "placements": len(moves) - total_passes}


def wilson_interval(wins, games):
    z = stats.norm.ppf(0.975)
    proportion = wins / games
    denominator = 1 + z * z / games
    centre = (proportion + z * z / (2 * games)) / denominator
    radius = z * math.sqrt(proportion * (1 - proportion) / games
                          + z * z / (4 * games * games)) / denominator
    # Include the observed endpoint exactly when rounding produces 1 - epsilon.
    return (float(max(0, min(proportion, centre - radius))),
            float(min(1, max(proportion, centre + radius))))


def summarise(key, records, measured):
    turns = np.array([record["turns"] for record in records], dtype=float)
    n_games = len(records)
    mean = float(turns.mean())
    sd = float(turns.std(ddof=1))
    se = sd / math.sqrt(n_games)
    radius = float(stats.t.ppf(0.975, n_games - 1) * se)
    black = sum(record["winner"] == "black" for record in records)
    white = sum(record["winner"] == "white" for record in records)
    black_lo, black_hi = wilson_interval(black, n_games)
    components = [measured[game_key(record)] for record in records]
    area = key[0] ** 2
    return {
        "experiment": experiment_name(key), "size": key[0],
        "black_iterations": key[1], "white_iterations": key[2], "komi": key[3],
        "games": n_games, "mean_turns": mean, "mean_turns_ci_low": mean - radius,
        "mean_turns_ci_high": mean + radius, "standard_deviation": sd,
        "standard_error": se, "median_turns": float(np.median(turns)),
        "q1_turns": float(np.quantile(turns, 0.25)),
        "q3_turns": float(np.quantile(turns, 0.75)),
        "min_turns": int(turns.min()), "max_turns": int(turns.max()),
        "coefficient_of_variation": sd / mean,
        "normalised_mean": mean / area,
        "normalised_mean_ci_low": (mean - radius) / area,
        "normalised_mean_ci_high": (mean + radius) / area,
        "black_wins": black, "white_wins": white, "draws": n_games - black - white,
        "black_win_rate": black / n_games, "black_win_ci_low": black_lo,
        "black_win_ci_high": black_hi,
        "mean_passes": float(np.mean([c["passes"] for c in components])),
        "mean_captured_stones": float(np.mean([c["captured_stones"] for c in components])),
        "mean_final_stones": float(np.mean([c["final_stones"] for c in components])),
        "mean_seconds": float(np.mean([record["seconds"] for record in records])),
    }


def fit_models(groups, summaries):
    sizes = np.arange(5, 10, dtype=float)
    arrays = [np.array([r["turns"] for r in groups[(int(n), 100, 100, 7.5)]],
                       dtype=float) for n in sizes]
    means = np.array([a.mean() for a in arrays])
    errors = np.array([a.std(ddof=1) / math.sqrt(len(a)) for a in arrays])
    rng = np.random.default_rng(ANALYSIS_SEED)
    bootstrap_means = np.column_stack([
        a[rng.integers(len(a), size=(BOOTSTRAP_REPLICATES, len(a)))].mean(axis=1)
        for a in arrays
    ])
    weights = 1 / errors ** 2
    projection = weights * sizes ** 2 / np.sum(weights * sizes ** 4)
    coefficient = float(means @ projection)
    coefficient_ci = np.quantile(bootstrap_means @ projection, [0.025, 0.975])
    lack_of_fit = float(np.sum(((means - coefficient * sizes ** 2) / errors) ** 2))
    # Fit the log of the group mean, not the mean of log individual lengths.
    design = np.column_stack([np.ones(5), np.log(sizes)])
    log_weights = (means / errors) ** 2
    log_projection = np.linalg.solve(design.T @ (log_weights[:, None] * design),
                                     design.T * log_weights)
    power_parameters = log_projection @ np.log(means)
    power_bootstrap = np.log(bootstrap_means) @ log_projection.T
    # Exploratory parity model: E[T]/n^2 = alpha + beta*(n-7) + gamma*I(even).
    parity_design = np.column_stack([np.ones(5), sizes - 7, (sizes % 2 == 0).astype(float)])
    parity_weights = (sizes ** 2 / errors) ** 2
    parity_projection = np.linalg.solve(
        parity_design.T @ (parity_weights[:, None] * parity_design),
        parity_design.T * parity_weights)
    parity_parameters = parity_projection @ (means / sizes ** 2)
    parity_bootstrap = (bootstrap_means / sizes ** 2) @ parity_projection.T
    low = np.array([r["turns"] for r in groups[(5, 100, 100, 7.5)]], dtype=float)
    high = np.array([r["turns"] for r in groups[(5, 1000, 1000, 7.5)]], dtype=float)
    variance_low, variance_high = low.var(ddof=1) / len(low), high.var(ddof=1) / len(high)
    difference_se = math.sqrt(variance_low + variance_high)
    degrees = (variance_low + variance_high) ** 2 / (
        variance_low ** 2 / (len(low) - 1) + variance_high ** 2 / (len(high) - 1))
    difference = float(high.mean() - low.mean())
    difference_ci = difference + stats.t.ppf([0.025, 0.975], degrees) * difference_se
    strength = []
    for black_budget, white_budget, colour in [(1000, 100, "black"), (100, 1000, "white")]:
        records = groups[(5, black_budget, white_budget, 7.5)]
        wins = sum(r["winner"] == colour for r in records)
        lo, hi = wilson_interval(wins, len(records))
        strength.append({"higher_budget_colour": colour, "wins": wins,
                         "games": len(records), "win_rate": wins / len(records),
                         "ci_low": lo, "ci_high": hi,
                         "seeds": sorted(r["seed"] for r in records)})
    return {
        "quadratic": {"formula": "E[T] = c * n^2", "coefficient": coefficient,
                      "ci_95": coefficient_ci.tolist(), "chi_square": lack_of_fit,
                      "degrees_of_freedom": 4,
                      "approximate_lack_of_fit_p": float(stats.chi2.sf(lack_of_fit, 4))},
        "power_law": {"formula": "E[T] = a * n^p", "a": float(np.exp(power_parameters[0])),
                      "exponent": float(power_parameters[1]),
                      "exponent_ci_95": np.quantile(power_bootstrap[:, 1], [0.025, 0.975]).tolist(),
                      "fit_method": "Weighted least squares on log group means; fixed observed inverse variances"},
        "parity": {"formula": "E[T]/n^2 = alpha + beta*(n-7) + gamma*I(even)",
                   "alpha": float(parity_parameters[0]), "size_slope": float(parity_parameters[1]),
                   "even_effect": float(parity_parameters[2]),
                   "even_effect_ci_95": np.quantile(parity_bootstrap[:, 2], [0.025, 0.975]).tolist(),
                   "interpretation": "Exploratory and conditional on a linear size trend, with only five sizes"},
        "equal_budget_difference": {"contrast": "1000-each minus 100-each on 5x5",
                                    "difference_turns": difference,
                                    "ci_95": difference_ci.tolist(),
                                    "method": "Welch t interval for independent batches",
                                    "welch_degrees_of_freedom": float(degrees),
                                    "welch_two_sided_p": float(stats.ttest_ind(high, low, equal_var=False).pvalue)},
        "strength": {"by_colour": strength, "total_wins": sum(s["wins"] for s in strength),
                     "total_games": sum(s["games"] for s in strength),
                     "pooled_interval": None,
                     "note": "The same 25 seed labels occur in both colour conditions. Report within-colour Wilson intervals; the pooled percentage is descriptive."},
        "bootstrap": {"replicates": BOOTSTRAP_REPLICATES, "seed": ANALYSIS_SEED,
                      "method": "Resample 100 games with replacement within each board size; percentile intervals with fixed original fit weights"},
    }


def style_figures():
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9,
        "axes.labelsize": 9, "axes.titlesize": 10, "axes.titleweight": "bold",
        "axes.labelcolor": INK, "text.color": INK, "xtick.color": INK,
        "ytick.color": INK, "axes.edgecolor": "#B7C2C8",
        "axes.spines.top": False, "axes.spines.right": False,
        "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 7.5,
        "figure.facecolor": "white", "axes.facecolor": "white",
        "savefig.facecolor": "white", "pdf.fonttype": 42, "ps.fonttype": 42,
    })


def save_figure(figure, folder, name):
    for extension in ("png", "pdf"):
        figure.savefig(folder / f"{name}.{extension}", dpi=300, bbox_inches="tight")
    plt.close(figure)


def plot_figures(groups, summary_by_key, models, folder):
    style_figures()
    folder.mkdir(parents=True, exist_ok=True)
    sizes = np.arange(5, 10)
    rows = [summary_by_key[(int(n), 100, 100, 7.5)] for n in sizes]
    means = np.array([s["mean_turns"] for s in rows])
    radii = np.array([s["mean_turns_ci_high"] - s["mean_turns"] for s in rows])
    area = sizes ** 2
    coefficient = models["quadratic"]["coefficient"]
    fig, axes = plt.subplots(1, 2, figsize=(7, 3.1), layout="constrained")
    dense = np.linspace(4.8, 9.2, 200)
    axes[0].plot(dense, coefficient * dense ** 2, color=TEAL,
                 label=f"Quadratic fit: {coefficient:.3f} n²")
    axes[0].errorbar(sizes, means, yerr=radii, fmt="o", color=INK, capsize=3,
                     label="Mean, 95% confidence interval")
    axes[0].set(xlabel="Board side length, n", ylabel="Mean turns", title="A. Average game length", xticks=sizes)
    axes[0].legend(loc="upper left", frameon=False, fontsize=7)
    axes[1].axhline(coefficient, color=TEAL, linewidth=1.3, label="Fitted constant ratio")
    axes[1].errorbar(sizes, means / area, yerr=radii / area, fmt="o", color=INK, capsize=3)
    axes[1].set(xlabel="Board side length, n", ylabel="Mean turns / n²", title="B. Normalised game length",
                xticks=sizes, ylim=(1.15, 1.52))
    axes[1].legend(loc="upper left", frameon=False, fontsize=7)
    for axis in axes:
        axis.grid(axis="y", color="#E7ECEF", zorder=0)
        axis.set_axisbelow(True)
    save_figure(fig, folder, "01_board_size_scaling")

    fig, axes = plt.subplots(3, 2, figsize=(7, 5.5), layout="constrained")
    bins = np.arange(0, 2.8001, 0.2)
    for size, axis in zip(sizes, axes.flat):
        values = np.array([r["turns"] / size ** 2 for r in groups[(int(size), 100, 100, 7.5)]])
        axis.hist(values, bins=bins, weights=np.ones(len(values)) / len(values),
                  color=BOARD_COLOURS[int(size)], alpha=0.82, edgecolor="white", linewidth=0.5)
        axis.axvline(values.mean(), color=INK, linestyle="--", linewidth=1)
        axis.set(title=f"{size} × {size}: mean {values.mean():.3f}", xlim=(0, 2.8), ylim=(0, 0.4),
                 xticks=[0, 0.8, 1.6, 2.4], xlabel="Turns / n²", ylabel="Share of games")
        axis.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        axis.set_yticks([0, 0.2, 0.4])
    axis = axes[2, 1]
    for size in sizes:
        values = np.sort([r["turns"] / size ** 2 for r in groups[(int(size), 100, 100, 7.5)]])
        axis.step(np.r_[0, values], np.r_[0, np.arange(1, len(values) + 1) / len(values)],
                  where="post", label=f"{size} × {size}", color=BOARD_COLOURS[int(size)], linewidth=1.3)
    axis.set(title="Cumulative distributions", xlim=(0, 2.8), ylim=(0, 1.02),
             xlabel="Turns / n²", ylabel="Share at or below x", xticks=[0, 0.8, 1.6, 2.4])
    axis.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    axis.legend(loc="lower right", frameon=False, fontsize=6.8)
    save_figure(fig, folder, "02_normalised_distributions")

    fig, axis = plt.subplots(figsize=(7, 2.55), layout="constrained")
    for item, y, colour in zip(models["strength"]["by_colour"], [1, 0], [BLUE, TEAL]):
        point = item["win_rate"]
        axis.errorbar(point, y, xerr=[[point - item["ci_low"]], [item["ci_high"] - point]],
                       fmt="o", color=colour, capsize=4, markersize=7, linewidth=1.6)
        axis.text(point, y + 0.2, f"{item['wins']}/{item['games']} ({point:.0%})", ha="right", fontsize=9)
    axis.axvline(0.5, color=GREY, linestyle="--", linewidth=1)
    axis.set(xlim=(0.3, 1.04), ylim=(-0.5, 1.55), yticks=[1, 0],
             yticklabels=["Higher budget as Black", "Higher budget as White"],
             xlabel="Win rate of the 1,000-iteration agent", title="1,000 versus 100 iterations per move")
    axis.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    axis.grid(axis="x", color="#E7ECEF")
    axis.set_axisbelow(True)
    save_figure(fig, folder, "03_search_budget_strength")

    fig, axes = plt.subplots(1, 2, figsize=(7, 3.0), layout="constrained", gridspec_kw={"width_ratios": [1, 1.45]})
    low, high = summary_by_key[(5, 100, 100, 7.5)], summary_by_key[(5, 1000, 1000, 7.5)]
    for x, row, colour in [(0, low, BLUE), (1, high, TEAL)]:
        axes[0].errorbar(x, row["mean_turns"], yerr=row["mean_turns_ci_high"] - row["mean_turns"],
                         fmt="o", capsize=4, color=colour, markersize=6)
        axes[0].text(x, row["mean_turns"] + 3, f"{row['mean_turns']:.2f}", ha="center", fontsize=8)
    axes[0].set(xticks=[0, 1], xticklabels=["100 each", "1,000 each"], xlim=(-0.6, 1.6),
                ylim=(0, 45), ylabel="Mean turns", title="A. Mean length, 95% intervals")
    for budget, colour in [(100, BLUE), (1000, TEAL)]:
        values = [r["turns"] for r in groups[(5, budget, budget, 7.5)]]
        axes[1].hist(values, bins=np.arange(0, 64.1, 4), weights=np.ones(len(values)) / len(values),
                     histtype="step", linewidth=1.6, color=colour, label=f"{budget:,} each")
    axes[1].set(xlabel="Turns", ylabel="Share of games", title="B. Game-length distributions", xlim=(0, 64))
    axes[1].yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    axes[1].legend(frameon=False)
    save_figure(fig, folder, "04_equal_budget_lengths")

    fig, axes = plt.subplots(1, 2, figsize=(7, 3.0), layout="constrained")
    for parity, label, colour, marker in [(1, "Odd sizes", BLUE, "o"), (0, "Even sizes", ORANGE, "s")]:
        selected = [row for row in rows if row["size"] % 2 == parity]
        n = np.array([row["size"] for row in selected])
        rates = np.array([row["black_win_rate"] for row in selected])
        lo = np.array([row["black_win_ci_low"] for row in selected])
        hi = np.array([row["black_win_ci_high"] for row in selected])
        axes[0].errorbar(n, rates, yerr=[rates - lo, hi - rates], fmt=marker,
                         capsize=3, color=colour, label=label)
        ratios = np.array([row["normalised_mean"] for row in selected])
        radius = np.array([row["normalised_mean_ci_high"] - row["normalised_mean"] for row in selected])
        axes[1].errorbar(n, ratios, yerr=radius, fmt=marker, capsize=3, color=colour)
    axes[0].axhline(0.5, color=GREY, linestyle="--", linewidth=1)
    axes[0].set(xlabel="Board side length, n", ylabel="Black win rate", title="A. Colour balance", xticks=sizes,
                xlim=(4.6, 9.4), ylim=(0.3, 0.7))
    axes[0].yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
    axes[0].legend(frameon=False, loc="upper right", fontsize=7)
    axes[1].set(xlabel="Board side length, n", ylabel="Mean turns / n²", title="B. Normalised game length",
                xticks=sizes, xlim=(4.6, 9.4), ylim=(1.15, 1.52))
    for axis in axes:
        axis.grid(axis="y", color="#E7ECEF")
        axis.set_axisbelow(True)
    save_figure(fig, folder, "05_odd_even_comparison")

    fig, axis = plt.subplots(figsize=(7, 2.9), layout="constrained")
    bottom = np.zeros(5)
    for field, label, colour in [("mean_final_stones", "Stones left on board", BLUE),
                                 ("mean_captured_stones", "Captured stones", TEAL),
                                 ("mean_passes", "Passes", ORANGE)]:
        values = np.array([row[field] for row in rows]) / area
        axis.bar(sizes, values, bottom=bottom, width=0.58, color=colour, label=label)
        bottom += values
    for size, total in zip(sizes, bottom):
        axis.text(size, total + 0.035, f"{total:.3f}", ha="center", fontsize=8)
    axis.set(xlabel="Board side length, n", ylabel="Contribution to mean turns / n²",
             xticks=sizes, ylim=(0, 1.7))
    axis.legend(loc="upper left", ncol=3, frameon=False, fontsize=7.5)
    save_figure(fig, folder, "06_turn_count_components")


def main():
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=base / "raw")
    parser.add_argument("--output", type=Path, default=base / "analysis")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    unique, sources, duplicates, failures, inventory = load_records(args.input)
    groups, measured, game_rows = defaultdict(list), {}, []
    for key, record in sorted(unique.items()):
        if record.get("max_turns") != 500:
            raise ValueError("Unexpected real-game turn limit; do not silently pool different settings")
        try:
            measures = replay_and_measure(record)
        except ValueError as error:
            raise ValueError(f"Replay failed for {key}: {error}") from error
        measured[key] = measures
        groups[key[:4]].append(record)
        game_rows.append({
            "experiment": experiment_name(key), "size": key[0],
            "black_iterations": key[1], "white_iterations": key[2], "komi": key[3],
            "seed": key[4], "source_file": sources[key], "game_id_in_source": record["game_id"],
            "turns": record["turns"], "normalised_turns": record["turns"] / key[0] ** 2,
            **measures, "black_score": record["black_score"], "white_score": record["white_score"],
            "winner": record["winner"], "seconds": record["seconds"],
        })
    failure_rows = []
    for item in failures:
        record = item["record"]
        replay_and_measure(record)
        failure_rows.append({
            "source_file": item["source_file"], "size": record["size"],
            "black_iterations": record["black_iterations"], "white_iterations": record["white_iterations"],
            "komi": record["komi"], "seed": record["seed"], "status": record["status"],
            "turns_before_error": record["turns"], "error": record["error"],
            "recovered_in_completed_data": game_key(record) in unique,
        })
    summaries = [summarise(key, records, measured) for key, records in sorted(groups.items())]
    summary_by_key = {key: row for key, row in zip(sorted(groups), summaries)}
    models = fit_models(groups, summaries)
    baseline_9_seeds = sorted(r["seed"] for r in groups[(9, 100, 100, 7.5)])
    audit = {
        "source_jsonl_files": len(inventory),
        "source_records": sum(row["records"] for row in inventory),
        "unique_finished_games": len(unique), "duplicate_finished_records": len(duplicates),
        "failed_records": len(failure_rows),
        "unresolved_failed_seeds": [row["seed"] for row in failure_rows if not row["recovered_in_completed_data"]],
        "replayed_turns": sum(row["turns"] for row in game_rows)
                           + sum(row["turns_before_error"] for row in failure_rows),
        "replay_inconsistencies": 0,
        "nine_by_nine_missing_from_initial_seed_plan": sorted(set(range(19001, 19101)) - set(baseline_9_seeds)),
        "nine_by_nine_extra_to_initial_seed_plan": sorted(set(baseline_9_seeds) - set(range(19001, 19101))),
        "completed_games_at_most_six_turns": [
            {k: row[k] for k in ("experiment", "seed", "turns", "passes", "winner")}
            for row in game_rows if row["turns"] <= 6],
        "scope": "Independent move/rule/score replay; original MCTS source code was not supplied or audited",
    }
    output = {"study": "Board size and search budget in MCTS Go", "summaries": summaries,
              "models": models, "audit": audit,
              "versions": {"python": platform.python_version(), "numpy": np.__version__,
                           "scipy": scipy.__version__, "matplotlib": matplotlib.__version__}}
    write_csv(args.output / "games.csv", game_rows)
    write_csv(args.output / "experiment_summary.csv", summaries)
    write_csv(args.output / "source_inventory.csv", inventory)
    write_csv(args.output / "duplicate_records.csv", duplicates)
    write_csv(args.output / "failed_records.csv", failure_rows)
    (args.output / "analysis.json").write_text(json.dumps(output, indent=2), encoding="utf-8")
    plot_figures(groups, summary_by_key, models, args.output / "figures")
    print(f"Analysed {len(unique)} unique completed games; wrote six figures and summary tables to {args.output}")
    print(f"Quadratic coefficient: {models['quadratic']['coefficient']:.6f}")
    print(f"Equal-budget mean difference: {models['equal_budget_difference']['difference_turns']:.2f} turns")


if __name__ == "__main__":
    main()
