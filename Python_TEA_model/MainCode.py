# translating PRM matlab code to python

import numpy as np 
import pandas as pd
import shutil
import sys

import user_inputs
import initialization
from solar_class_update import solar_class


# dynamicall add dependencies
dependencies = [
    user_inputs.subsurface_dir,
    user_inputs.utility_dir,
    user_inputs.SAM_dir,
    user_inputs.data_dir
]

for folder in dependencies:
    if folder.exists():
        sys.path.append(str(folder))
    else:
        print(f"Warning: Dependency folder not found {folder}")
# can now safely import modules in the various subfolders
# e.g. from subsurface_model import solve_geothermal_flow

try:
    from thermo_cycle_class_update import thermo_cycle_class
    from geoTES_class_update import geoTES_class
    from economic_class_update import economics_class
    from fluid_class_update import calc_fluid_props
    from external_models import call_SAM
    from interpolation import interpolate_off_design
    from subsurface import (
        ExplorationCost,
        DrillingCostUpdated,
        ProductionPumpingCost,
        InjectionPumpingCost,
        geoTES_size,
        geoTES_well_flows,
        CSP_annual_energy,
        PC_annual_energy,
        geoTES_annual_energy,
        calc_CSP_cost,
        calc_PC_cost,
    )
except ImportError as e:
    print(f"Warning during submodule imports: {e}")
    print("Ensure these translation classes are located inside your dependency subfolders.")


def main():
    # create output folder if it does not exist
    user_inputs.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Verified output directory exists at: {user_inputs.output_dir}")


    # set up classes and run simulation
    location = user_inputs.system["location"]
    nY = user_inputs.system["nY'"]
    total_hours = nY * 8760

    # ==========================================
    # CSP set up
    # ==========================================
    mirror_type = user_inputs.csp_specs["mirror_type"]
    nominal_dni = user_inputs.csp_specs["nominal_dni"]
    solar_multiple = user_inputs.csp_specs["solar_multiple"]
    csp_tmax = user_inputs.csp_specs["csp_tmax"]
    csp_tmin = user_inputs.csp_specs["csp_tmin"]
    csp_land_mult = user_inputs.csp_specs["csp_land_mult"]
    csp_cost = user_inputs.csp_costs

    print("☀️ Initializing solar CSP calculation system...")
    csp_system = solar_class(location, mirror_type, nominal_dni, solar_multiple, ...)

    # ==========================================
    # Low-Temperature Power Cycle (LTPC)
    # ==========================================
    # Extract values from our configuration
    ltpc_type = user_inputs.ltpc_type
    ltpc_design = user_inputs.ltpc_design
    
    # convert the pathlib Path object to a string format if the underlying 
    # thermo_cycle_class expects a file path string (like Excel readers usually do)
    ltpc_foff = str(user_inputs.ltpc_foff)
    
    ltpc_costs = user_inputs.ltpc_costs

    print("🔄 Initializing Thermodynamic Power Cycle Class (LTPC)...")
    ltpc_system = thermo_cycle_class(
        ltpc_type,
        ltpc_design,
        ltpc_foff,
        ltpc_costs,
        nY
    )

    # ==========================================
    # Low-temp geoTES
    # ==========================================
    gtes_recovery = user_inputs.gtes_settings["recovery"]
    gtes_tinit = user_inputs.gtes_settings["t_init"]
    gtes_qmax = user_inputs.gtes_settings["q_max"]
    gtes_fluid = user_inputs.gtes_settings["fluid"]
    gtes_mode = user_inputs.gtes_settings["mode"]
    
    gtes_flowrate = user_inputs.gtes_flowrate
    gtes_props = user_inputs.gtes_props

    print("🕳️ Initializing Geothermal Thermal Energy Storage Class (gTES)...")
    gtes_system = geoTES_class(
        gtes_recovery,
        gtes_tinit,
        gtes_flowrate,
        gtes_qmax,
        gtes_props,
        gtes_fluid,
        gtes_mode,
        nY
    )


    # ==========================================
    # Economic Evaluator (econ)
    # ==========================================
    finance_inputs = user_inputs.finance

    print("💰 Initializing Economics Evaluation Class...")
    econ_system = economics_class(finance_inputs)


    # ==========================================
    # Initialize Operational States
    # ==========================================
    print("❄️  Loading initial operational states and fluid boundaries...")
    
    # Fetch and unpack all initial states from our initialization file
    (gtes_system.charge_production,
        gtes_system.charge_injection,
        gtes_system.discharge_production,
        gtes_system.discharge_injection) = initialization.initialize_gtes_states()

    # Calculate remaining fluid properties
    gtes_system.charge_production = calc_fluid_props(gtes_system.charge_production, 'pT')
    gtes_system.charge_injection = calc_fluid_props(gtes_system.charge_injection, 'pT')
    gtes_system.discharge_production = calc_fluid_props(gtes_system.discharge_production, 'qT')
    gtes_system.discharge_injection = calc_fluid_props(gtes_system.discharge_injection, 'pT')

    print("✅ Initial fluid states calculated.")        

    # ==========================================
    # Annual Energy Flows & Meteorological (SAM) Solvers
    # ==========================================
    print("☁️  Simulating meteorological solar performance (call_SAM)...")
    out = call_SAM(csp_system, ltpc_system)
    
    csp_system.mirror_aperture = out.mirror_area
    csp_system.land_area = out.land_area
    csp_system.nominal_eff = out.nominal_eff
    csp_system.annual_eff = out.annual_eff
    csp_system.DNI = out.DNI

    dt = 1  # Timestep = 1 hour

    # Tile solar field outputs over years
    csp_system.power = np.tile(out.field_thermal_power, nY)
    ltpc_system.Tamb = np.tile(out.Tamb, nY)

    # Vectorized clip to zero for negative values
    csp_system.power = np.maximum(csp_system.power, 0)

    # Pre-allocate monitoring arrays
    gtes_system.energy = np.zeros(total_hours)
    gtes_system.power = np.zeros(total_hours)
    csp_system.dumped = np.zeros(total_hours)
    ltpc_system.Qin = np.zeros(total_hours)

    # First time-step setup (Python zero-indexing)
    ltpc_system.Qin[0] = csp_system.power[0]
    ltpc_system = interpolate_off_design(ltpc_system, 0)

    # Dispatch Clock
    hour = 2
    houry = 2

    # ==========================================
    # Main Plant Dispatch Loop
    # ==========================================
    print(f"⏳ Running {total_hours}-hour plant dispatch loop...")
    
    for i in range(1, total_hours):
        gtes_system.energy[i] = gtes_system.energy[i-1]

        operate = False
        if user_inputs.phases["phase1"][0] <= houry < user_inputs.phases["phase1"][1]:
            operate = hour in user_inputs.operating_hours["op_hour1"]
        elif user_inputs.phases["phase2"][0] <= houry < user_inputs.phases["phase2"][1]:
            operate = hour in user_inputs.operating_hours["op_hour2"]
        elif user_inputs.phases["phase3"][0] <= houry < user_inputs.phases["phase3"][1]:
            operate = hour in user_inputs.operating_hours["op_hour3"]

        if operate:
            if csp_system.power[i] > ltpc_system.Qin0:
                ltpc_system.Qin[i] = ltpc_system.Qin0
                ltpc_system = interpolate_off_design(ltpc_system, i)

                dP = csp_system.power[i] - ltpc_system.Qin0
                if dP < gtes_system.Qmax:
                    gtes_system.power[i] = dP
                else:
                    gtes_system.power[i] = gtes_system.Qmax
                    csp_system.dumped[i] = dP - gtes_system.Qmax

                gtes_system.energy[i] = gtes_system.energy[i-1] + (gtes_system.power[i] * dt * gtes_system.recovery)
            else:
                dP = ltpc_system.Qin0 - csp_system.power[i]
                if (dP * dt) < gtes_system.energy[i-1]:
                    gtes_system.power[i] = -dP
                    gtes_system.energy[i] = gtes_system.energy[i-1] + gtes_system.power[i]
                    
                    ltpc_system.Qin[i] = ltpc_system.Qin0
                    ltpc_system = interpolate_off_design(ltpc_system, i)
                else:
                    gtes_system.power[i] = -gtes_system.energy[i-1] / dt
                    gtes_system.energy[i] = gtes_system.energy[i-1] + gtes_system.power[i]
                    
                    ltpc_system.Qin[i] = csp_system.power[i] - gtes_system.power[i]
                    ltpc_system = interpolate_off_design(ltpc_system, i)
        else:
            dP = csp_system.power[i]
            if dP < gtes_system.Qmax:
                gtes_system.power[i] = dP
            else:
                gtes_system.power[i] = gtes_system.Qmax
                csp_system.dumped[i] = dP - gtes_system.Qmax

            gtes_system.energy[i] = gtes_system.energy[i-1] + (gtes_system.power[i] * dt * gtes_system.recovery)

        # Update Timers
        hour += 1
        houry += 1

        if hour == 25:
            hour = 1
        if houry == 8761:
            houry = 1

    # ==========================================
    # Sizing, Annual performance, and system cost structures
    # ==========================================
    print("📈 Processing annual energy balances...")
    gtes_system = geoTES_size(gtes_system)
    gtes_system = geoTES_well_flows(gtes_system)

    csp_system = CSP_annual_energy(csp_system)
    ltpc_system = PC_annual_energy(ltpc_system)
    gtes_system = geoTES_annual_energy(gtes_system)

    csp_system = calc_CSP_cost(csp_system, ltpc_system)
    ltpc_system = calc_PC_cost(ltpc_system)

    # ==========================================
    # Exploration & Permitting Capital Costs
    # ==========================================
    print("🏗️  Calculating subsurface exploration, drilling, and capital structures...")
    
    exploration_calc = ExplorationCost(
        user_inputs.exploration["type"],
        user_inputs.exploration["wells_count"],
        user_inputs.exploration["target_depth"],
        user_inputs.exploration["cost_multiplier"]
    )
    total_exploration_cost = exploration_calc.ExplorationCostCalc()

    field_dev_plant_permitting = (
        initialization.BASE_PERMITTING_COST * 
        initialization.PPI_MULTIPLIER
    )

    # ==========================================
    # Charge Well Capital Cost Calculations (By Mode)
    # ==========================================
    if gtes_system.mode == "separate":
        # Charge Production Drilling Cost
        charge_drilling_cost_prod = DrillingCostUpdated(
            gtes_system.charge_prod_Nwell, 0, gtes_system.depth, gtes_system.thickness,
            "Small", 1, 1.5, "Deviated", "Liner"
        )
        charge_well_cost_prod = charge_drilling_cost_prod.WellCost()
        total_charge_drilling_cost_prod = charge_drilling_cost_prod.TotalDC(charge_well_cost_prod)

        # Charge Injection Drilling Cost
        charge_drilling_cost_inj = DrillingCostUpdated(
            0, gtes_system.charge_inj_Nwell, gtes_system.depth, gtes_system.thickness,
            "Small", 1, 1.5, "Deviated", "Openhole"
        )
        charge_well_cost_inj = charge_drilling_cost_inj.WellCost()
        total_charge_drilling_cost_inj = charge_drilling_cost_inj.TotalDC(charge_well_cost_inj)

        # Production Pumping during Charge
        p_flowrate = gtes_system.flowrate_per_well_prod * gtes_system.charge_production.rho / 1000
        charge_prod_pumping_estimation = ProductionPumpingCost(
            gtes_system.tinit, p_flowrate, gtes_system.charge_prod_Nwell, 6370,
            gtes_system.depth, gtes_system.thickness, "Small", "Lineshaft", "Liner", 1.553
        )
        step3 = charge_prod_pumping_estimation.Sunctiondepth(
            charge_prod_pumping_estimation.HeadSunction(charge_prod_pumping_estimation.HeadProdTop().Prodtop)
        )
        step5 = charge_prod_pumping_estimation.Pumppower(
            step3, charge_prod_pumping_estimation.CasingFriction(step3, charge_prod_pumping_estimation.HeadProdTop().Prodtop)
        )
        step6 = charge_prod_pumping_estimation.Pumpcost(step5, step3)
        charge_prod_pumping_cost_duty = charge_prod_pumping_estimation.TotalPumpDutyCost(step5, step6)

        # Injection Pumping during Charge
        i_flowrate = gtes_system.flowrate_per_well_inj * gtes_system.charge_injection.rho / 1000
        pressure_thermal_source = gtes_system.charge_injection.p * 14.5038
        charge_inj_pumping_estimation = InjectionPumpingCost(
            gtes_system.tinit, ltpc_system.Tmax, i_flowrate, p_flowrate, pressure_thermal_source,
            gtes_system.charge_inj_Nwell, 7645, gtes_system.depth, gtes_system.thickness,
            "Small", "Openhole", 1.533, "Charge"
        )
        step9 = charge_inj_pumping_estimation.Pumppower(
            charge_inj_pumping_estimation.HeadInjection(charge_inj_pumping_estimation.HeadSunction())
        )
        step10 = charge_inj_pumping_estimation.Pumpcost(step9)
        charge_inj_pumping_cost_duty = charge_inj_pumping_estimation.TotalPumpDutyCost(step9, step10)

        # Surface Piping Lines
        total_number_of_wells = gtes_system.charge_prod_Nwell + gtes_system.charge_inj_Nwell
        charge_flowline_cost = (
            initialization.FLOWLINE_LENGTH_M * 
            initialization.M_TO_FT * 
            initialization.PIPING_UNIT_COST_USD_FT * 
            total_number_of_wells
        )

        # Well field O&M, pump maintenance, makeup water costs
        charge_wellfield_maintenance = 0.015 * (
            total_charge_drilling_cost_prod + total_charge_drilling_cost_inj + charge_flowline_cost
        )
        charge_pump_maintenance = charge_prod_pumping_estimation.PumpMaintenanceCost(step3, step6)
        charge_makeup_water_subsurface = (
            initialization.MAKEUP_WATER_UNIT_COST * gtes_system.charge_prod_Nwell * 
            (p_flowrate * 18.0917 * 34.2857 * 365) * 
            (initialization.OIL_SATURATION + initialization.SUBSURFACE_WATER_LOSS_BASE)
        )

    elif gtes_system.mode == "continuous":
        total_charge_drilling_cost_prod = 0.0
        total_charge_drilling_cost_inj = 0.0
        charge_prod_pumping_cost_duty = [0.0, 0.0]
        charge_inj_pumping_cost_duty = [0.0, 0.0]
        charge_flowline_cost = 0.0
        charge_wellfield_maintenance = 0.0
        charge_pump_maintenance = 0.0
        charge_makeup_water_subsurface = 0.0

    # ==========================================
    # Discharge Well Capital Cost Calculations
    # ==========================================
    discharge_drilling_cost_prod = DrillingCostUpdated(
        gtes_system.discharge_prod_Nwell, 0, gtes_system.depth, gtes_system.thickness,
        "Small", 1, 1.5, "Deviated", "Liner"
    )
    discharge_well_cost_prod = discharge_drilling_cost_prod.WellCost()
    
    total_discharge_drilling_cost_prod = (
        0.0 if user_inputs.gtes_settings["reversible_wells"] 
        else discharge_drilling_cost_prod.TotalDC(discharge_well_cost_prod)
    )

    discharge_drilling_cost_inj = DrillingCostUpdated(
        0, gtes_system.discharge_inj_Nwell, gtes_system.depth, gtes_system.thickness,
        "Small", 1, 1.5, "Deviated", "Openhole"
    )
    discharge_well_cost_inj = discharge_drilling_cost_inj.WellCost()
    
    total_discharge_drilling_cost_inj = (
        0.0 if user_inputs.gtes_settings["reversible_wells"] 
        else discharge_drilling_cost_inj.TotalDC(discharge_well_cost_inj)
    )

    # Discharge Production Pumping
    p_flowrate_d = gtes_system.flowrate_per_well_prod * gtes_system.discharge_production.rho / 1000
    discharge_prod_pumping_estimation = ProductionPumpingCost(
        gtes_system.tinit, p_flowrate_d, gtes_system.discharge_prod_Nwell, 6370,
        gtes_system.depth, gtes_system.thickness, "Small", "Lineshaft", "Liner", 1.553
    )
    step3_d = discharge_prod_pumping_estimation.Sunctiondepth(
        discharge_prod_pumping_estimation.HeadSunction(discharge_prod_pumping_estimation.HeadProdTop().Prodtop)
    )
    step5_d = discharge_prod_pumping_estimation.Pumppower(
        step3_d, discharge_prod_pumping_estimation.CasingFriction(step3_d, discharge_prod_pumping_estimation.HeadProdTop().Prodtop)
    )
    step6_d = discharge_prod_pumping_estimation.Pumpcost(step5_d, step3_d)
    discharge_prod_pumping_cost_duty = discharge_prod_pumping_estimation.TotalPumpDutyCost(step5_d, step6_d)

    # Discharge Injection Pumping
    i_flowrate_d = gtes_system.flowrate_per_well_inj * gtes_system.discharge_injection.rho / 1000
    pressure_thermal_source_d = gtes_system.discharge_injection.p * 14.5038
    discharge_inj_pumping_estimation = InjectionPumpingCost(
        gtes_system.tinit, gtes_system.tinit, i_flowrate_d, p_flowrate_d, pressure_thermal_source_d,
        gtes_system.discharge_inj_Nwell, 7645, gtes_system.depth, gtes_system.thickness,
        "Small", "Openhole", 1.533, "Discharge"
    )
    step9_d = discharge_inj_pumping_estimation.Pumppower(
        discharge_inj_pumping_estimation.HeadInjection(discharge_inj_pumping_estimation.HeadSunction())
    )
    step10_d = discharge_inj_pumping_estimation.Pumpcost(step9_d)
    discharge_inj_pumping_cost_duty = (
        [0.0, 0.0] if user_inputs.gtes_settings["reversible_wells"] 
        else discharge_inj_pumping_estimation.TotalPumpDutyCost(step9_d, step10_d)
    )

    # Flow lines (Discharge)
    total_number_of_wells_d = gtes_system.discharge_prod_Nwell + gtes_system.discharge_inj_Nwell
    discharge_flowline_cost = (
        0.0 if user_inputs.gtes_settings["reversible_wells"] 
        else (initialization.FLOWLINE_LENGTH_M * initialization.M_TO_FT * initialization.PIPING_UNIT_COST_USD_FT * total_number_of_wells_d)
    )

    # Discharge Maintenance
    discharge_wellfield_maintenance = 0.015 * (
        total_discharge_drilling_cost_prod + total_discharge_drilling_cost_inj + discharge_flowline_cost
    )
    discharge_pump_maintenance = discharge_prod_pumping_estimation.PumpMaintenanceCost(step3_d, step6_d)
    discharge_makeup_water_subsurface = (
        initialization.MAKEUP_WATER_UNIT_COST * gtes_system.discharge_prod_Nwell * 
        (p_flowrate_d * 18.0917 * 34.2857 * 365) * 
        (initialization.OIL_SATURATION + initialization.SUBSURFACE_WATER_LOSS_BASE)
    )

    # Subsurface CapEx, Tax, and OpEx totals
    subsurface_capital_cost = (
        total_exploration_cost + field_dev_plant_permitting +
        total_charge_drilling_cost_prod + total_charge_drilling_cost_inj +
        total_discharge_drilling_cost_prod + total_discharge_drilling_cost_inj +
        charge_prod_pumping_cost_duty[1] + charge_inj_pumping_cost_duty[1] +
        discharge_prod_pumping_cost_duty[1] + discharge_inj_pumping_cost_duty[1] +
        charge_flowline_cost + discharge_flowline_cost
    )

    annual_tax_and_insurance = initialization.PROPERTY_TAX_RATE * subsurface_capital_cost

    subsurface_o_and_m_cost = (
        charge_wellfield_maintenance + charge_pump_maintenance + charge_makeup_water_subsurface +
        discharge_wellfield_maintenance + discharge_pump_maintenance + discharge_makeup_water_subsurface +
        annual_tax_and_insurance
    )

    # ==========================================
    # Financial levelization computations
    # ==========================================
    print("💰 Calculating plant-level LCOE and capacity metrics...")
    final_year_start = (nY - 1) * 8760
    final_year_end = nY * 8760
    final_year_power = gtes_system.power[final_year_start:final_year_end]

    charging_hours = int(np.sum(final_year_power > 0))
    discharging_hours = int(np.sum(final_year_power < 0))

    discharge_air_fan = discharging_hours * ltpc_system.fan0 * ltpc_system.Wout0 / 1e3

    # Power requirements
    if gtes_system.mode == "separate":
        Energy_charge_prod = charging_hours * charge_prod_pumping_cost_duty[0] / 1e6
        Energy_charge_inj = charging_hours * charge_inj_pumping_cost_duty[0] / 1e6
        Energy_discharge_prod = discharging_hours * discharge_prod_pumping_cost_duty[0] / 1e6
        Energy_discharge_inj = discharging_hours * discharge_inj_pumping_cost_duty[0] / 1e6
    elif gtes_system.mode == "continuous":
        Energy_charge_prod = charging_hours * discharge_prod_pumping_cost_duty[0] / 1e6
        Energy_charge_inj = charging_hours * discharge_inj_pumping_cost_duty[0] / 1e6
        Energy_discharge_prod = discharging_hours * discharge_prod_pumping_cost_duty[0] / 1e6
        Energy_discharge_inj = discharging_hours * discharge_inj_pumping_cost_duty[0] / 1e6

    geotes_max_hours = gtes_system.energy_capacity * 1000 / (ltpc_system.Wout0 / ltpc_system.eff0)
    geotes_max_elec = (
        (ltpc_system.Wout0 - discharge_prod_pumping_cost_duty[0]/1e3 - discharge_inj_pumping_cost_duty[0]/1e3 - ltpc_system.fan0 * ltpc_system.Wout0) 
        * geotes_max_hours / 1e3
    )
    geotes_capacity_hours = gtes_system.net_energy * 1000 / (ltpc_system.Wout0 / ltpc_system.eff0)
    geotes_capacity_elec = (
        (ltpc_system.Wout0 - discharge_prod_pumping_cost_duty[0]/1e3 - discharge_inj_pumping_cost_duty[0]/1e3 - ltpc_system.fan0 * ltpc_system.Wout0) 
        * geotes_capacity_hours / 1e3
    )

    # 1. Levelized Cost of Heat (LCOH)
    try:
        econ_system.surface_capital_cost = (
            csp_system.total_cost + ltpc_system.total_cost + (250 * qload * 1000) - 
            user_inputs.lcoh_csp_offset
        )
        econ_system.OnM_surface = (
            econ_system.OnM * (csp_system.total_cost + ltpc_system.total_cost + 250 * qload * 1000) - 
            user_inputs.lcoh_om_offset
        )
        econ_system.subsurface_capital_cost = subsurface_capital_cost - user_inputs.lcoh_sub_cap_offset
        econ_system.OnM_subsurface = subsurface_o_and_m_cost - user_inputs.lcoh_sub_om_offset
        econ_system.Ein = (
            Energy_charge_prod + Energy_charge_inj + Energy_discharge_prod + Energy_discharge_inj - 
            user_inputs.lcoh_ein_offset
        )
        econ_system.Qout = np.sum(qload_hourly[final_year_start:final_year_end]) / 1e3
        
        econ_system = econ_system.calc_fcr()
        econ_system = econ_system.calc_levelized_cost("H")
    except NameError:
        print("ℹ️ LCOH calculations skipped: 'qload' and 'qload_hourly' not defined in scope.")

    # 2. Levelized Cost of Electricity (LCOE)
    econ_system.subsurface_capital_cost = subsurface_capital_cost
    econ_system.OnM_subsurface = subsurface_o_and_m_cost
    econ_system.surface_capital_cost = csp_system.total_cost + ltpc_system.total_cost
    econ_system.OnM_surface = econ_system.OnM * econ_system.surface_capital_cost
    
    econ_system.Ein = Energy_charge_prod + Energy_charge_inj
    econ_system.Eout = ltpc_system.Wout_tot - (Energy_discharge_prod + Energy_discharge_inj) - discharge_air_fan

    econ_system = econ_system.calc_fcr()
    econ_system = econ_system.calc_levelized_cost("E")

    # Group Capital arrays (M$)
    ccap = np.array([
        total_exploration_cost,
        field_dev_plant_permitting,
        total_charge_drilling_cost_inj + total_charge_drilling_cost_prod,
        charge_prod_pumping_cost_duty[1],
        charge_inj_pumping_cost_duty[1],
        charge_flowline_cost,
        total_discharge_drilling_cost_prod + total_discharge_drilling_cost_inj,
        discharge_prod_pumping_cost_duty[1],
        discharge_inj_pumping_cost_duty[1],
        discharge_flowline_cost,
        csp_system.total_cost,
        ltpc_system.total_cost
    ]) / 1e6

    lcoe_mat = (ccap * econ_system.FCR * 1e6 + econ_system.OnM_subsurface + econ_system.OnM_surface) / econ_system.Eout / 1e6

    geotes_ccap_sum = np.sum(ccap[0:10])
    geotes_lcoe = (
        (geotes_ccap_sum * econ_system.FCR * 1e6 + econ_system.OnM_subsurface) / 
        (econ_system.Eout * gtes_system.energy_out_tot / ltpc_system.Qin_tot) / 1e6
    )
    geotes_lcoe_itc = (
        (geotes_ccap_sum * econ_system.FCR * 1e6 * (1 - econ_system.itc) + econ_system.OnM_subsurface) / 
        (econ_system.Eout * gtes_system.energy_out_tot / ltpc_system.Qin_tot) / 1e6
    )

    # Net electrical and Capacity Factor (%)
    net_elec = ltpc_system.Wout_tot - (Energy_discharge_prod + Energy_discharge_inj) - discharge_air_fan
    cap_fac = (
        100 * 1000 * net_elec / 
        (ltpc_system.Wout0 - discharge_prod_pumping_cost_duty[0]/1e3 - discharge_inj_pumping_cost_duty[0]/1e3 - ltpc_system.fan0 * ltpc_system.Wout0) / 
        8760
    )

    # Display Simulation Outputs
    print("\n" + "="*50)
    print("📊 FINAL SIMULATION METRICS")
    print("="*50)
    print(f"💰 Subsurface CapEx:              ${subsurface_capital_cost:,.2f}")
    print(f"🔧 Annual Subsurface OpEx:        ${subsurface_o_and_m_cost:,.2f}")
    print(f"💡 Net Electricity Generation:    {net_elec:,.2f} MWh/year")
    print(f"⚙️ Plant Capacity Factor:         {cap_fac:.2f}%")
    print(f"⚡ GeoTES LCOE (Base):            ${geotes_lcoe:.4f}/kWh")
    print(f"🎁 GeoTES LCOE (with 40% ITC):   ${geotes_lcoe_itc:.4f}/kWh")
    print("="*50 + "\n")

    
    # When saving output data/plots, write them directly to your output directory:
    # plot_path = config.OUTPUT_DIR / "solar_production_profile.png"
    # plt.savefig(plot_path)





if __name__ == "__main__":
    main()
