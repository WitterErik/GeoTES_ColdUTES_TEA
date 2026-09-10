import os
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

project_root = Path(__file__).resolve().parent
subsurface_module_path = project_root.parent / "Subsurface TEA Model"
if subsurface_module_path.exists():
    sys.path.insert(0, str(subsurface_module_path))

from economics_class import economics_class
from geoTES_class import geoTES_class
from SAM.call_SAM import call_SAM
from TES_class import TES_class
from thermo_cycle_class import thermo_cycle_class
from solar_class import solar_class
from DrillingCost import DrillingCostUpdated
from ExplorationCost import ExplorationCost
from InjectionPumpingCost import InjectionPumpingCost
from ProductionPumpingCost import ProductionPumpingCost


def ensure_output_folder(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    else:
        for existing_file in path.glob("*"):
            if existing_file.is_file():
                existing_file.unlink()


def build_operating_hours() -> tuple[tuple[int, int], tuple[int, int], tuple[int, int], np.ndarray, np.ndarray, np.ndarray]:
    # MATLAB hours are 1-based inclusive. Convert to 0-based exclusive-end ranges.
    phase1 = (0, (31 + 28 + 31) * 24)
    phase2 = (phase1[1], (31 + 28 + 31 + 30 + 31 + 30 + 31 + 31 + 30) * 24)
    phase3 = (phase2[1], (31 + 28 + 31 + 30 + 31 + 30 + 31 + 31 + 30 + 31 + 30 + 31) * 24)

    # MATLAB 6:8 and 17:24 are inclusive ranges. In Python 0-based, these are 5-7 and 16-23.
    op_hour1 = np.concatenate((np.arange(5, 8), np.arange(16, 24)))
    op_hour2 = np.concatenate((np.arange(5, 8), np.arange(16, 24)))
    op_hour3 = np.concatenate((np.arange(5, 8), np.arange(16, 24)))

    return phase1, phase2, phase3, op_hour1, op_hour2, op_hour3


def get_year_slice_indices(nY: int) -> tuple[int, int]:
    hours = 8760
    return (nY - 1) * hours, nY * hours


def main() -> None:
    save_figs = True
    output_dir = Path("Outputs")
    ensure_output_folder(output_dir)

    location = "Antelope Hills CA"
    nY = 2
    dT = 1.0

    phase1, phase2, phase3, op_hour1, op_hour2, op_hour3 = build_operating_hours()

    # CSP inputs
    mirror_type = "Parabolic trough"
    nominal_DNI = 950.0
    solar_multiple = 2.5
    CSP_Tmax = 400.0
    CSP_Tmin = 250.0
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

    # High-temperature power cycle inputs
    HTPC_type = "HE"
    HTPC_design = {
        "Wout": 100.0,
        "T0": 25.0,
        "TIT": -350.0,
        "eff": 0.117,
        "fan": 0.0,
        "Qin": -1.0,
    }
    HTPC_foff = project_root / "data" / "example_off_design.xlsx"
    HTPC_cost = {"power_block": 500.0, "HX": 500.0}
    HTPC = thermo_cycle_class(HTPC_type, HTPC_design, str(HTPC_foff), HTPC_cost, nY)

    # Low-temperature power cycle inputs
    LTPC_type = "HE"
    LTPC_design = {
        "Wout": 100.0,
        "T0": 25.0,
        "TIT": 200.0,
        "fan": 0.1,
    }
    LTPC_foff = project_root / "data" / "example_off_design.xlsx"
    LTPC_cost = {"power_block": 1000.0, "HX": 250.0}
    LTPC = thermo_cycle_class(LTPC_type, LTPC_design, str(LTPC_foff), LTPC_cost, nY)

    LTPC.Qin0 = HTPC.Qout0
    LTPC.Wout0 = LTPC.eff0 * LTPC.Qin0

    # High-temperature thermal storage inputs
    TES_duration = 4.0
    TES_fluid = "Therminol VP1"
    TES_Thot = CSP_Tmax
    TES_Tcld = CSP_Tmin
    TES_Qloss = 1.0
    TES_max_tank_vol = 50000.0
    ins = {"k": 0.08, "rho": 150.0}
    TES_cost = {"fluid": 1.5, "tank": 0.0, "insulation": 50.0}

    TES = TES_class(
        TES_duration,
        HTPC.Qin0,
        TES_fluid,
        TES_Thot,
        TES_Tcld,
        TES_Qloss,
        TES_max_tank_vol,
        ins,
        TES_cost,
    )
    TES.tank_sizes()

    # Low-temperature thermal storage inputs
    reversible_wells = False
    gTES_recovery = 0.95
    gTES_Tinit = 50.0
    gTES_flowrate = {"P": 5.6, "I": 11.0}
    gTES_Qmax = 1e5
    gTES_props = {
        "rho": 2000.0,
        "cp": 800.0,
        "void": 0.32,
        "depth": 500.0,
        "thickness": 100.0,
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
        "lifetime": 50,
        "elec_price": 0.05,
        "inflation": 0.025,
        "irr": 0.10,
        "debt_frac": 0.60,
        "debt_IR": 0.08,
        "tax_rate": 0.28,
        "deprec": [0.20, 0.32, 0.20, 0.14, 0.14],
        "annual_cost": [1.0, 0.0, 0.0],
        "construc_IR": 0.0,
        "OnM": 0.015,
        "ITC": 0.4,
    }
    econ = economics_class(finance)

    gTES.charge_production.T = gTES.Tinit
    gTES.charge_production.p = 40.0
    gTES.charge_production.calc_fluid_props("pT")

    gTES.charge_injection.T = LTPC.Tmax
    gTES.charge_injection.q = 0.0
    gTES.charge_injection.p = 40.0
    gTES.charge_injection.calc_fluid_props("pT")

    gTES.discharge_production.T = LTPC.Tmax
    gTES.discharge_production.q = 0.0
    gTES.discharge_production.calc_fluid_props("qT")

    gTES.discharge_injection.T = gTES.Tinit
    gTES.discharge_injection.p = 40.0
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

    T_amb = np.asarray(out.Tamb, dtype=float).ravel()
    HTPC.Tamb = np.tile(T_amb, nY)
    LTPC.Tamb = HTPC.Tamb.copy()

    HTPC.Qin = np.zeros(n_hours, dtype=float)
    TES.power = np.zeros(n_hours, dtype=float)
    TES.energy = np.zeros(n_hours, dtype=float)
    gTES.power = np.zeros(n_hours, dtype=float)
    gTES.energy = np.zeros(n_hours, dtype=float)
    CSP.dumped = np.zeros(n_hours, dtype=float)

    HTPC.Qin[0] = CSP.power[0]
    HTPC.interpolate_off_design(0)

    for i in range(1, n_hours):
        TES.energy[i] = TES.energy[i - 1]
        gTES.energy[i] = gTES.energy[i - 1]

        houry = i
        if phase1[0] <= houry < phase1[1]:
            operate = int(houry % 24) in op_hour1
        elif phase2[0] <= houry < phase2[1]:
            operate = int(houry % 24) in op_hour2
        else:
            operate = int(houry % 24) in op_hour3

        if operate:
            if CSP.power[i] > HTPC.Qin0:
                HTPC.Qin[i] = HTPC.Qin0
                HTPC.interpolate_off_design(i)

                LTPC.Qin[i] = LTPC.Qin0
                LTPC.interpolate_off_design(i)

                dP = CSP.power[i] - HTPC.Qin0
                dTES = TES.energy_capacity - TES.energy[i - 1]
                if dTES > dP * dT:
                    TES.power[i] = dP
                    TES.energy[i] = TES.energy[i - 1] + dP * dT
                else:
                    TES.power[i] = dTES / dT
                    TES.energy[i] = TES.energy_capacity
                    dP -= TES.power[i]
                    if dP < gTES.Qmax:
                        gTES.power[i] = dP
                    else:
                        gTES.power[i] = gTES.Qmax
                        CSP.dumped[i] = dP - gTES.Qmax
                    gTES.energy[i] = gTES.energy[i - 1] + gTES.power[i] * dT * gTES.recovery
            else:
                dP = HTPC.Qin0 - CSP.power[i]
                if dP * dT < TES.energy[i - 1]:
                    TES.power[i] = -dP
                    TES.energy[i] = TES.energy[i - 1] - dP * dT
                    HTPC.Qin[i] = HTPC.Qin0
                    HTPC.interpolate_off_design(i)
                    LTPC.Qin[i] = LTPC.Qin0
                    LTPC.interpolate_off_design(i)
                else:
                    TES.power[i] = -TES.energy[i - 1] / dT
                    TES.energy[i] = 0.0
                    HTPC.Qin[i] = CSP.power[i] - TES.power[i]
                    HTPC.interpolate_off_design(i)

                    Qex = HTPC.Qin[i] - HTPC.Wout[i]
                    dQ = LTPC.Qin0 - Qex
                    if dQ > gTES.energy[i - 1]:
                        gTES.power[i] = -gTES.energy[i - 1] / dT
                    else:
                        gTES.power[i] = -dQ

                    gTES.energy[i] = gTES.energy[i - 1] + gTES.power[i]
                    LTPC.Qin[i] = Qex - gTES.power[i]
                    LTPC.interpolate_off_design(i)
        else:
            dP = CSP.power[i]
            dTES = TES.energy_capacity - TES.energy[i - 1]
            if dTES > dP * dT:
                TES.power[i] = dP
                TES.energy[i] = TES.energy[i - 1] + dP * dT
            else:
                TES.power[i] = dTES / dT
                TES.energy[i] = TES.energy_capacity
                dP -= TES.power[i]
                if dP > HTPC.Qin0:
                    HTPC.Qin[i] = HTPC.Qin0
                    HTPC.interpolate_off_design(i)
                    excess = dP - HTPC.Qin0
                else:
                    HTPC.Qin[i] = dP
                    HTPC.interpolate_off_design(i)
                    excess = 0.0

                Qex = HTPC.Qin[i] - HTPC.Wout[i] + excess
                if Qex < gTES.Qmax:
                    gTES.power[i] = Qex
                else:
                    gTES.power[i] = gTES.Qmax
                    CSP.dumped[i] = Qex - gTES.Qmax
                gTES.energy[i] = gTES.energy[i - 1] + gTES.power[i] * dT * gTES.recovery

    gTES.geoTES_size()
    gTES.geoTES_well_flows()

    CSP.CSP_annual_energy()
    LTPC.PC_annual_energy()
    HTPC.PC_annual_energy()
    gTES.geoTES_annual_energy()
    TES.TES_annual_energy()

    CSP.calc_CSP_cost(LTPC)
    LTPC.calc_PC_cost()
    HTPC.calc_PC_cost()
    TES.calc_TES_cost()

    Exploration_Cost = ExplorationCost("Greenfield", 3, 20000, 1.2)
    Total_Exploration_Cost = Exploration_Cost.ExplorationCostCalc()

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
        Step1 = Charge_ProdPumping_Estimation.HeadProdTop()
        Step2 = Charge_ProdPumping_Estimation.HeadSunction(Step1.Prodtop)
        Step3 = Charge_ProdPumping_Estimation.Sunctiondepth(Step2)
        Step4 = Charge_ProdPumping_Estimation.CasingFriction(Step3, Step1.Prodtop)
        Step5 = Charge_ProdPumping_Estimation.Pumppower(Step3, Step4)
        Step6 = Charge_ProdPumping_Estimation.Pumpcost(Step5, Step3)
        Charge_ProdPumping_Cost_Duty = Charge_ProdPumping_Estimation.TotalPumpDutyCost(Step5, Step6)

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
        Step7 = Charge_InjPumping_Estimation.HeadSunction()
        Step8 = Charge_InjPumping_Estimation.HeadInjection(Step7)
        Step9 = Charge_InjPumping_Estimation.Pumppower(Step8)
        Step10 = Charge_InjPumping_Estimation.Pumpcost(Step9)
        Charge_InjPumping_Cost_Duty = Charge_InjPumping_Estimation.TotalPumpDutyCost(Step9, Step10)

        LengthofFlowline = 300.0
        PipingUnitCost = 256.98
        TotalNumberofWells = gTES.charge_prod_Nwell + gTES.charge_inj_Nwell
        Charge_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * TotalNumberofWells

        Charge_WellFieldMaintenance = 0.015 * (
            Total_Charge_Drilling_Cost_prod
            + Total_Charge_Drilling_Cost_inj
            + Charge_FlowLineCost
        )
        Charge_PumpMaintenance = Charge_ProdPumping_Estimation.PumpMaintenanceCost(Step3, Step6)

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
    Step1 = Discharge_ProdPumping_Estimation.HeadProdTop()
    Step2 = Discharge_ProdPumping_Estimation.HeadSunction(Step1.Prodtop)
    Step3 = Discharge_ProdPumping_Estimation.Sunctiondepth(Step2)
    Step4 = Discharge_ProdPumping_Estimation.CasingFriction(Step3, Step1.Prodtop)
    Step5 = Discharge_ProdPumping_Estimation.Pumppower(Step3, Step4)
    Step6 = Discharge_ProdPumping_Estimation.Pumpcost(Step5, Step3)
    Discharge_ProdPumping_Cost_Duty = Discharge_ProdPumping_Estimation.TotalPumpDutyCost(Step5, Step6)

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
    Step7 = Discharge_InjPumping_Estimation.HeadSunction()
    Step8 = Discharge_InjPumping_Estimation.HeadInjection(Step7)
    Step9 = Discharge_InjPumping_Estimation.Pumppower(Step8)
    Step10 = Discharge_InjPumping_Estimation.Pumpcost(Step9)
    Discharge_InjPumping_Cost_Duty = Discharge_InjPumping_Estimation.TotalPumpDutyCost(Step9, Step10)
    if reversible_wells:
        Discharge_InjPumping_Cost_Duty = np.array([0.0, 0.0])

    LengthofFlowline = 300.0
    PipingUnitCost = 256.98
    TotalNumberofWells = gTES.discharge_prod_Nwell + gTES.discharge_inj_Nwell
    Discharge_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * TotalNumberofWells
    if reversible_wells:
        Discharge_FlowLineCost = 0.0

    Discharge_WellFieldMaintenance = 0.015 * (
        Total_Discharge_Drilling_Cost_prod
        + Total_Discharge_Drilling_Cost_inj
        + Discharge_FlowLineCost
    )
    Discharge_PumpMaintenance = Discharge_ProdPumping_Estimation.PumpMaintenanceCost(Step3, Step6)

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

    last_year_slice = slice(*get_year_slice_indices(nY))
    year_power = gTES.power[last_year_slice]
    charging_hours = int(np.count_nonzero(year_power > 0.0))
    discharging_hours = int(np.count_nonzero(year_power < 0.0))

    discharge_air_fan = discharging_hours * LTPC.fan0 * (LTPC.Wout0 + HTPC.Wout0) / 1e3

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

    econ.surface_capital_cost = CSP.total_cost + TES.total_cost
    econ.OnM_surface = econ.OnM * econ.surface_capital_cost
    econ.Ein = Energy_charge_prod + Energy_charge_inj + Energy_discharge_prod + Energy_discharge_inj
    econ.Qout = LTPC.Qin_tot
    econ.calc_fcr()
    econ.calc_levelized_cost("H")

    econ.surface_capital_cost = CSP.total_cost + LTPC.total_cost + TES.total_cost + HTPC.total_cost
    econ.OnM_surface = econ.OnM * econ.surface_capital_cost
    econ.Ein = Energy_charge_prod + Energy_charge_inj
    econ.Eout = LTPC.Wout_tot + HTPC.Wout_tot - (Energy_discharge_prod + Energy_discharge_inj) - discharge_air_fan
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
            HTPC.total_cost,
            TES.total_cost,
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

    net_elec = HTPC.Wout_tot + LTPC.Wout_tot - (Energy_discharge_prod + Energy_discharge_inj) - discharge_air_fan
    cap_fac = 100.0 * 1000.0 * net_elec / (
        HTPC.Wout0
        + LTPC.Wout0
        - Discharge_ProdPumping_Cost_Duty[0] / 1e3
        - Discharge_InjPumping_Cost_Duty[0] / 1e3
        - LTPC.fan0 * LTPC.Wout0
    ) / 8760.0

    print("\nPOWER OUTPUTS\n")
    print(f"Maximum solar power generated             = {np.max(CSP.power):6.2f} MW-th")
    print(f"High-temp power cycle power output        = {HTPC.Wout0:6.2f} MW-e")
    print(f"Average high-temp power cycle output      = {np.mean(HTPC.Wout[HTPC.Wout[last_year_slice] > 0]):6.2f} MW-e")
    print(f"Low-temp Power cycle power output         = {LTPC.Wout0:6.2f} MW-e")
    print(f"Average power cycle output                = {np.mean(LTPC.Wout[LTPC.Wout[last_year_slice] > 0]):6.2f} MW-e")
    print(f"Max. thermal power into subsurface        = {np.max(gTES.power[last_year_slice]):6.2f} MW-th")
    print(f"Max. thermal power out of subsurface      = {-np.min(gTES.power[last_year_slice]):6.2f} MW-th")
    print(f"Charge production pump power              = {Charge_ProdPumping_Cost_Duty[0] / 1e3:6.2f} MW-e")
    print(f"Charge injection pump power               = {Charge_InjPumping_Cost_Duty[0] / 1e3:6.2f} MW-e")
    print(f"Discharge production pump power           = {Discharge_ProdPumping_Cost_Duty[0] / 1e3:6.2f} MW-e")
    print(f"Discharge injection pump power            = {Discharge_InjPumping_Cost_Duty[0] / 1e3:6.2f} MW-e")

    print("\nANNUAL ENERGY OUTPUTS\n")
    print(f"Available solar heat                      = {CSP.available_solar_heat:6.2f} GWh-th")
    print(f"Solar heat generated                      = {CSP.solar_thermal_generated:6.2f} GWh-th")
    print(f"Dumped solar heat                         = {CSP.total_dumped:6.2f} GWh-th\n")
    print(f"Heat delivered to high-temp. cycle        = {HTPC.Qin_tot:6.2f} GWh-th")
    print(f"Electricity generated by high-temp. cycle = {HTPC.Wout_tot:6.2f} GWh-e\n")
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
    print(f"Total electricity generation              = {HTPC.Wout_tot + LTPC.Wout_tot:6.2f} GWh-e\n")
    print(f"Net electricity generated                 = {net_elec:6.2f} GWh-e")
    print(f"Capacity factor                           = {cap_fac:6.2f} %\n")
    print(f"Number of charging production wells       = {gTES.charge_prod_Nwell:6.2f}")
    print(f"Number of charging injection wells        = {gTES.charge_inj_Nwell:6.2f}")
    print(f"Number of discharging production wells    = {gTES.discharge_prod_Nwell:6.2f}")
    print(f"Number of discharging injection wells     = {gTES.discharge_inj_Nwell:6.2f}\n")


if __name__ == "__main__":
    main()
