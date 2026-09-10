import os
import sys
from pathlib import Path
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np

try:
    from scipy.io import loadmat
except ImportError:
    loadmat = None

project_root = Path(__file__).resolve().parent
subsurface_module_path = project_root.parent / "Subsurface TEA Model"
if subsurface_module_path.exists():
    sys.path.insert(0, str(subsurface_module_path))

from solar_class import solar_class
from thermo_cycle_class import thermo_cycle_class
from TES_class import TES_class
from geoTES_class import geoTES_class
from economics_class import economics_class
from SAM.call_SAM import call_SAM
from ExplorationCost import ExplorationCost
from DrillingCost import DrillingCost
from ProductionPumpingCost import ProductionPumpingCost
from InjectionPumpingCost import InjectionPumpingCost


def ensure_output_folder(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    else:
        for existing_file in path.glob("*"):
            if existing_file.is_file():
                existing_file.unlink()


def read_csv_column(path: Path, column_index: int, skip_rows: int) -> np.ndarray:
    if not path.is_absolute():
        path = project_root / path
    return np.genfromtxt(path, delimiter=",", skip_header=skip_rows, usecols=[column_index])


def main() -> None:
    save_figs = 0
    output_dir = Path("Outputs")
    ensure_output_folder(output_dir)

    location = "Imperial CA"
    year = 2020

    HE_type = "HE"
    HE_design = {
        "Wout": 100.0,
        "T0": 15.0,
        "eff": 0.11,
        "TIT": -1.0,
        "Qin": -1.0,
    }
    HE_foff = str(project_root / "data" / "example_off_design_v1.xlsx")
    HE_cost = {"power_block": 1000.0, "HX": 0.0}
    HE = thermo_cycle_class(HE_type, HE_design, HE_foff, HE_cost)

    HP_type = "HP"
    HP_design = {
        "Win": 250.0,
        "T0": 15.0,
        "COP": 3.7,
        "COT": -1.0,
        "Qout": -1.0,
    }
    HP_foff = str(project_root / "data" / "example_off_design_HP_v1.xlsx")
    HP_cost = {"power_block": 1000.0, "HX": 0.0}
    HP = thermo_cycle_class(HP_type, HP_design, HP_foff, HP_cost)

    CB = {"Tmax": 150.0, "Tmin": 5.0}
    CB["RTeff"] = HE.eff0 * HP.COP0

    gCTES_recovery = 0.95
    gCTES_Tinit = 50.0
    gCTES_flowrate = 60.0
    gCTES_Qmax = 10000.0
    gCTES_props = {"rho": 2000.0, "cp": 800.0, "void": 0.25}
    gCTES_fluid = "water"
    gCTES = geoTES_class(
        gCTES_recovery,
        gCTES_Tinit,
        gCTES_flowrate,
        gCTES_Qmax,
        gCTES_props,
        gCTES_fluid,
    )

    gHTES_recovery = 0.95
    gHTES_Tinit = 50.0
    gHTES_flowrate = 60.0
    gHTES_Qmax = 1000.0
    gHTES_props = {"rho": 2000.0, "cp": 800.0, "void": 0.25}
    gHTES_fluid = "water"
    gHTES = geoTES_class(
        gHTES_recovery,
        gHTES_Tinit,
        gHTES_flowrate,
        gHTES_Qmax,
        gHTES_props,
        gHTES_fluid,
    )

    finance = {
        "lifetime": 30,
        "elec_price": 0.025,
        "inflation": 0.025,
        "irr": 0.10,
        "debt_frac": 0.60,
        "debt_IR": 0.08,
        "tax_rate": 0.40,
        "deprec": [0.20, 0.32, 0.20, 0.14, 0.14],
        "annual_cost": [1.0, 0.0, 0.0],
        "construc_IR": 0.0,
        "OnM": 0.05,
    }
    econ = economics_class(finance)

    if location == "Imperial CA":
        if loadmat is None:
            raise ImportError(
                "scipy is required to read 'caliPrices.mat' for Imperial CA price data"
            )
        mat_data = loadmat(str(project_root / "data" / "caliPrices.mat"))
        econ.elec_price_hourly = mat_data["cali"]["margCost"][0, 0].ravel()
    elif location == "Elk Hills CA":
        if year == 2020:
            raise ValueError("Elk Hills 2020 price data not available")
        if year == 2021:
            econ.elec_price_hourly = read_csv_column(
                Path("data/2021_CAIOS_EK_DA.csv"), 1, skip_rows=1
            )
        elif year == 2022:
            econ.elec_price_hourly = read_csv_column(
                Path("data/2022_CAIOS_EK_DA.csv"), 1, skip_rows=1
            )
        else:
            raise ValueError("Unsupported year for Elk Hills CA")
    elif location == "ERCOT West":
        if year == 2020:
            econ.elec_price_hourly = read_csv_column(
                Path("data/2020_PECO__DA.csv"), 1, skip_rows=1
            )
        elif year == 2021:
            econ.elec_price_hourly = read_csv_column(
                Path("data/2021_PECO__DA.csv"), 1, skip_rows=1
            )
        else:
            raise ValueError("ERCOT West 2022 price data not available")
    else:
        raise ValueError("Unsupported location")

    econ.median_price = float(np.median(econ.elec_price_hourly))
    econ.charge_price = 0.9999 * econ.median_price
    econ.discharge_price = 1.001 * econ.median_price

    expected_hours = 8760
    if econ.elec_price_hourly is not None:
        if econ.elec_price_hourly.shape[0] > expected_hours:
            econ.elec_price_hourly = econ.elec_price_hourly[:expected_hours]
        elif econ.elec_price_hourly.shape[0] < expected_hours:
            raise ValueError(
                f"Hourly price data length {econ.elec_price_hourly.shape[0]} "
                f"does not match expected {expected_hours} hours"
            )

    for reservoir in (gCTES, gHTES):
        reservoir.charge_production.T = reservoir.Tinit
        reservoir.charge_production.p = 10.0
        reservoir.charge_production.calc_fluid_props("pT")

        reservoir.charge_injection.q = 0.0
        reservoir.charge_injection.T = CB["Tmax"] if reservoir is gHTES else CB["Tmin"]
        reservoir.charge_injection.calc_fluid_props("qT")

        reservoir.discharge_production.q = 0.0
        reservoir.discharge_production.T = CB["Tmax"] if reservoir is gHTES else CB["Tmin"]
        reservoir.discharge_production.calc_fluid_props("qT")

        reservoir.discharge_injection.T = reservoir.Tinit
        reservoir.discharge_injection.p = 10.0
        reservoir.discharge_injection.calc_fluid_props("pT")

    if location == "Imperial CA":
        location_path = project_root / "data" / "imperial_ca_32.835205_-115.572398_psmv3_60_tmy.csv"
        column_index = 9
        skip_rows = 3
    elif location == "Elk Hills CA":
        location_path = project_root / "data" / "Elk_Hills_tmy-2021.csv"
        column_index = 11
        skip_rows = 3
    else:
        location_path = project_root / "data" / "ERCOT_West_tmy-2021.csv"
        column_index = 11
        skip_rows = 3

    Tamb = read_csv_column(location_path, column_index, skip_rows)
    hours = 8760
    hours2 = 2 * hours

    HE.Tamb = np.concatenate((Tamb, Tamb))
    HP.Tamb = np.concatenate((Tamb, Tamb))
    elec_prices = np.concatenate((econ.elec_price_hourly, econ.elec_price_hourly))

    HE.Win = np.zeros(hours2, dtype=float)
    HE.Qin = np.zeros(hours2, dtype=float)
    HE.Qout = np.zeros(hours2, dtype=float)
    HP.Win = np.zeros(hours2, dtype=float)
    HP.Qin = np.zeros(hours2, dtype=float)
    HP.Qout = np.zeros(hours2, dtype=float)
    gCTES.power = np.zeros(hours2, dtype=float)
    gCTES.energy = np.zeros(hours2, dtype=float)
    gHTES.power = np.zeros(hours2, dtype=float)
    gHTES.energy = np.zeros(hours2, dtype=float)

    dT = 1.0

    for i in range(1, hours2):
        gCTES.energy[i] = gCTES.energy[i - 1]
        gHTES.energy[i] = gHTES.energy[i - 1]

        if elec_prices[i] <= econ.charge_price:
            HP.Win[i] = HP.Win0
            HP.interpolate_off_design(i)
            gHTES.power[i] = HP.Qout[i]
            gHTES.energy[i] = gHTES.energy[i - 1] + gHTES.power[i] * dT * gHTES.recovery
            gCTES.power[i] = -HP.Qin0 * (gHTES.power[i] / HP.Qout0)
            gCTES.energy[i] = gCTES.energy[i - 1] + gCTES.power[i] * dT * gCTES.recovery

        elif elec_prices[i] > econ.discharge_price:
            Qh = HE.Qin0
            if Qh * dT < gHTES.energy[i - 1]:
                gHTES.power[i] = -Qh
            else:
                gHTES.power[i] = -gHTES.energy[i - 1] / dT

            gHTES.energy[i] = gHTES.energy[i - 1] + gHTES.power[i] * dT
            HE.Qin[i] = -gHTES.power[i]
            HE.interpolate_off_design(i)
            gCTES.power[i] = -HE.Qout0 * (gHTES.power[i] / HE.Qin0)
            gCTES.energy[i] = gCTES.energy[i - 1] + gCTES.power[i] * dT

    gCTES.geoTES_size()
    gCTES.geoTES_well_flows()
    gHTES.geoTES_size()
    gHTES.geoTES_well_flows()

    HP.PC_annual_energy()
    HE.PC_annual_energy()
    gCTES.geoTES_annual_energy()
    gHTES.geoTES_annual_energy()

    HP.calc_PC_cost()
    HE.calc_PC_cost()

    Exploration_Cost = ExplorationCost("Greenfield", 3, 20000, 1.2)
    Total_Exploration_Cost = Exploration_Cost.exploration_cost_calc()
    PPImultiplier = 1.175
    FieldDevPlantPermitting = 1_000_000.0 * PPImultiplier

    Charge_Drilling_Cost = DrillingCost(
        gCTES.charge_prod_Nwell,
        gCTES.charge_inj_Nwell,
        500,
        200,
        "Large",
        1,
        1.5,
        "Vertical",
        "Openhole",
    )
    Charge_Well_Cost = Charge_Drilling_Cost.well_cost()
    Total_Charge_Drilling_Cost = Charge_Drilling_Cost.total_dc(Charge_Well_Cost)

    ResTemp = gCTES.Tinit
    Pflowrate = gCTES.flowrate_per_well * gCTES.charge_production.rho / 1000.0
    Charge_ProdPumping_Estimation = ProductionPumpingCost(
        ResTemp,
        Pflowrate,
        gCTES.charge_prod_Nwell,
        6370,
        500,
        200,
        "Large",
        "Lineshaft",
        "Openhole",
        1.553,
    )
    Step1 = Charge_ProdPumping_Estimation.head_prod_top()
    Step2 = Charge_ProdPumping_Estimation.head_suction(Step1)
    Step3 = Charge_ProdPumping_Estimation.suction_depth(Step2)
    Step4 = Charge_ProdPumping_Estimation.casing_friction(Step3, Step1)
    Step5 = Charge_ProdPumping_Estimation.pump_power(Step3, Step4)
    Step6 = Charge_ProdPumping_Estimation.pump_cost(Step5, Step3)
    Charge_ProdPumping_Cost_Duty = Charge_ProdPumping_Estimation.total_pump_duty_cost(Step5, Step6)

    InjTemp = CB["Tmin"]
    Iflowrate = gCTES.flowrate_per_well * gCTES.charge_injection.rho / 1000.0
    PressureThermalSource = gCTES.charge_injection.p * 14.5038
    Charge_InjPumping_Estimation = InjectionPumpingCost(
        ResTemp,
        InjTemp,
        Iflowrate,
        Pflowrate,
        PressureThermalSource,
        gCTES.charge_inj_Nwell,
        7645,
        500,
        200,
        "Large",
        "Openhole",
        1.533,
        "Discharge",
    )
    Step7 = Charge_InjPumping_Estimation.head_suction()
    Step8 = Charge_InjPumping_Estimation.head_injection(Step7)
    Step9 = Charge_InjPumping_Estimation.pump_power(Step8)
    Step10 = Charge_InjPumping_Estimation.pump_cost(Step9)
    Charge_InjPumping_Cost_Duty = Charge_InjPumping_Estimation.total_pump_duty_cost(Step9, Step10)

    LengthofFlowline = 750.0
    PipingUnitCost = 256.98
    TotalNumberofWells = gCTES.charge_prod_Nwell + gCTES.charge_inj_Nwell
    Charge_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * TotalNumberofWells

    Charge_WellFieldMaintenance = 0.015 * (Total_Charge_Drilling_Cost + Charge_FlowLineCost)
    Charge_PumpMaintenance = Charge_ProdPumping_Estimation.pump_maintenance_cost(Step3, Step6)

    OilSaturation = 0.0
    NumberProductionWells = gCTES.charge_prod_Nwell
    ProductionRateperWell = Pflowrate
    MakeupWaterUnitCost = 0.65
    SubsurfaceWaterLoss = OilSaturation + 0.001
    Charge_MakeupWaterSubsurface = (
        MakeupWaterUnitCost
        * NumberProductionWells
        * (ProductionRateperWell * 18.0917 * 34.2857 * 365.0)
        * SubsurfaceWaterLoss
    )

    Discharge_Drilling_Cost = DrillingCost(
        gHTES.charge_prod_Nwell,
        gHTES.charge_inj_Nwell,
        500,
        200,
        "Large",
        1,
        1.5,
        "Vertical",
        "Openhole",
    )
    Discharge_Well_Cost = Discharge_Drilling_Cost.well_cost()
    Total_Discharge_Drilling_Cost = Discharge_Drilling_Cost.total_dc(Discharge_Well_Cost)

    ResTemp = gHTES.Tinit
    Pflowrate = gHTES.flowrate_per_well * gHTES.charge_production.rho / 1000.0
    Discharge_ProdPumping_Estimation = ProductionPumpingCost(
        ResTemp,
        Pflowrate,
        gHTES.charge_prod_Nwell,
        6370,
        500,
        200,
        "Large",
        "Lineshaft",
        "Openhole",
        1.553,
    )
    Step1 = Discharge_ProdPumping_Estimation.head_prod_top()
    Step2 = Discharge_ProdPumping_Estimation.head_suction(Step1)
    Step3 = Discharge_ProdPumping_Estimation.suction_depth(Step2)
    Step4 = Discharge_ProdPumping_Estimation.casing_friction(Step3, Step1)
    Step5 = Discharge_ProdPumping_Estimation.pump_power(Step3, Step4)
    Step6 = Discharge_ProdPumping_Estimation.pump_cost(Step5, Step3)
    Discharge_ProdPumping_Cost_Duty = Discharge_ProdPumping_Estimation.total_pump_duty_cost(Step5, Step6)

    InjTemp = gHTES.Tinit
    Iflowrate = gHTES.flowrate_per_well * gHTES.charge_injection.rho / 1000.0
    PressureThermalSource = gHTES.charge_injection.p * 14.5038
    Discharge_InjPumping_Estimation = InjectionPumpingCost(
        ResTemp,
        InjTemp,
        Iflowrate,
        Pflowrate,
        PressureThermalSource,
        gHTES.charge_inj_Nwell,
        7645,
        500,
        200,
        "Large",
        "Openhole",
        1.533,
        "Discharge",
    )
    Step7 = Discharge_InjPumping_Estimation.head_suction()
    Step8 = Discharge_InjPumping_Estimation.head_injection(Step7)
    Step9 = Discharge_InjPumping_Estimation.pump_power(Step8)
    Step10 = Discharge_InjPumping_Estimation.pump_cost(Step9)
    Discharge_InjPumping_Cost_Duty = Discharge_InjPumping_Estimation.total_pump_duty_cost(Step9, Step10)

    LengthofFlowline = 750.0
    PipingUnitCost = 256.98
    Discharge_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * (
        gHTES.charge_prod_Nwell + gHTES.charge_inj_Nwell
    )

    Discharge_WellFieldMaintenance = 0.015 * (Total_Discharge_Drilling_Cost + Discharge_FlowLineCost)
    Discharge_PumpMaintenance = Discharge_ProdPumping_Estimation.pump_maintenance_cost(Step3, Step6)

    NumberProductionWells = gHTES.charge_prod_Nwell
    ProductionRateperWell = Pflowrate
    Discharge_MakeupWaterSubsurface = (
        MakeupWaterUnitCost
        * NumberProductionWells
        * (ProductionRateperWell * 18.0917 * 34.2857 * 365.0)
        * SubsurfaceWaterLoss
    )

    SubsurfaceCapitalCost = (
        Total_Exploration_Cost
        + FieldDevPlantPermitting
        + Total_Charge_Drilling_Cost
        + Charge_ProdPumping_Cost_Duty[1]
        + Charge_InjPumping_Cost_Duty[1]
        + Discharge_ProdPumping_Cost_Duty[1]
        + Discharge_InjPumping_Cost_Duty[1]
        + Charge_FlowLineCost
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
    econ.surface_capital_cost = HE.total_cost + HP.total_cost
    econ.OnM_surface = econ.OnM * econ.surface_capital_cost
    econ.Ein = HP.Win_tot
    econ.Eout = HE.Wout_tot

    econ.calc_fcr()
    econ.calc_levelized_cost("S")
    econ.calc_revenue(HP.Win[hours:hours2], HE.Wout[hours:hours2])

    if econ.charge_cost_hourly is not None and econ.charge_cost_hourly.shape[0] == hours:
        econ.charge_cost_hourly = np.concatenate((econ.charge_cost_hourly, econ.charge_cost_hourly))
    if econ.discharge_revenue_hourly is not None and econ.discharge_revenue_hourly.shape[0] == hours:
        econ.discharge_revenue_hourly = np.concatenate((econ.discharge_revenue_hourly, econ.discharge_revenue_hourly))

    print("\nPOWER OUTPUTS\n")
    print(f"Heat pump power input                     = {HP.Win0:6.2f} MW-e")
    print(f"Heat pump heat output                     = {HP.Qout0:6.2f} MW-th")
    print(f"Heat pump heat input                      = {HP.Qin0:6.2f} MW-th")
    print(
        f"Average heat pump power input             = {np.mean(HP.Win[hours:hours2][HP.Win[hours:hours2] > 0]):6.2f} MW-e\n"
    )
    print(f"Heat engine power output                  = {HE.Wout0:6.2f} MW-e")
    print(f"Heat engine heat input                    = {HE.Qin0:6.2f} MW-th")
    print(f"Heat engine heat output                   = {HE.Qout0:6.2f} MW-th")
    print(
        f"Average power cycle output                = {np.mean(HE.Wout[hours:hours2][HE.Wout[hours:hours2] > 0]):6.2f} MW-e\n"
    )
    print(f"Max. thermal power into hot storage       = {np.max(gHTES.power[hours:hours2]):6.2f} MW-th")
    print(f"Max. thermal power out of hot storage     = {-np.min(gHTES.power[hours:hours2]):6.2f} MW-th")
    print(f"Max. thermal power into cold storage      = {np.max(gCTES.power[hours:hours2]):6.2f} MW-th")
    print(f"Max. thermal power out of cold storage    = {-np.min(gCTES.power[hours:hours2]):6.2f} MW-th")
    print(f"Charge production pump power              = {Charge_ProdPumping_Cost_Duty[0] / 1e3:6.2f} MW-e")
    print(f"Charge injection pump power               = {Charge_InjPumping_Cost_Duty[0] / 1e3:6.2f} MW-e")
    print(f"Discharge production pump power           = {Discharge_ProdPumping_Cost_Duty[0] / 1e3:6.2f} MW-e")
    print(f"Discharge injection pump power            = {Discharge_InjPumping_Cost_Duty[0] / 1e3:6.2f} MW-e")

    print("\nANNUAL ENERGY OUTPUTS\n")
    print(f"Electricity input to heat pump            = {HP.Win_tot:6.2f} GWh-e")
    print(f"Electricity output of heat engine         = {HE.Wout_tot:6.2f} GWh-e\n")
    print(f"Heat delivered to hot storage             = {gHTES.energy_in_tot:6.2f} GWh-th")
    print(f"Heat extracted from hot storage           = {gHTES.energy_out_tot:6.2f} GWh-th\n")
    print(f"Heat delivered to cold storage            = {gCTES.energy_in_tot:6.2f} GWh-th")
    print(f"Heat extracted from cold storage          = {gCTES.energy_out_tot:6.2f} GWh-th\n")
    print(
        f"Charge production pump consumption        = {np.count_nonzero(gCTES.power[hours:hours2] > 0) * Charge_ProdPumping_Cost_Duty[0] / 1e6:6.2f} GWh-e"
    )
    print(
        f"Charge injection pump consumption         = {np.count_nonzero(gCTES.power[hours:hours2] > 0) * Charge_InjPumping_Cost_Duty[0] / 1e6:6.2f} GWh-e"
    )
    print(
        f"Discharge production pump consumption     = {np.count_nonzero(gCTES.power[hours:hours2] < 0) * Discharge_ProdPumping_Cost_Duty[0] / 1e6:6.2f} GWh-e"
    )
    print(
        f"Discharge injection pump consumption      = {np.count_nonzero(gCTES.power[hours:hours2] < 0) * Discharge_InjPumping_Cost_Duty[0] / 1e6:6.2f} GWh-e\n"
    )

    print("\nSUBSURFACE COST RESULTS\n")
    print(f"Total Exploration Cost          = {Total_Exploration_Cost / 1e6:6.2f} M$")
    print(f"Permitting cost                 = {FieldDevPlantPermitting / 1e6:6.2f} M$\n")
    print(f"Total Charge Drilling Cost      = {Total_Charge_Drilling_Cost / 1e6:6.2f} M$")
    print(f"Charge production pump cost     = {Charge_ProdPumping_Cost_Duty[1] / 1e6:6.2f} M$")
    print(f"Charge injection pump cost      = {Charge_InjPumping_Cost_Duty[1] / 1e6:6.2f} M$")
    print(f"Charge flow line cost           = {Charge_FlowLineCost / 1e6:6.2f} M$\n")
    print(f"Total Discharge Drilling Cost   = {Total_Discharge_Drilling_Cost / 1e6:6.2f} M$")
    print(f"Discharge production pump cost  = {Discharge_ProdPumping_Cost_Duty[1] / 1e6:6.2f} M$")
    print(f"Discharge injection pump cost   = {Discharge_InjPumping_Cost_Duty[1] / 1e6:6.2f} M$")
    print(f"Discharge flow line cost        = {Discharge_FlowLineCost / 1e6:6.2f} M$\n")
    print(f"Subsurface Capital Cost         = {SubsurfaceCapitalCost / 1e6:6.2f} M$")
    print(f"Subsurface O&M Cost             = {SubsurfaceOandMCost / 1e6:6.2f} M$\n")

    print("SURFACE COST RESULTS\n")
    print(f"Heat pump cost                  = {HP.total_cost / 1e6:6.2f} M$")
    print(f"Heat engine cost                = {HE.total_cost / 1e6:6.2f} M$\n")
    print(f"Surface capital cost            = {econ.surface_capital_cost / 1e6:6.2f} M$")
    print(f"Surface O&M cost                = {econ.OnM_surface / 1e6:6.2f} M$\n")

    print("TOTAL COST RESULTS\n")
    print(f"Total capital cost              = {econ.total_capital_cost / 1e6:6.2f} M$")
    print(f"LCOS                            = {econ.LCOS:6.2f} $/kWh-e")
    print(f"LCOH                            = {econ.LCOH:6.2f} $/kWh-th\n")
    print(f"Charging electricity cost       = {econ.charge_cost / 1e6:6.2f} M$")
    print(f"Discharging electricity revenue = {econ.discharge_revenue / 1e6:6.2f} M$")
    print(f"Net revenue                     = {econ.net_revenue / 1e6:6.2f} M$\n")

    formats = ["png"]

    Ccap = np.array(
        [
            Total_Exploration_Cost,
            FieldDevPlantPermitting,
            Total_Charge_Drilling_Cost,
            Charge_ProdPumping_Cost_Duty[1],
            Charge_InjPumping_Cost_Duty[1],
            Charge_FlowLineCost,
            Total_Discharge_Drilling_Cost,
            Discharge_ProdPumping_Cost_Duty[1],
            Discharge_InjPumping_Cost_Duty[1],
            Discharge_FlowLineCost,
            HP.total_cost,
            HE.total_cost,
        ]
    )
    xlab = [
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
        "Heat pump",
        "Heat engine",
    ]

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(np.arange(len(Ccap)), Ccap / 1e6)
    ax.set_xticks(np.arange(len(Ccap)))
    ax.set_xticklabels(xlab, rotation=45, ha="right")
    ax.set_ylabel("Capital cost, M$")
    ax.set_title("Capital cost breakdown")
    plt.tight_layout()
    fig.savefig(output_dir / "capital_cost.png", dpi=300)
    plt.close(fig)

    LCOS_mat = np.concatenate((Ccap * econ.FCR * 1e6, [econ.OnM_subsurface, econ.OnM_surface]))
    LCOS_mat = LCOS_mat / econ.Eout / 1e6
    xlab = [
        *xlab,
        "Subsurface O&M",
        "Surface O&M",
    ]

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(np.arange(len(LCOS_mat)), LCOS_mat)
    ax.set_xticks(np.arange(len(LCOS_mat)))
    ax.set_xticklabels(xlab, rotation=45, ha="right")
    ax.set_ylabel("LCOS, $/kWh-e")
    ax.set_title("LCOS contribution breakdown")
    plt.tight_layout()
    fig.savefig(output_dir / "LCOS.png", dpi=300)
    plt.close(fig)

    n = np.arange(hours, hours2)
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(n, gCTES.energy[n] / 1000)
    ax.set_xlim(0, hours)
    ax.set_title("Energy in cold storage")
    ax.set_xlabel("Hour of the year")
    ax.set_ylabel("Energy in cold storage, GWh-th")
    plt.tight_layout()
    fig.savefig(output_dir / "Cold_geoTES_SOC.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(n, gHTES.energy[n] / 1000)
    ax.set_xlim(0, hours)
    ax.set_title("Energy in hot storage")
    ax.set_xlabel("Hour of the year")
    ax.set_ylabel("Energy in hot storage, GWh-th")
    plt.tight_layout()
    fig.savefig(output_dir / "Hot_geoTES_SOC.png", dpi=300)
    plt.close(fig)

    n1 = np.arange(hours + 24 * 27 - 1, hours + 24 * 31 + 1)
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(n1, HP.Win[n1], label="Heat pump power input")
    ax.plot(n1, HE.Wout[n1], label="Heat engine power output")
    ax.plot(n1, gHTES.power[n1], label="Heat to hot geoTES")
    ax.set_title("January 27")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Energy, MWh")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.3), ncol=2)
    plt.tight_layout()
    fig.savefig(output_dir / "January_energy.png", dpi=300)
    plt.close(fig)

    day_jun1 = datetime(2022, 6, 1).timetuple().tm_yday
    day_jun4 = datetime(2022, 6, 4).timetuple().tm_yday
    n2 = np.arange(hours + 24 * day_jun1 - 1, hours + 24 * day_jun4 + 1)
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(n2, HP.Win[n2], label="Heat pump power input")
    ax.plot(n2, HE.Wout[n2], label="Heat engine power output")
    ax.plot(n2, gHTES.power[n2], label="Heat to hot geoTES")
    ax.set_title("June 4")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Energy, MWh")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.3), ncol=2)
    plt.tight_layout()
    fig.savefig(output_dir / "June_energy.png", dpi=300)
    plt.close(fig)

    jan_prices_start = hours + 24 * 27 - 1
    jan_prices_end = hours + 24 * 31 + 1
    n3 = np.arange(jan_prices_start, jan_prices_end)
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(n3, econ.charge_cost_hourly[n3], label="Charge cost")
    ax.plot(n3, econ.discharge_revenue_hourly[n3], label="Discharge revenue")
    ax.set_title("January 27")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Price, $")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.3), ncol=2)
    plt.tight_layout()
    fig.savefig(output_dir / "January_prices.png", dpi=300)
    plt.close(fig)

    n4 = np.arange(hours + 24 * day_jun1 - 1, hours + 24 * day_jun4 + 1)
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(n4, econ.charge_cost_hourly[n4], label="Charge cost")
    ax.plot(n4, econ.discharge_revenue_hourly[n4], label="Discharge revenue")
    ax.set_title("June 4")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Price, $")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.3), ncol=2)
    plt.tight_layout()
    fig.savefig(output_dir / "June_prices.png", dpi=300)
    plt.close(fig)

    n5 = np.arange(0, hours)
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(n5, econ.elec_price_hourly[n5])
    ax.set_xlim(0, hours)
    ax.set_title("Electricity price")
    ax.set_xlabel("Hour of the year")
    ax.set_ylabel("Electricity price, $/MWh")
    plt.tight_layout()
    fig.savefig(output_dir / "electricity_prices.png", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
