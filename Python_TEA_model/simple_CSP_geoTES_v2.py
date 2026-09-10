import datetime
import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

project_root = Path(__file__).resolve().parent
subsurface_module_path = project_root / "Subsurface TEA Model"
if subsurface_module_path.exists():
    sys.path.insert(0, str(subsurface_module_path))

from economics_class import economics_class
from geoTES_class import geoTES_class
from SAM.call_SAM import call_SAM
from thermo_cycle_class import thermo_cycle_class
from solar_class import solar_class
from DrillingCostUpdated import DrillingCostUpdated
from ExplorationCost import ExplorationCost
from InjectionPumpingCost import InjectionPumpingCost
from ProductionPumpingCost import ProductionPumpingCost


def ensure_output_folder(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    else:
        for file in path.iterdir():
            if file.is_file():
                file.unlink()


def build_operating_hours() -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], list[int], list[int], list[int]]:
    phase1 = (0, (31 + 28 + 31) * 24)
    phase2 = (phase1[1], (31 + 28 + 31 + 30 + 31 + 30 + 31 + 31 + 30) * 24)
    phase3 = (phase2[1], (31 + 28 + 31 + 30 + 31 + 30 + 31 + 31 + 30 + 31 + 30 + 31) * 24)

    op_hours = list(range(6, 9)) + list(range(18, 22))
    return phase1, phase2, phase3, op_hours, op_hours, op_hours


def day_of_year(year: int, month: int, day: int) -> int:
    return datetime.date(year, month, day).timetuple().tm_yday


def year_slice(nY: int) -> slice:
    hours = 8760
    return slice((nY - 1) * hours, nY * hours)


def save_figure(fig, path: Path, formats: list[str]) -> None:
    for fmt in formats:
        fig.savefig(path.with_suffix(f".{fmt}"), bbox_inches="tight")


def main() -> None:
    save_figs = False
    output_dir = Path("Outputs")
    ensure_output_folder(output_dir)

    location = "Imperial CA"
    nY = 2
    dT = 1.0

    phase1, phase2, phase3, op_hour1, op_hour2, op_hour3 = build_operating_hours()

    mirror_type = "Parabolic trough"
    nominal_DNI = 1000.0
    solar_multiple = 2.9
    initial_size = 100.0
    CSP_Tmax = 565.0
    CSP_Tmin = 300.0
    CSP_land_mult = 1.1

    CSP_cost = {
        "mirror": 150.0,
        "land": 20.0,
        "HX": 250.0,
    }

    CSP = solar_class(
        location,
        mirror_type,
        nominal_DNI,
        solar_multiple,
        initial_size,
        CSP_Tmax,
        CSP_Tmin,
        CSP_land_mult,
        CSP_cost,
        nY,
    )

    LTPC_type = "HE"
    LTPC_design = {
        "Wout": 100.0,
        "T0": 15.0,
        "TIT": 200.0,
        "fan": 0.1,
    }
    LTPC_foff = project_root / "data" / "example_off_design.xlsx"
    LTPC_cost = {"power_block": 1000.0, "HX": 250.0}
    LTPC = thermo_cycle_class(LTPC_type, LTPC_design, str(LTPC_foff), LTPC_cost, nY)

    reversible_wells = False
    gTES_recovery = 0.95
    gTES_Tinit = 50.0
    gTES_flowrate = {"P": 60.0, "I": 60.0}
    gTES_Qmax = 10000.0
    gTES_props = {
        "rho": 2000.0,
        "cp": 800.0,
        "void": 0.32,
        "depth": 500.0,
        "thickness": 200.0,
    }
    gTES_fluid = "water"
    gTES_mode = "continuous"

    gTES = geoTES_class(
        gTES_recovery,
        gTES_Tinit,
        gTES_flowrate["P"],
        gTES_Qmax,
        gTES_props,
        gTES_fluid,
        nY,
    )
    gTES.mode = gTES_mode
    gTES.flowrate_per_well_prod = gTES_flowrate["P"]
    gTES.flowrate_per_well_inj = gTES_flowrate["I"]
    gTES.depth = gTES_props["depth"]
    gTES.thickness = gTES_props["thickness"]

    finance = {
        "lifetime": 30,
        "elec_price": 0.05,
        "inflation": 0.025,
        "irr": 0.10,
        "debt_frac": 0.60,
        "debt_IR": 0.08,
        "tax_rate": 0.28,
        "deprec": [0.20, 0.32, 0.20, 0.14, 0.14],
        "annual_cost": [1.0, 0.0, 0.0],
        "construc_IR": 0.0,
        "OnM": 0.02,
        "ITC": 0.3,
    }
    econ = economics_class(finance)

    gTES.charge_production.T = gTES.Tinit
    gTES.charge_production.p = 20.0
    gTES.charge_production.calc_fluid_props("pT")

    gTES.charge_injection.T = LTPC.Tmax
    gTES.charge_injection.q = 0.0
    gTES.charge_injection.p = 20.0
    gTES.charge_injection.calc_fluid_props("pT")

    gTES.discharge_production.T = LTPC.Tmax
    gTES.discharge_production.q = 0.0
    gTES.discharge_production.calc_fluid_props("qT")

    gTES.discharge_injection.T = gTES.Tinit
    gTES.discharge_injection.p = 20.0
    gTES.discharge_injection.calc_fluid_props("pT")

    out = call_SAM(CSP, LTPC)
    CSP.mirror_aperture = out.mirror_area
    CSP.land_area = out.land_area
    CSP.nominal_eff = out.nominal_eff
    CSP.annual_eff = out.annual_eff
    CSP.DNI = out.DNI

    n_hours = nY * 8760
    out_power = np.asarray(out.field_thermal_power, dtype=float).ravel()
    CSP.power = np.tile(out_power, nY)
    CSP.power = np.maximum(CSP.power, 0.0)

    LTPC.Tamb = np.tile(np.asarray(out.Tamb, dtype=float).ravel(), nY)

    LTPC.Qin[0] = CSP.power[0]
    LTPC.interpolate_off_design(0)

    hour = 2
    houry = 2
    for i in range(1, n_hours):
        gTES.energy[i] = gTES.energy[i - 1]

        if phase1[0] <= houry < phase1[1]:
            operate = hour in op_hour1
        elif phase2[0] <= houry < phase2[1]:
            operate = hour in op_hour2
        else:
            operate = hour in op_hour3

        if operate:
            if CSP.power[i] > LTPC.Qin0:
                LTPC.Qin[i] = LTPC.Qin0
                LTPC.interpolate_off_design(i)

                dP = CSP.power[i] - LTPC.Qin0
                if dP < gTES.Qmax:
                    gTES.power[i] = dP
                else:
                    gTES.power[i] = gTES.Qmax
                    CSP.dumped[i] = dP - gTES.Qmax
                gTES.energy[i] = gTES.energy[i - 1] + gTES.power[i] * dT * gTES.recovery
            else:
                dP = LTPC.Qin0 - CSP.power[i]
                if dP * dT < gTES.energy[i - 1]:
                    gTES.power[i] = -dP
                    gTES.energy[i] = gTES.energy[i - 1] + gTES.power[i]
                    LTPC.Qin[i] = LTPC.Qin0
                    LTPC.interpolate_off_design(i)
                else:
                    gTES.power[i] = -gTES.energy[i - 1] / dT
                    gTES.energy[i] = gTES.energy[i - 1] + gTES.power[i]
                    LTPC.Qin[i] = CSP.power[i] - gTES.power[i]
                    LTPC.interpolate_off_design(i)
        else:
            dP = CSP.power[i]
            if dP < gTES.Qmax:
                gTES.power[i] = dP
            else:
                gTES.power[i] = gTES.Qmax
                CSP.dumped[i] = dP - gTES.Qmax
            gTES.energy[i] = gTES.energy[i - 1] + gTES.power[i] * dT * gTES.recovery

        hour += 1
        houry += 1
        if hour == 25:
            hour = 1
        if houry == 8761:
            houry = 1

    gTES.geoTES_size()
    gTES.geoTES_well_flows()

    CSP.CSP_annual_energy()
    LTPC.PC_annual_energy()
    gTES.geoTES_annual_energy()

    CSP.calc_CSP_cost(LTPC)
    LTPC.calc_PC_cost()

    Exploration_Cost = ExplorationCost("Greenfield", 3, 20000, 1.2)
    Total_Exploration_Cost = ExplorationCost.exploration_cost_calc(Exploration_Cost)

    PPImultiplier = 1.175
    FieldDevPlantPermitting = 1_000_000.0 * PPImultiplier

    if gTES.mode == "separate":
        Charge_Drilling_Cost_prod = DrillingCostUpdated(
            gTES.charge_prod_Nwell,
            0,
            gTES.depth,
            gTES.thickness,
            "Small",
            1,
            1.5,
            "Deviated",
            "Liner",
        )
        Charge_Well_Cost_prod = Charge_Drilling_Cost_prod.WellCost()
        Total_Charge_Drilling_Cost_prod = Charge_Drilling_Cost_prod.TotalDC(Charge_Well_Cost_prod)

        Charge_Drilling_Cost_inj = DrillingCostUpdated(
            0,
            gTES.charge_inj_Nwell,
            gTES.depth,
            gTES.thickness,
            "Small",
            1,
            1.5,
            "Deviated",
            "Openhole",
        )
        Charge_Well_Cost_inj = Charge_Drilling_Cost_inj.WellCost()
        Total_Charge_Drilling_Cost_inj = Charge_Drilling_Cost_inj.TotalDC(Charge_Well_Cost_inj)

        ResTemp = gTES.Tinit
        Pflowrate = gTES.flowrate_per_well_prod * gTES.charge_production.rho / 1000.0
        Charge_ProdPumping_Estimation = ProductionPumpingCost(
            ResTemp,
            Pflowrate,
            gTES.charge_prod_Nwell,
            6370,
            gTES.depth,
            gTES.thickness,
            "Small",
            "Lineshaft",
            "Liner",
            1.553,
        )
        Step1 = Charge_ProdPumping_Estimation.head_prod_top()
        Step2 = Charge_ProdPumping_Estimation.head_suction(Step1)
        Step3 = Charge_ProdPumping_Estimation.suction_depth(Step2)
        Step4 = Charge_ProdPumping_Estimation.casing_friction(Step3, Step1)
        Step5 = Charge_ProdPumping_Estimation.pump_power(Step3, Step4)
        Step6 = Charge_ProdPumping_Estimation.pump_cost(Step5, Step3)
        Charge_ProdPumping_Cost_Duty = Charge_ProdPumping_Estimation.total_pump_duty_cost(Step5, Step6)

        InjTemp = LTPC.Tmax
        Iflowrate = gTES.flowrate_per_well_inj * gTES.charge_injection.rho / 1000.0
        PressureThermalSource = gTES.charge_injection.p * 14.5038
        Charge_InjPumping_Estimation = InjectionPumpingCost(
            ResTemp,
            InjTemp,
            Iflowrate,
            Pflowrate,
            PressureThermalSource,
            gTES.charge_inj_Nwell,
            7645,
            gTES.depth,
            gTES.thickness,
            "Small",
            "Openhole",
            1.533,
            "Charge",
        )
        Step7 = Charge_InjPumping_Estimation.head_suction()
        Step8 = Charge_InjPumping_Estimation.head_injection(Step7)
        Step9 = Charge_InjPumping_Estimation.pump_power(Step8)
        Step10 = Charge_InjPumping_Estimation.pump_cost(Step9)
        Charge_InjPumping_Cost_Duty = Charge_InjPumping_Estimation.total_pump_duty_cost(Step9, Step10)

        Charge_FlowLineCost = (
            300.0 * 3.28084 * 256.98 * (gTES.charge_prod_Nwell + gTES.charge_inj_Nwell)
        )
        Charge_WellFieldMaintenance = 0.015 * (
            Total_Charge_Drilling_Cost_prod
            + Total_Charge_Drilling_Cost_inj
            + Charge_FlowLineCost
        )
        Charge_PumpMaintenance = Charge_ProdPumping_Estimation.pump_maintenance_cost(Step3, Step6)

        OilSaturation = 0.0
        NumberProductionWells = gTES.charge_prod_Nwell
        ProductionRateperWell = Pflowrate
        MakeupWaterUnitCost = 0.65
        SubsurfaceWaterLoss = OilSaturation + 0.001
        Charge_MakeupWaterSubsurface = (
            MakeupWaterUnitCost
            * NumberProductionWells
            * (ProductionRateperWell * 18.0917 * 34.2857 * 365.0)
            * SubsurfaceWaterLoss
        )
    else:
        Total_Charge_Drilling_Cost_prod = 0.0
        Total_Charge_Drilling_Cost_inj = 0.0
        Charge_ProdPumping_Cost_Duty = np.array([0.0, 0.0])
        Charge_InjPumping_Cost_Duty = np.array([0.0, 0.0])
        Charge_FlowLineCost = 0.0
        Charge_WellFieldMaintenance = 0.0
        Charge_PumpMaintenance = 0.0
        Charge_MakeupWaterSubsurface = 0.0

    Discharge_Drilling_Cost_prod = DrillingCostUpdated(
        gTES.discharge_prod_Nwell,
        0,
        gTES.depth,
        gTES.thickness,
        "Small",
        1,
        1.5,
        "Deviated",
        "Liner",
    )
    Discharge_Well_Cost_prod = Discharge_Drilling_Cost_prod.WellCost()
    if reversible_wells:
        Total_Discharge_Drilling_Cost_prod = 0.0
    else:
        Total_Discharge_Drilling_Cost_prod = Discharge_Drilling_Cost_prod.TotalDC(Discharge_Well_Cost_prod)

    Discharge_Drilling_Cost_inj = DrillingCostUpdated(
        0,
        gTES.discharge_inj_Nwell,
        gTES.depth,
        gTES.thickness,
        "Small",
        1,
        1.5,
        "Deviated",
        "Openhole",
    )
    Discharge_Well_Cost_inj = Discharge_Drilling_Cost_inj.WellCost()
    if reversible_wells:
        Total_Discharge_Drilling_Cost_inj = 0.0
    else:
        Total_Discharge_Drilling_Cost_inj = Discharge_Drilling_Cost_inj.TotalDC(Discharge_Well_Cost_inj)

    ResTemp = gTES.Tinit
    Pflowrate = gTES.flowrate_per_well_prod * gTES.discharge_production.rho / 1000.0
    Discharge_ProdPumping_Estimation = ProductionPumpingCost(
        ResTemp,
        Pflowrate,
        gTES.discharge_prod_Nwell,
        6370,
        gTES.depth,
        gTES.thickness,
        "Small",
        "Lineshaft",
        "Liner",
        1.553,
    )
    Step1 = Discharge_ProdPumping_Estimation.head_prod_top()
    Step2 = Discharge_ProdPumping_Estimation.head_suction(Step1)
    Step3 = Discharge_ProdPumping_Estimation.suction_depth(Step2)
    Step4 = Discharge_ProdPumping_Estimation.casing_friction(Step3, Step1)
    Step5 = Discharge_ProdPumping_Estimation.pump_power(Step3, Step4)
    Step6 = Discharge_ProdPumping_Estimation.pump_cost(Step5, Step3)
    Discharge_ProdPumping_Cost_Duty = Discharge_ProdPumping_Estimation.total_pump_duty_cost(Step5, Step6)

    InjTemp = gTES.Tinit
    Iflowrate = gTES.flowrate_per_well_inj * gTES.discharge_injection.rho / 1000.0
    PressureThermalSource = gTES.discharge_injection.p * 14.5038
    Discharge_InjPumping_Estimation = InjectionPumpingCost(
        ResTemp,
        InjTemp,
        Iflowrate,
        Pflowrate,
        PressureThermalSource,
        gTES.discharge_inj_Nwell,
        7645,
        gTES.depth,
        gTES.thickness,
        "Small",
        "Openhole",
        1.533,
        "Discharge",
    )
    Step7 = Discharge_InjPumping_Estimation.head_suction()
    Step8 = Discharge_InjPumping_Estimation.head_injection(Step7)
    Step9 = Discharge_InjPumping_Estimation.pump_power(Step8)
    Step10 = Discharge_InjPumping_Estimation.pump_cost(Step9)
    Discharge_InjPumping_Cost_Duty = Discharge_InjPumping_Estimation.total_pump_duty_cost(Step9, Step10)
    if reversible_wells:
        Discharge_InjPumping_Cost_Duty = np.array([0.0, 0.0])

    Discharge_FlowLineCost = (
        300.0 * 3.28084 * 256.98 * (gTES.discharge_prod_Nwell + gTES.discharge_inj_Nwell)
    )
    if reversible_wells:
        Discharge_FlowLineCost = 0.0

    Discharge_WellFieldMaintenance = 0.015 * (
        Total_Discharge_Drilling_Cost_prod
        + Total_Discharge_Drilling_Cost_inj
        + Discharge_FlowLineCost
    )
    Discharge_PumpMaintenance = Discharge_ProdPumping_Estimation.pump_maintenance_cost(Step3, Step6)

    OilSaturation = 0.0
    NumberProductionWells = gTES.discharge_prod_Nwell
    ProductionRateperWell = Pflowrate
    MakeupWaterUnitCost = 0.65
    SubsurfaceWaterLoss = OilSaturation + 0.001
    Discharge_MakeupWaterSubsurface = (
        MakeupWaterUnitCost
        * NumberProductionWells
        * (ProductionRateperWell * 18.0917 * 34.2857 * 365.0)
        * SubsurfaceWaterLoss
    )

    SubsurfaceCapitalCost = (
        Total_Exploration_Cost
        + FieldDevPlantPermitting
        + Total_Charge_Drilling_Cost_prod
        + Total_Charge_Drilling_Cost_inj
        + Total_Discharge_Drilling_Cost_prod
        + Total_Discharge_Drilling_Cost_inj
        + Charge_ProdPumping_Cost_Duty[1]
        + Charge_InjPumping_Cost_Duty[1]
        + Discharge_ProdPumping_Cost_Duty[1]
        + Discharge_InjPumping_Cost_Duty[1]
        + Charge_FlowLineCost
        + Discharge_FlowLineCost
    )

    PropertyTaxRate = 0.0075
    AnnualTaxandInsurance = PropertyTaxRate * SubsurfaceCapitalCost

    SubsurfaceOandMCost = (
        Charge_WellFieldMaintenance
        + Charge_PumpMaintenance
        + Charge_MakeupWaterSubsurface
        + Discharge_WellFieldMaintenance
        + Discharge_PumpMaintenance
        + Discharge_MakeupWaterSubsurface
        + AnnualTaxandInsurance
    )

    econ.subsurface_capital_cost = SubsurfaceCapitalCost
    econ.OnM_subsurface = SubsurfaceOandMCost

    last_year = year_slice(nY)
    charging_hours = int(np.count_nonzero(gTES.power[last_year] > 0.0))
    discharging_hours = int(np.count_nonzero(gTES.power[last_year] < 0.0))

    discharge_air_fan = discharging_hours * LTPC.fan0 * LTPC.Wout0 / 1e3

    if gTES.mode == "separate":
        Energy_charge_prod = charging_hours * Charge_ProdPumping_Cost_Duty[0] / 1e6
        Energy_charge_inj = charging_hours * Charge_InjPumping_Cost_Duty[0] / 1e6
        Energy_discharge_prod = discharging_hours * Discharge_ProdPumping_Cost_Duty[0] / 1e6
        Energy_discharge_inj = discharging_hours * Discharge_InjPumping_Cost_Duty[0] / 1e6
    else:
        Energy_charge_prod = charging_hours * Discharge_ProdPumping_Cost_Duty[0] / 1e6
        Energy_charge_inj = charging_hours * Discharge_InjPumping_Cost_Duty[0] / 1e6
        Energy_discharge_prod = discharging_hours * Discharge_ProdPumping_Cost_Duty[0] / 1e6
        Energy_discharge_inj = discharging_hours * Discharge_InjPumping_Cost_Duty[0] / 1e6

    geoTES_max_hours = gTES.energy_capacity * 1000.0 / (LTPC.Wout0 / LTPC.eff0)
    geoTES_max_elec = (
        LTPC.Wout0
        - Discharge_ProdPumping_Cost_Duty[0] / 1e3
        - Discharge_InjPumping_Cost_Duty[0] / 1e3
        - LTPC.fan0 * LTPC.Wout0
    ) * geoTES_max_hours / 1e3

    geoTES_capacity_hours = gTES.net_energy * 1000.0 / (LTPC.Wout0 / LTPC.eff0)
    geoTES_capacity_elec = (
        LTPC.Wout0
        - Discharge_ProdPumping_Cost_Duty[0] / 1e3
        - Discharge_InjPumping_Cost_Duty[0] / 1e3
        - LTPC.fan0 * LTPC.Wout0
    ) * geoTES_capacity_hours / 1e3

    econ.surface_capital_cost = CSP.total_cost
    econ.OnM_surface = econ.OnM * econ.surface_capital_cost
    econ.Ein = Energy_charge_prod + Energy_charge_inj + Energy_discharge_prod + Energy_discharge_inj
    econ.Qout = LTPC.Qin_tot
    econ.calc_fcr()
    econ.calc_levelized_cost("H")

    econ.surface_capital_cost = CSP.total_cost + LTPC.total_cost
    econ.OnM_surface = econ.OnM * econ.surface_capital_cost
    econ.Ein = Energy_charge_prod + Energy_charge_inj
    econ.Eout = LTPC.Wout_tot - (Energy_discharge_prod + Energy_discharge_inj) - discharge_air_fan
    econ.calc_fcr()
    econ.calc_levelized_cost("E")

    Ccap = np.array(
        [
            Total_Exploration_Cost,
            FieldDevPlantPermitting,
            Total_Charge_Drilling_Cost_inj + Total_Charge_Drilling_Cost_prod,
            Charge_ProdPumping_Cost_Duty[1],
            Charge_InjPumping_Cost_Duty[1],
            Charge_FlowLineCost,
            Total_Discharge_Drilling_Cost_prod + Total_Discharge_Drilling_Cost_inj,
            Discharge_ProdPumping_Cost_Duty[1],
            Discharge_InjPumping_Cost_Duty[1],
            Discharge_FlowLineCost,
            CSP.total_cost,
            LTPC.total_cost,
        ],
        dtype=float,
    )
    Ccap = Ccap / 1e6
    LCOE_mat = np.concatenate((Ccap * econ.FCR * 1e6, [econ.OnM_subsurface, econ.OnM_surface])) / econ.Eout / 1e6
    geoTES_LCOE = (
        np.sum(Ccap[:10]) * econ.FCR * 1e6 + econ.OnM_subsurface
    ) / (econ.Eout * gTES.energy_out_tot / LTPC.Qin_tot) / 1e6
    geoTES_LCOE_ITC = (
        np.sum(Ccap[:10]) * econ.FCR * 1e6 * (1.0 - econ.ITC) + econ.OnM_subsurface
    ) / (econ.Eout * gTES.energy_out_tot / LTPC.Qin_tot) / 1e6

    net_elec = LTPC.Wout_tot - (Energy_discharge_prod + Energy_discharge_inj) - discharge_air_fan
    cap_fac = 100.0 * 1000.0 * net_elec / (
        LTPC.Wout0
        - Discharge_ProdPumping_Cost_Duty[0] / 1e3
        - Discharge_InjPumping_Cost_Duty[0] / 1e3
        - LTPC.fan0 * LTPC.Wout0
    ) / 8760.0

    print("\nPOWER OUTPUTS\n")
    print(f"Maximum solar power generated             = {np.max(CSP.power):6.2f} MW-th")
    print(f"Power cycle power output                  = {LTPC.Wout0:6.2f} MW-e")
    positive_wout = LTPC.Wout[last_year][LTPC.Wout[last_year] > 0.0]
    print(f"Average power cycle output                = {np.mean(positive_wout) if positive_wout.size else 0.0:6.2f} MW-e")
    print(f"Max. thermal power into subsurface        = {np.max(gTES.power[last_year]):6.2f} MW-th")
    print(f"Max. thermal power out of subsurface      = {-np.min(gTES.power[last_year]):6.2f} MW-th")
    print(f"Charge production pump power              = {Charge_ProdPumping_Cost_Duty[0] / 1e3:6.2f} MW-e")
    print(f"Charge injection pump power               = {Charge_InjPumping_Cost_Duty[0] / 1e3:6.2f} MW-e")
    print(f"Discharge production pump power           = {Discharge_ProdPumping_Cost_Duty[0] / 1e3:6.2f} MW-e")
    print(f"Discharge injection pump power            = {Discharge_InjPumping_Cost_Duty[0] / 1e3:6.2f} MW-e")

    print("\nANNUAL ENERGY OUTPUTS\n")
    print(f"Available solar heat                      = {CSP.available_solar_heat:6.2f} GWh-th")
    print(f"Solar heat generated                      = {CSP.solar_thermal_generated:6.2f} GWh-th")
    print(f"Dumped solar heat                         = {CSP.total_dumped:6.2f} GWh-th\n")
    print(f"Heat delivered to low-temp. cycle         = {LTPC.Qin_tot:6.2f} GWh-th")
    print(f"Electricity generated by low-temp. cycle  = {LTPC.Wout_tot:6.2f} GWh-e")
    print(f"Discharge condenser fan parasitic         = {discharge_air_fan:6.2f} GWh-e\n")
    print(f"Heat delivered to geoTES                  = {gTES.energy_in_tot:6.2f} GWh-th")
    print(f"Heat extracted from geoTES                = {gTES.energy_out_tot:6.2f} GWh-th")
    print(f"Max. energy stored in geoTES              = {gTES.energy_capacity:6.2f} GWh-th")
    print(f"Max. hours of power delivery              = {geoTES_max_hours:6.2f} h")
    print(f"Approx. electricity from max. hours       = {geoTES_max_elec:6.2f} GWh-e\n")
    print(f"Net annual change in geoTES capacity      = {gTES.net_energy:6.2f} GWh-th")
    print(f"Equivalent hours of power delivery        = {geoTES_capacity_hours:6.2f} h")
    print(f"Approx. electricity from space capacity   = {geoTES_capacity_elec:6.2f} GWh-e\n")
    print(f"Charge production pump consumption        = {charging_hours * Charge_ProdPumping_Cost_Duty[0] / 1e6:6.2f} GWh-e")
    print(f"Charge injection pump consumption         = {charging_hours * Charge_InjPumping_Cost_Duty[0] / 1e6:6.2f} GWh-e")
    print(f"Discharge production pump consumption     = {discharging_hours * Discharge_ProdPumping_Cost_Duty[0] / 1e6:6.2f} GWh-e")
    print(f"Discharge injection pump consumption      = {discharging_hours * Discharge_InjPumping_Cost_Duty[0] / 1e6:6.2f} GWh-e\n")
    print(f"Net electricity generated                 = {net_elec:6.2f} GWh-e")
    print(f"Capacity factor                           = {cap_fac:6.2f} %\n")
    print(f"Number of charging production wells       = {gTES.charge_prod_Nwell:6.2f}")
    print(f"Number of charging injection wells        = {gTES.charge_inj_Nwell:6.2f}")
    print(f"Number of discharging production wells    = {gTES.discharge_prod_Nwell:6.2f}")
    print(f"Number of discharging injection wells     = {gTES.discharge_inj_Nwell:6.2f}\n")

    print("\nSUBSURFACE COST RESULTS\n")
    print(f"Total Exploration Cost          = {Total_Exploration_Cost/1e6:6.2f} M$")
    print(f"Permitting cost                 = {FieldDevPlantPermitting/1e6:6.2f} M$\n")
    print(f"Total Charge Drilling Cost      = {(Total_Charge_Drilling_Cost_prod + Total_Charge_Drilling_Cost_inj)/1e6:6.2f} M$")
    print(f"Charge production pump cost     = {Charge_ProdPumping_Cost_Duty[1]/1e6:6.2f} M$")
    print(f"Charge injection pump cost      = {Charge_InjPumping_Cost_Duty[1]/1e6:6.2f} M$")
    print(f"Charge flow line cost           = {Charge_FlowLineCost/1e6:6.2f} M$\n")
    print(f"Total Discharge Drilling Cost   = {(Total_Discharge_Drilling_Cost_prod + Total_Discharge_Drilling_Cost_inj)/1e6:6.2f} M$")
    print(f"Discharge production pump cost  = {Discharge_ProdPumping_Cost_Duty[1]/1e6:6.2f} M$")
    print(f"Discharge injection pump cost   = {Discharge_InjPumping_Cost_Duty[1]/1e6:6.2f} M$")
    print(f"Discharge flow line cost        = {Discharge_FlowLineCost/1e6:6.2f} M$\n")
    print(f"Subsurface Capital Cost         = {SubsurfaceCapitalCost/1e6:6.2f} M$")
    print(f"Subsurface O&M Cost             = {SubsurfaceOandMCost/1e6:6.2f} M$")
    print(f"Capital cost of storage         = {econ.subsurface_capital_cost/(gTES.energy_capacity*1e6):6.2f} $/kWh-th\n")

    print("SURFACE COST RESULTS\n")
    print(f"Solar field cost                = {CSP.total_cost/1e6:6.2f} M$")
    print(f"Low-temp. power cycle cost      = {LTPC.total_cost/1e6:6.2f} M$\n")
    print(f"Surface capital cost            = {econ.surface_capital_cost/1e6:6.2f} M$")
    print(f"Surface O&M cost                = {econ.OnM_surface/1e6:6.2f} M$\n")

    print("TOTAL COST RESULTS\n")
    print(f"Total capital cost              = {econ.total_capital_cost/1e6:6.2f} M$")
    print(f"LCOE                            = {econ.LCOE:6.3f} $/kWh-e")
    print(f"LCOH                            = {econ.LCOH:6.3f} $/kWh-th")
    print(f"GeoTES contribution to LCOE     = {geoTES_LCOE:6.3f} $/kWh-e\n")
    print(f"Cost results including an investment tax credit of {100.0 * econ.ITC:4.2f}%")
    print(f"Total capital cost (ITC)        = {econ.total_capital_cost_ITC/1e6:6.2f} M$")
    print(f"LCOE (ITC)                      = {econ.LCOE_ITC:6.3f} $/kWh-e")
    print(f"LCOH (ITC)                      = {econ.LCOH_ITC:6.3f} $/kWh-th")
    print(f"GeoTES contribution to LCOE (ITC) = {geoTES_LCOE_ITC:6.3f} $/kWh-e\n")

    formats = ["png", "svg"]

    fig = plt.figure(1)
    plt.bar(np.arange(1, len(Ccap) + 1), Ccap)
    plt.xticks(
        np.arange(1, len(Ccap) + 1),
        [
            "Exploration",
            "Permitting",
            "Charge drilling",
            "Charge production pumps",
            "Charge injection pump",
            "Charge flow line",
            "Discharge drilling",
            "Discharge production pumps",
            "Discharge injection pump",
            "Discharge flow line",
            "CSP",
            "Low-temp power cycle",
        ],
        rotation=45,
        ha="right",
    )
    plt.ylabel("Capital cost, M$")
    plt.tight_layout()
    if save_figs:
        save_figure(fig, output_dir / "capital_cost", formats)

    fig = plt.figure(2)
    plt.bar(np.arange(1, len(LCOE_mat) + 1), LCOE_mat)
    plt.xticks(
        np.arange(1, len(LCOE_mat) + 1),
        [
            "Exploration",
            "Permitting",
            "Charge drilling",
            "Charge production pumps",
            "Charge injection pump",
            "Charge flow line",
            "Discharge drilling",
            "Discharge production pumps",
            "Discharge injection pump",
            "Discharge flow line",
            "CSP",
            "Low-temp power cycle",
            "Subsurface O&M",
            "Surface O&M",
        ],
        rotation=45,
        ha="right",
    )
    plt.ylabel("LCOE, $/kWh-e")
    plt.tight_layout()
    if save_figs:
        save_figure(fig, output_dir / "LCOE", formats)

    fig = plt.figure(3)
    current_year = year_slice(nY)
    hours = np.arange(current_year.start, current_year.stop)
    plt.plot(hours, gTES.energy[current_year] / 1000.0)
    plt.xlim([0, 8760])
    plt.gca().set_aspect(3.0, adjustable="box")
    plt.xlabel("Hour of the year")
    plt.ylabel("Energy in geoTES, GWh-th")
    plt.tight_layout()
    if save_figs:
        save_figure(fig, output_dir / "geoTES_SOC", formats)

    def doy_slice(start_month: int, start_day: int, end_month: int, end_day: int) -> slice:
        start = 24 * (day_of_year(2022, start_month, start_day) - 1)
        end = 24 * day_of_year(2022, end_month, end_day)
        return slice(start, end)

    fig = plt.figure(4)
    n = doy_slice(1, 27, 1, 31)
    plt.plot(CSP.power[n], label="Solar heat")
    plt.plot(gTES.power[n], label="Heat to geoTES")
    plt.plot(LTPC.Qin[n], label="Heat to LT power cycle")
    plt.gca().set_aspect(3.0, adjustable="box")
    plt.title("January 27")
    plt.xlabel("Hour")
    plt.ylabel("Heat, MWh-th")
    plt.legend(loc="lower center", bbox_to_anchor=(0.5, -0.25), ncol=1)
    plt.tight_layout()
    if save_figs:
        save_figure(fig, output_dir / "January_power_flows", formats)

    fig = plt.figure(5)
    n = doy_slice(8, 1, 8, 4)
    plt.plot(CSP.power[n], label="Solar heat")
    plt.plot(gTES.power[n], label="Heat to geoTES")
    plt.plot(LTPC.Qin[n], label="Heat to LT power cycle")
    plt.gca().set_aspect(3.0, adjustable="box")
    plt.title("August 4")
    plt.xlabel("Hour")
    plt.ylabel("Heat, MWh-th")
    plt.legend(loc="lower center", bbox_to_anchor=(0.5, -0.25), ncol=1)
    plt.tight_layout()
    if save_figs:
        save_figure(fig, output_dir / "August_power_flows", formats)

    fig = plt.figure(6)
    n = doy_slice(2, 7, 2, 11)
    plt.plot(CSP.power[n], label="Solar heat")
    plt.plot(gTES.power[n], label="Heat to geoTES")
    plt.plot(LTPC.Qin[n], label="Heat to LT power cycle")
    plt.gca().set_aspect(3.0, adjustable="box")
    plt.title("February 7")
    plt.xlabel("Hour")
    plt.ylabel("Heat, MWh-th")
    plt.legend(loc="lower center", bbox_to_anchor=(0.5, -0.25), ncol=1)
    plt.tight_layout()
    if save_figs:
        save_figure(fig, output_dir / "Feb_power_flows", formats)

    Net_wout = LTPC.Wout_tot - (Energy_charge_prod + Energy_charge_inj + Energy_discharge_prod + Energy_discharge_inj)
    cap_hours = (gTES.energy_in_tot * gTES.recovery - gTES.energy_out_tot) * LTPC.eff0 * 1000.0 / LTPC.Wout0
    Ecap = (gTES.energy_in_tot * gTES.recovery - gTES.energy_out_tot) * LTPC.eff0 * 1e6
    d = 0.05
    G = (1.0 - (1.0 + d) ** -econ.lifetime) / (1.0 - (1.0 + d) ** -1.0)

    pel_5 = 0.05
    Rel_5 = pel_5 * Net_wout * 1e6
    cv_5 = (econ.total_capital_cost / G - Rel_5 + econ.OnM_total) / Ecap
    cap_payment_5 = (econ.total_capital_cost / G - Rel_5 + econ.OnM_total) / (LTPC.Wout0 * 1000.0)

    pel_10 = 0.10
    Rel_10 = pel_10 * Net_wout * 1e6
    cv_10 = (econ.total_capital_cost / G - Rel_10 + econ.OnM_total) / Ecap
    cap_payment_10 = (econ.total_capital_cost / G - Rel_10 + econ.OnM_total) / (LTPC.Wout0 * 1000.0)

    print(f"cv_5 = {cv_5: .6f}")
    print(f"cap_payment_5 = {cap_payment_5: .6f}")
    print(f"cv_10 = {cv_10: .6f}")
    print(f"cap_payment_10 = {cap_payment_10: .6f}")


if __name__ == "__main__":
    main()
