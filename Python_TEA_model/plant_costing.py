"""GeoTES wellfield costing and levelized-cost calculations."""

import numpy as np
from types import SimpleNamespace

import user_inputs
import initialization

initialization.setup_environmental_paths()

from DrillingCostUpdated import DrillingCostUpdated
from ExplorationCost import ExplorationCost
from InjectionPumpingCost import InjectionPumpingCost
from ProductionPumpingCost import ProductionPumpingCost


def _production_pump(geotes, state, n_wells):
    """Return production-pump estimator, duty/cost tuple, and maintenance cost."""
    flowrate = geotes.flowrate_per_well_prod * state.rho / 1000.0
    pump = ProductionPumpingCost(
        geotes.Tinit, flowrate, n_wells, 6370, geotes.depth,
        geotes.thickness, "Small", "Lineshaft", "Liner", 1.553,
    )
    prod_head = pump.head_prod_top()
    suction_depth = pump.suction_depth(pump.head_suction(prod_head))
    power = pump.pump_power(
        suction_depth, pump.casing_friction(suction_depth, prod_head)
    )
    cost = pump.pump_cost(power, suction_depth)
    duty_cost = pump.total_pump_duty_cost(power, cost)
    maintenance = pump.pump_maintenance_cost(suction_depth, cost)
    return pump, flowrate, duty_cost, maintenance


def _injection_pump(geotes, state, production_flowrate, injection_temperature, mode):
    """Return injection-pump estimator and duty/cost tuple."""
    injection_flowrate = geotes.flowrate_per_well_inj * state.rho / 1000.0
    pressure_source = state.p * 14.5038
    pump = InjectionPumpingCost(
        geotes.Tinit, injection_temperature, injection_flowrate,
        production_flowrate, pressure_source,
        geotes.discharge_inj_Nwell if mode == "Discharge" else geotes.charge_inj_Nwell,
        7645, geotes.depth, geotes.thickness, "Small", "Openhole", 1.533, mode,
    )
    pump_power = pump.pump_power(pump.head_injection(pump.head_suction()))
    pump_cost = pump.pump_cost(pump_power)
    return pump, pump.total_pump_duty_cost(pump_power, pump_cost)


def calculate_costs(plant, qload_hourly):
    """Calculate annual metrics and return costs and reporting values."""
    csp = plant.csp
    cycle = plant.power_cycle
    geotes = plant.geotes
    econ = plant.economics
    n_years = plant.n_years
    qload = float(user_inputs.qload)

    print("📈 Processing annual energy balances...")
    geotes.geoTES_size()
    geotes.geoTES_well_flows()
    csp.CSP_annual_energy()
    cycle.PC_annual_energy()
    geotes.geoTES_annual_energy()
    csp.calc_CSP_cost(cycle)
    cycle.calc_PC_cost()

    print("🏗️  Calculating subsurface exploration, drilling, and capital structures...")
    exploration = user_inputs.exploration_specs
    total_exploration_cost = ExplorationCost(
        exploration["field_type"], exploration["wells_count"],
        exploration["target_depth"], exploration["cost_multiplier"],
    ).exploration_cost_calc()
    field_permitting = initialization.BASE_PERMITTING_COST * initialization.PPI_MULTIPLIER

    zero_duty = (0.0, 0.0)
    if geotes.mode == "separate":
        charge_prod_drill = DrillingCostUpdated(
            geotes.charge_prod_Nwell, 0, geotes.depth, geotes.thickness,
            "Small", 1, 1.5, "Deviated", "Liner",
        )
        charge_drill_prod_cost = charge_prod_drill.TotalDC(charge_prod_drill.WellCost())
        charge_inj_drill = DrillingCostUpdated(
            0, geotes.charge_inj_Nwell, geotes.depth, geotes.thickness,
            "Small", 1, 1.5, "Deviated", "Openhole",
        )
        charge_drill_inj_cost = charge_inj_drill.TotalDC(charge_inj_drill.WellCost())

        charge_prod_pump, charge_prod_flow, charge_prod_duty, charge_prod_maintenance = _production_pump(
            geotes, geotes.charge_production, geotes.charge_prod_Nwell
        )
        _, charge_inj_duty = _injection_pump(
            geotes, geotes.charge_injection, charge_prod_flow,
            cycle.Tmax, "Charge",
        )
        charge_flowline_cost = (
            initialization.FLOWLINE_LENGTH_M * initialization.M_TO_FT
            * initialization.PIPING_UNIT_COST_USD_FT
            * (geotes.charge_prod_Nwell + geotes.charge_inj_Nwell)
        )
        charge_well_maintenance = 0.015 * (
            charge_drill_prod_cost + charge_drill_inj_cost + charge_flowline_cost
        )
        charge_makeup_water = (
            initialization.MAKEUP_WATER_UNIT_COST * geotes.charge_prod_Nwell
            * (charge_prod_flow * 18.0917 * 34.2857 * 365)
            * (initialization.OIL_SATURATION + initialization.SUBSURFACE_WATER_LOSS_BASE)
        )
    elif geotes.mode == "continuous":
        charge_drill_prod_cost = charge_drill_inj_cost = 0.0
        charge_prod_duty = charge_inj_duty = zero_duty
        charge_flowline_cost = charge_well_maintenance = 0.0
        charge_prod_maintenance = charge_makeup_water = 0.0
    else:
        raise ValueError(f"Unsupported GeoTES mode for costing: {geotes.mode}")

    discharge_prod_drill = DrillingCostUpdated(
        geotes.discharge_prod_Nwell, 0, geotes.depth, geotes.thickness,
        "Small", 1, 1.5, "Deviated", "Liner",
    )
    discharge_drill_prod_cost = (
        0.0 if user_inputs.reversible_wells
        else discharge_prod_drill.TotalDC(discharge_prod_drill.WellCost())
    )
    discharge_inj_drill = DrillingCostUpdated(
        0, geotes.discharge_inj_Nwell, geotes.depth, geotes.thickness,
        "Small", 1, 1.5, "Deviated", "Openhole",
    )
    discharge_drill_inj_cost = (
        0.0 if user_inputs.reversible_wells
        else discharge_inj_drill.TotalDC(discharge_inj_drill.WellCost())
    )

    discharge_prod_pump, discharge_prod_flow, discharge_prod_duty, discharge_prod_maintenance = _production_pump(
        geotes, geotes.discharge_production, geotes.discharge_prod_Nwell
    )
    _, discharge_inj_duty = _injection_pump(
        geotes, geotes.discharge_injection, discharge_prod_flow,
        geotes.Tinit, "Discharge",
    )
    if user_inputs.reversible_wells:
        discharge_inj_duty = zero_duty

    discharge_flowline_cost = (
        0.0 if user_inputs.reversible_wells
        else initialization.FLOWLINE_LENGTH_M * initialization.M_TO_FT
        * initialization.PIPING_UNIT_COST_USD_FT
        * (geotes.discharge_prod_Nwell + geotes.discharge_inj_Nwell)
    )
    discharge_well_maintenance = 0.015 * (
        discharge_drill_prod_cost + discharge_drill_inj_cost + discharge_flowline_cost
    )
    discharge_makeup_water = (
        initialization.MAKEUP_WATER_UNIT_COST * geotes.discharge_prod_Nwell
        * (discharge_prod_flow * 18.0917 * 34.2857 * 365)
        * (initialization.OIL_SATURATION + initialization.SUBSURFACE_WATER_LOSS_BASE)
    )

    subsurface_capital_cost = (
        total_exploration_cost + field_permitting
        + charge_drill_prod_cost + charge_drill_inj_cost
        + discharge_drill_prod_cost + discharge_drill_inj_cost
        + charge_prod_duty[1] + charge_inj_duty[1]
        + discharge_prod_duty[1] + discharge_inj_duty[1]
        + charge_flowline_cost + discharge_flowline_cost
    )
    annual_tax_insurance = initialization.PROPERTY_TAX_RATE * subsurface_capital_cost
    subsurface_om = (
        charge_well_maintenance + charge_prod_maintenance + charge_makeup_water
        + discharge_well_maintenance + discharge_prod_maintenance
        + discharge_makeup_water + annual_tax_insurance
    )

    print("💰 Calculating plant-level LCOE and capacity metrics...")
    year_start = (n_years - 1) * 8760
    year_end = n_years * 8760
    final_year_power = geotes.power[year_start:year_end]
    charging_hours = int(np.sum(final_year_power > 0))
    discharging_hours = int(np.sum(final_year_power < 0))
    discharge_air_fan = discharging_hours * cycle.fan0 * cycle.Wout0 / 1e3

    if geotes.mode == "separate":
        energy_charge_prod = charging_hours * charge_prod_duty[0] / 1e6
        energy_charge_inj = charging_hours * charge_inj_duty[0] / 1e6
        energy_discharge_prod = discharging_hours * discharge_prod_duty[0] / 1e6
        energy_discharge_inj = discharging_hours * discharge_inj_duty[0] / 1e6
    else:
        energy_charge_prod = charging_hours * discharge_prod_duty[0] / 1e6
        energy_charge_inj = charging_hours * discharge_inj_duty[0] / 1e6
        energy_discharge_prod = discharging_hours * discharge_prod_duty[0] / 1e6
        energy_discharge_inj = discharging_hours * discharge_inj_duty[0] / 1e6

    net_discharge_power = (
        cycle.Wout0 - discharge_prod_duty[0] / 1e3
        - discharge_inj_duty[0] / 1e3 - cycle.fan0 * cycle.Wout0
    )
    geotes_max_hours = geotes.energy_capacity * 1000 / (cycle.Wout0 / cycle.eff0)
    geotes_max_elec = net_discharge_power * geotes_max_hours / 1e3
    geotes_capacity_hours = geotes.net_energy * 1000 / (cycle.Wout0 / cycle.eff0)
    geotes_capacity_elec = net_discharge_power * geotes_capacity_hours / 1e3

    offsets = user_inputs.finance_baseline_offsets
    econ.surface_capital_cost = (
        csp.total_cost + cycle.total_cost + 250 * qload * 1000
        - offsets["lcoh_csp_offset"]
    )
    econ.OnM_surface = (
        econ.OnM * (csp.total_cost + cycle.total_cost + 250 * qload * 1000)
        - offsets["lcoh_om_offset"]
    )
    econ.subsurface_capital_cost = subsurface_capital_cost - offsets["lcoh_sub_cap_offset"]
    econ.OnM_subsurface = subsurface_om - offsets["lcoh_sub_om_offset"]
    econ.Ein = (
        energy_charge_prod + energy_charge_inj + energy_discharge_prod
        + energy_discharge_inj - offsets["lcoh_ein_offset"]
    )
    econ.Qout = float(np.sum(qload_hourly[year_start:year_end]) / 1e3)
    econ.calc_fcr()
    econ.calc_levelized_cost("H")

    econ.subsurface_capital_cost = subsurface_capital_cost
    econ.OnM_subsurface = subsurface_om
    econ.surface_capital_cost = csp.total_cost + cycle.total_cost
    econ.OnM_surface = econ.OnM * econ.surface_capital_cost
    econ.Ein = energy_charge_prod + energy_charge_inj
    econ.Eout = cycle.Wout_tot - energy_discharge_prod - energy_discharge_inj - discharge_air_fan
    econ.calc_fcr()
    econ.calc_levelized_cost("E")

    capital_costs_millions = np.array([
        total_exploration_cost, field_permitting,
        charge_drill_prod_cost + charge_drill_inj_cost,
        charge_prod_duty[1], charge_inj_duty[1], charge_flowline_cost,
        discharge_drill_prod_cost + discharge_drill_inj_cost,
        discharge_prod_duty[1], discharge_inj_duty[1], discharge_flowline_cost,
        csp.total_cost, cycle.total_cost,
    ]) / 1e6
    geotes_capital = float(np.sum(capital_costs_millions[:10]))
    geotes_lcoe = (
        (geotes_capital * econ.FCR * 1e6 + econ.OnM_subsurface)
        / (econ.Eout * geotes.energy_out_tot / cycle.Qin_tot) / 1e6
    )
    geotes_lcoe_itc = (
        (geotes_capital * econ.FCR * 1e6 * (1 - econ.ITC) + econ.OnM_subsurface)
        / (econ.Eout * geotes.energy_out_tot / cycle.Qin_tot) / 1e6
    )
    net_electricity = econ.Eout
    capacity_factor = (
        100 * 1000 * net_electricity / net_discharge_power / 8760
    )

    return SimpleNamespace(
        plant=plant,
        exploration_cost=total_exploration_cost,
        permitting_cost=field_permitting,
        charge_drill_prod=charge_drill_prod_cost,
        charge_drill_inj=charge_drill_inj_cost,
        charge_prod_duty=charge_prod_duty,
        charge_inj_duty=charge_inj_duty,
        charge_flowline=charge_flowline_cost,
        discharge_drill_prod=discharge_drill_prod_cost,
        discharge_drill_inj=discharge_drill_inj_cost,
        discharge_prod_duty=discharge_prod_duty,
        discharge_inj_duty=discharge_inj_duty,
        discharge_flowline=discharge_flowline_cost,
        subsurface_capital=subsurface_capital_cost,
        subsurface_om=subsurface_om,
        charging_hours=charging_hours,
        discharging_hours=discharging_hours,
        discharge_air_fan=discharge_air_fan,
        geotes_max_hours=geotes_max_hours,
        geotes_max_elec=geotes_max_elec,
        geotes_capacity_hours=geotes_capacity_hours,
        geotes_capacity_elec=geotes_capacity_elec,
        geotes_lcoe=geotes_lcoe,
        geotes_lcoe_itc=geotes_lcoe_itc,
        net_electricity=net_electricity,
        capacity_factor=capacity_factor,
        year_start=year_start,
        year_end=year_end,
        qload=qload,
    )
