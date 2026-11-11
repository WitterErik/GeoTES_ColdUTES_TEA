"""Plot parameter-study results without rerunning the plant model."""

import re
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


METRIC_LABELS = {
    "LCOE_$/kWh": "LCOE ($/kWh-e)",
    "LCOE_ITC_$/kWh": "LCOE with ITC ($/kWh-e)",
    "LCOH": "LCOH ($/kWh-th)",
    "LCOS": "LCOS ($/kWh-e)",
    "geoTES_LCOE": "GeoTES contribution to LCOE ($/kWh-e)",
    "geoTES_LCOE_ITC": "GeoTES contribution to LCOE with ITC ($/kWh-e)",
    "net_electricity": "Net electricity (GWh-e)",
    "capacity_factor_%": "Electricity capacity factor (%)",
    "subsurface_capital": "Subsurface capital cost ($)",
    "surface_capital": "Surface capital cost ($)",
    "geotes_max_hours": "Maximum stored energy (equivalent hours)",
    "geotes_capacity_hours": "Final-year net energy change (equivalent hours)",
}

DEFAULT_PLOT_METRICS = [
    "LCOE_$/kWh",
    "capacity_factor_%",
    "geotes_max_hours",
    "geotes_capacity_hours",
]

PARAMETER_LABELS = {
    "qload": "Thermal load (MW-th)",
}


def select_metrics(metrics):
    """Resolve a list of metric column names, or ['all'], to plot."""
    if metrics == ["all"]:
        return list(METRIC_LABELS)
    unknown = [metric for metric in metrics if metric not in METRIC_LABELS]
    if unknown:
        raise ValueError(f"Unknown plot metrics: {', '.join(unknown)}")
    return list(dict.fromkeys(metrics))


def plot_study(frame, name, parameters, output_dir, metrics=DEFAULT_PLOT_METRICS):
    """Save one PNG per metric, using the first parameter for the x-axis."""
    metrics = select_metrics(metrics)
    missing = [parameter for parameter in parameters if parameter not in frame.columns]
    if not parameters or missing:
        raise ValueError(f"Study {name!r} has missing or no parameter columns: {missing}")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    x_column = parameters[0]
    other_parameters = parameters[1:]
    if "error" in frame:
        failed = frame["error"].notna() & frame["error"].astype(str).str.strip().ne("")
    else:
        failed = pd.Series(False, index=frame.index)
    if failed.any():
        warnings.warn(f"{name}: {failed.sum()} failed case(s) will be omitted from plots.")

    saved = []
    for metric in metrics:
        if metric not in frame.columns:
            warnings.warn(f"{name}: metric {metric!r} is missing; no plot was saved.")
            continue
        data = frame.copy()
        data[metric] = pd.to_numeric(data[metric], errors="coerce").replace([np.inf, -np.inf], np.nan)
        data.loc[failed, metric] = np.nan
        if not data[metric].notna().any():
            warnings.warn(f"{name}: metric {metric!r} has no valid values; no plot was saved.")
            continue

        numeric_x = pd.to_numeric(data[x_column], errors="coerce")
        is_numeric = numeric_x.notna().all() and not pd.api.types.is_bool_dtype(data[x_column])
        if is_numeric:
            data[x_column] = numeric_x
            data = data.sort_values(x_column)
        else:
            data[x_column] = data[x_column].astype(str)
            categories = list(dict.fromkeys(data[x_column]))

        fig, ax = plt.subplots(figsize=(8, 5))
        try:
            if len(other_parameters) == 1:
                groups = data.groupby(other_parameters[0], sort=False, dropna=False)
            elif other_parameters:
                groups = data.groupby(other_parameters, sort=False, dropna=False)
            else:
                groups = [((), data)]
            for values, group in groups:
                if other_parameters:
                    if len(other_parameters) == 1:
                        values = (values,)
                    label = ", ".join(f"{key}={value}" for key, value in zip(other_parameters, values))
                else:
                    label = None
                x = group[x_column] if is_numeric else [categories.index(value) for value in group[x_column]]
                ax.plot(x, group[metric], marker="o", label=label)
            if not is_numeric:
                ax.set_xticks(range(len(categories)))
                ax.set_xticklabels(categories, rotation=30, ha="right")
            ax.set_xlabel(PARAMETER_LABELS.get(x_column, x_column))
            ax.set_ylabel(METRIC_LABELS[metric])
            ax.set_title(f"{name.replace('_', ' ').title()}: {METRIC_LABELS[metric]}")
            ax.grid(True, alpha=0.3)
            if other_parameters:
                ax.legend(title="Other inputs", fontsize="small")
            fig.tight_layout()
            safe_metric = re.sub(r"[^A-Za-z0-9_]+", "_", metric).strip("_")
            output = output_dir / f"{name}_{safe_metric}.png"
            fig.savefig(output, dpi=200)
            saved.append(output)
        finally:
            plt.close(fig)
    return saved


def plot_workbook(workbook, metrics=DEFAULT_PLOT_METRICS):
    """Plot all sheets in an existing parameter-study workbook."""
    workbook = Path(workbook)
    output_dir = workbook.with_name(f"{workbook.stem}_figures")
    saved = []
    for name, frame in pd.read_excel(workbook, sheet_name=None).items():
        parameters = [column for column in frame.columns if column not in METRIC_LABELS and column != "error"]
        saved.extend(plot_study(frame, name, parameters, output_dir, metrics))
    return saved
