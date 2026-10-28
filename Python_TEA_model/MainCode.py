"""Thin entry point for the split CSP–GeoTES TEA model."""

import user_inputs
from plant_setup import initialize_plant
from plant_dispatch import run_dispatch
from plant_costing import calculate_costs
from plant_report import export_report, print_report


def main():
    """Coordinate the model stages; calculations live in their own modules."""
    user_inputs.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Verified output directory exists at: {user_inputs.output_dir}")

    plant = initialize_plant()
    qload_hourly = run_dispatch(plant)
    results = calculate_costs(plant, qload_hourly)
    print_report(results)
    report_path = export_report(results, user_inputs.output_dir)
    print(f"Excel report exported to: {report_path}")
    return plant, qload_hourly, results


if __name__ == "__main__":
    plant, qload_hourly, results = main()
