"""Parameter-study wrapper around the CSP-GeoTES TEA model.

Parameters are addressed by "<user_inputs name>.<key>" (e.g. "csp_specs.solar_multiple")
or just "<name>" for scalars (e.g. "qload"). Each case overrides user_inputs in
place, runs setup -> dispatch -> costing, records metrics, then restores inputs.

Edit STUDIES_TO_RUN and press Run Python File in VS Code.
Edit the value lists in STUDIES to change the parameter ranges.
Edit PLOT_METRICS to select figures (use ["all"] for every output).
Usage: python parameter_study.py [study_name ...] (arguments override selection)
Use --list to list available studies without running them.
Use --list-metrics to list available output columns.
Use --metrics all or --metrics <column> [<column> ...] to select plots.
Use --plot-existing <workbook.xlsx> to plot saved results without rerunning.
"""

import argparse
import contextlib
import copy
import io
import itertools
import sys
from datetime import datetime

import pandas as pd

import user_inputs
from plant_setup import initialize_plant
from plant_dispatch import run_dispatch
from plant_costing import calculate_costs
from parameter_study_plots import (
    DEFAULT_PLOT_METRICS, METRIC_LABELS, plot_study, plot_workbook, select_metrics,
)

# Used when pressing Play or running without command-line arguments.
# Use ["all"] for every study, or [] to only list available studies.
STUDIES_TO_RUN = ["load_size"]
PLOT_METRICS = DEFAULT_PLOT_METRICS.copy()

# ---------------------------------------------------------------------------
# Predefined studies: {name: {parameter_path: [values]}}; multiple keys = full grid
# ---------------------------------------------------------------------------
STUDIES = {
    # Sizing of the CSP field vs. thermal load / power block
    "solar_multiple": {"csp_specs.solar_multiple": [1.5, 2.0, 2.5, 3.0, 3.5, 4.0]},
    "load_size": {"qload": [100.0, 150.0, 200.0, 250.0, 300.0]},
    "power_block": {"ltpc_design.Wout": [50, 100, 150, 199, 250]},
    # Reservoir / subsurface
    "reservoir_temp": {"gtes_settings.Tinit": [30, 50, 70, 90]},
    "storage_mode": {"gtes_settings.mode": ["separate", "continuous", "push-pull"]},
    "recovery": {"gtes_settings.recovery": [0.7, 0.8, 0.9, 0.95, 1.0]},
    "flowrate": {
        "gtes_flowrate.production": [40, 80, 120],
        "gtes_flowrate.injection": [20, 40, 80],
    },
    "reservoir_geometry": {
        "gtes_props.depth": [500, 1000, 2000],
        "gtes_props.thickness": [50, 100, 200],
    },
    "well_count": {"exploration_specs.wells_count": [2, 3, 4, 6]},
    "reversible_wells": {"reversible_wells": [False, True]},
    # Cost and finance
    "mirror_cost": {"csp_costs.mirror": [60, 80, 105, 130]},
    "power_block_cost": {"ltpc_costs.power_block": [500, 750, 1000, 1250]},
    "finance_core": {
        "finance.irr": [0.06, 0.08, 0.10, 0.12],
        "finance.itc_rate": [0.0, 0.3, 0.4, 0.5],
    },
    "elec_price": {"finance.elec_price": [0.03, 0.05, 0.08, 0.12]},
    # Climate / operations
    "ambient_temp": {"ltpc_design.T0": [15, 25, 35]},
    "dispatch_window": {
        "operating_hours.op_hour1": [list(range(17, 25)), list(range(16, 24)), list(range(12, 24))],
    },
}


def _split(path):
    name, _, key = path.partition(".")
    if not hasattr(user_inputs, name):
        raise AttributeError(f"user_inputs has no '{name}'")
    return name, key


def _set(path, value):
    name, key = _split(path)
    if key:
        getattr(user_inputs, name)[key] = copy.deepcopy(value)
    else:
        setattr(user_inputs, name, copy.deepcopy(value))


def _get(path):
    name, key = _split(path)
    obj = getattr(user_inputs, name)
    return obj[key] if key else obj


def extract_metrics(plant, results):
    econ = plant.economics
    return {
        "LCOE_$/kWh": econ.LCOE,
        "LCOE_ITC_$/kWh": econ.LCOE_ITC,
        "LCOH": econ.LCOH,
        "LCOS": econ.LCOS,
        "geoTES_LCOE": results.geotes_lcoe,
        "geoTES_LCOE_ITC": results.geotes_lcoe_itc,
        "net_electricity": results.net_electricity,
        "capacity_factor_%": results.capacity_factor,
        "subsurface_capital": results.subsurface_capital,
        "surface_capital": econ.surface_capital_cost,
        "geotes_max_hours": results.geotes_max_hours,
        "geotes_capacity_hours": results.geotes_capacity_hours,
    }


def run_case(overrides, quiet=True):
    """Run the model once with {path: value} overrides; inputs are restored after."""
    saved = {_split(p)[0]: copy.deepcopy(getattr(user_inputs, _split(p)[0])) for p in overrides}
    try:
        for path, value in overrides.items():
            _set(path, value)
        sink = io.StringIO() if quiet else sys.stdout
        with contextlib.redirect_stdout(sink):
            plant = initialize_plant()
            qload_hourly = run_dispatch(plant)
            results = calculate_costs(plant, qload_hourly)
        return extract_metrics(plant, results)
    finally:
        for name, val in saved.items():
            setattr(user_inputs, name, val)


def run_sweep(grid, quiet=True):
    """Full-factorial sweep over {path: [values]}; returns a DataFrame."""
    keys = list(grid)
    rows = []
    for combo in itertools.product(*(grid[k] for k in keys)):
        overrides = dict(zip(keys, combo))
        row = {k: str(v) if isinstance(v, list) else v for k, v in overrides.items()}
        try:
            row.update(run_case(overrides, quiet))
        except Exception as exc:  # keep sweeping if one case is infeasible
            row["error"] = f"{type(exc).__name__}: {exc}"
        rows.append(row)
        print(f"  {row}")
    return pd.DataFrame(rows)


def main(names, metrics=None):
    if not names or names == ["--list"]:
        print("Available studies:", ", ".join(STUDIES))
        return
    unknown = [name for name in names if name not in STUDIES] if names != ["all"] else []
    if unknown:
        raise ValueError(
            f"Unknown studies: {', '.join(unknown)}. "
            f"Available studies: {', '.join(STUDIES)}. Use ['all'] to run every study."
        )
    user_inputs.output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = user_inputs.output_dir / f"parameter_study_{stamp}.xlsx"
    metrics = select_metrics(PLOT_METRICS if metrics is None else metrics)
    frames = {}
    with pd.ExcelWriter(out) as writer:
        for name in (STUDIES if names == ["all"] else names):
            print(f"Study: {name}")
            frames[name] = run_sweep(STUDIES[name])
            frames[name].to_excel(writer, sheet_name=name[:31], index=False)
    print(f"Saved: {out}")
    figure_dir = out.with_name(f"{out.stem}_figures")
    for name, frame in frames.items():
        for path in plot_study(frame, name, list(STUDIES[name]), figure_dir, metrics):
            print(f"Saved: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("studies", nargs="*", help="Study names, or all")
    parser.add_argument("--list", action="store_true", help="List available studies")
    parser.add_argument("--list-metrics", action="store_true", help="List plot metric names")
    parser.add_argument("--metrics", nargs="+", help="Metric column names, or all")
    parser.add_argument("--plot-existing", metavar="WORKBOOK", help="Plot a saved study workbook")
    args = parser.parse_args()
    if args.plot_existing and (args.studies or args.list or args.list_metrics):
        parser.error("--plot-existing cannot be combined with study names or list options")
    try:
        metrics = select_metrics(PLOT_METRICS if args.metrics is None else args.metrics)
    except ValueError as exc:
        parser.error(str(exc))
    if args.plot_existing:
        for path in plot_workbook(args.plot_existing, metrics):
            print(f"Saved: {path}")
    elif args.list_metrics:
        for key, label in METRIC_LABELS.items():
            print(f"{key}: {label}")
    elif args.list:
        main(["--list"])
    else:
        main(args.studies if args.studies else STUDIES_TO_RUN, metrics)
