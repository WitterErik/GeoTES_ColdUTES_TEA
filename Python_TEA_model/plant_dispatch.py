"""SAM coupling and hourly plant/GeoTES dispatch."""

import numpy as np

import user_inputs
from SAM.call_SAM import call_SAM


def run_dispatch(plant):
    """Run SAM and dispatch CSP, power cycle, GeoTES, and configured thermal load."""
    csp = plant.csp
    power_cycle = plant.power_cycle
    geotes = plant.geotes
    n_years = plant.n_years
    total_hours = plant.total_hours

    print("☁️  Simulating meteorological solar performance (call_SAM)...")
    sam_output = call_SAM(csp, power_cycle)

    csp.mirror_aperture = sam_output.mirror_area
    csp.land_area = sam_output.land_area
    csp.nominal_eff = sam_output.nominal_eff
    csp.annual_eff = sam_output.annual_eff
    csp.DNI = sam_output.DNI

    csp.power = np.maximum(
        np.tile(np.asarray(sam_output.field_thermal_power, dtype=float).ravel(), n_years),
        0.0,
    )
    power_cycle.Tamb = np.tile(np.asarray(sam_output.Tamb, dtype=float).ravel(), n_years)

    geotes.energy = np.zeros(total_hours, dtype=float)
    geotes.power = np.zeros(total_hours, dtype=float)
    csp.dumped = np.zeros(total_hours, dtype=float)
    power_cycle.Qin = np.zeros(total_hours, dtype=float)
    qload = float(user_inputs.qload)
    qload_hourly = np.zeros(total_hours, dtype=float)

    dt = 1.0
    power_cycle.Qin[0] = csp.power[0]
    power_cycle.interpolate_off_design(0)

    print(f"⏳ Running {total_hours}-hour plant dispatch loop...")
    for i in range(1, total_hours):
        geotes.energy[i] = geotes.energy[i - 1]
        hour = (i % 24) + 1
        hour_of_year = (i % 8760) + 1

        if user_inputs.phases["phase1"][0] <= hour_of_year < user_inputs.phases["phase1"][1]:
            operates_power_cycle = hour in user_inputs.operating_hours["op_hour1"]
        elif user_inputs.phases["phase2"][0] <= hour_of_year < user_inputs.phases["phase2"][1]:
            operates_power_cycle = hour in user_inputs.operating_hours["op_hour2"]
        else:
            operates_power_cycle = hour in user_inputs.operating_hours["op_hour3"]

        if operates_power_cycle:
            if csp.power[i] > power_cycle.Qin0 + qload:
                power_cycle.Qin[i] = power_cycle.Qin0
                power_cycle.interpolate_off_design(i)
                qload_hourly[i] = qload
                available_charge = csp.power[i] - power_cycle.Qin0 - qload
                geotes.power[i] = min(available_charge, geotes.Qmax)
                csp.dumped[i] = max(available_charge - geotes.Qmax, 0.0)
                geotes.energy[i] = (
                    geotes.energy[i - 1] + geotes.power[i] * dt * geotes.recovery
                )
            else:
                required_discharge = power_cycle.Qin0 + qload - csp.power[i]
                if required_discharge * dt < geotes.energy[i - 1]:
                    geotes.power[i] = -required_discharge
                    geotes.energy[i] = geotes.energy[i - 1] + geotes.power[i]
                    power_cycle.Qin[i] = power_cycle.Qin0
                    power_cycle.interpolate_off_design(i)
                    qload_hourly[i] = qload
                else:
                    geotes.power[i] = -geotes.energy[i - 1] / dt
                    geotes.energy[i] = geotes.energy[i - 1] + geotes.power[i]
                    if csp.power[i] + geotes.power[i] > power_cycle.Qin0:
                        power_cycle.Qin[i] = power_cycle.Qin0
                        power_cycle.interpolate_off_design(i)
                        qload_hourly[i] = csp.power[i] + geotes.power[i] - power_cycle.Qin0
                    else:
                        power_cycle.Qin[i] = csp.power[i] - geotes.power[i]
                        power_cycle.interpolate_off_design(i)
        elif csp.power[i] > qload:
            qload_hourly[i] = qload
            available_charge = csp.power[i] - qload
            geotes.power[i] = min(available_charge, geotes.Qmax)
            csp.dumped[i] = max(available_charge - geotes.Qmax, 0.0)
            geotes.energy[i] = (
                geotes.energy[i - 1] + geotes.power[i] * dt * geotes.recovery
            )
        else:
            required_discharge = qload - csp.power[i]
            if required_discharge * dt < geotes.energy[i - 1]:
                geotes.power[i] = -required_discharge
                geotes.energy[i] = geotes.energy[i - 1] + geotes.power[i]
                qload_hourly[i] = qload
            else:
                geotes.power[i] = -geotes.energy[i - 1] / dt
                geotes.energy[i] = geotes.energy[i - 1] + geotes.power[i]
                qload_hourly[i] = csp.power[i] - geotes.power[i]

    return qload_hourly
