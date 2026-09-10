from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

try:
    from scipy.io import loadmat
except ImportError:
    loadmat = None

from thermo_cycle_class import thermo_cycle_class
from geoTES_class import geoTES_class
from economics_class import economics_class
from ExplorationCost import ExplorationCost
from DrillingCost import DrillingCost
from ProductionPumpingCost import ProductionPumpingCost
from InjectionPumpingCost import InjectionPumpingCost

PROJECT_ROOT = Path(__file__).resolve().parent


def read_csv_column(path: Path, column_index: int, skip_rows: int) -> np.ndarray:
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return np.genfromtxt(path, delimiter=",", skip_header=skip_rows, usecols=[column_index])


def load_electricity_prices(location: str, year: int) -> np.ndarray:
    if location == "Imperial CA":
        if loadmat is None:
            raise ImportError("scipy is required to read MAT files for Imperial CA prices")
        mat_data = loadmat(PROJECT_ROOT / "data" / "caliPrices.mat")
        return np.ravel(mat_data["cali"]["margCost"])[0]

    if location == "Elk Hills CA":
        if year == 2020:
            raise ValueError("Elk Hills 2020 price data not available")
        file_name = "2021_CAIOS_EK_DA.csv" if year == 2021 else "2022_CAIOS_EK_DA.csv"
        return read_csv_column(PROJECT_ROOT / "data" / file_name, column_index=1, skip_rows=1)

    if location == "ERCOT West":
        if year == 2022:
            raise ValueError("ERCOT West 2022 price data not available")
        file_name = "2020_PECO__DA.csv" if year == 2020 else "2021_PECO__DA.csv"
        return read_csv_column(PROJECT_ROOT / "data" / file_name, column_index=1, skip_rows=1)

    raise ValueError(f"Unsupported location: {location}")


def load_ambient_temperature(location: str) -> np.ndarray:
    if location == "Imperial CA":
        return read_csv_column(
            PROJECT_ROOT / "data" / "imperial_ca_32.835205_-115.572398_psmv3_60_tmy.csv",
            column_index=9,
            skip_rows=3,
        )
    if location == "Elk Hills CA":
        return read_csv_column(
            PROJECT_ROOT / "data" / "Elk_Hills_tmy-2021.csv",
            column_index=11,
            skip_rows=3,
        )
    if location == "ERCOT West":
        return read_csv_column(
            PROJECT_ROOT / "data" / "ERCOT_West_tmy-2021.csv",
            column_index=11,
            skip_rows=3,
        )
    raise ValueError(f"Data file for suggested location not found: {location}")


def save_fig(fig: plt.Figure, filename: str, formats: list[str]) -> None:
    for fmt in formats:
        fig.savefig(f"{filename}.{fmt}", bbox_inches="tight")


def run_GeoTES_TEA_v2() -> np.ndarray:
    save_figs = 0
    location = "Elk Hills CA"
    year = 2021
    nY = 3

    HE_type = "HE"
    HE_design = {
        "Wout": 100.0,
        "T0": 15.0,
        "eff": 0.11,
        "TIT": -1.0,
        "Qin": -1.0,
        "fan": 0.0,
    }
    HE_foff = PROJECT_ROOT / "data" / "example_off_design_v1.xlsx"
    HE_cost = {"power_block": 1000.0, "HX": 0.0}
    HE = thermo_cycle_class(HE_type, HE_design, str(HE_foff), HE_cost)

    HP_type = "HP"
    HP_design = {
        "Win": 250.0,
        "T0": 15.0,
        "COP": 3.7,
        "COT": -1.0,
        "Qout": -1.0,
        "fan": 0.0,
    }
    HP_foff = PROJECT_ROOT / "data" / "example_off_design_HP_v1.xlsx"
    HP_cost = {"power_block": 1000.0, "HX": 0.0}
    HP = thermo_cycle_class(HP_type, HP_design, str(HP_foff), HP_cost)

    HE.Qout0 = HE.Qin0 / (HP.Qout0 / HP.Qin0)

    CB = {"Tmax": 158.8, "Tmin": 20.0}
    CB["RTeff"] = HE.eff0 * HP.COP0

    gCTES_recovery = 0.95
    gCTES_Tinit = 50.0
    gCTES_flowrate = {"P": 60.0, "I": 60.0}
    gCTES_Qmax = 10000.0
    gCTES_props = {
        "rho": 2000.0,
        "cp": 800.0,
        "void": 0.32,
        "depth": 500.0,
        "thickness": 100.0,
    }
    gCTES_fluid = "water"
    gCTES_mode = "push-pull"
    gCTES = geoTES_class(
        gCTES_recovery,
        gCTES_Tinit,
        gCTES_flowrate["P"],
        gCTES_Qmax,
        gCTES_props,
        gCTES_fluid,
    )
    gCTES.mode = gCTES_mode
    gCTES.flowrate_per_well_prod = gCTES_flowrate["P"]
    gCTES.flowrate_per_well_inj = gCTES_flowrate["I"]

    gHTES_recovery = 0.95
    gHTES_Tinit = 50.0
    gHTES_flowrate = {"P": 60.0, "I": 60.0}
    gHTES_Qmax = 1000.0
    gHTES_props = {
        "rho": 2000.0,
        "cp": 800.0,
        "void": 0.32,
        "depth": 500.0,
        "thickness": 100.0,
    }
    gHTES_fluid = "water"
    gHTES_mode = "push-pull"
    gHTES = geoTES_class(
        gHTES_recovery,
        gHTES_Tinit,
        gHTES_flowrate["P"],
        gHTES_Qmax,
        gHTES_props,
        gHTES_fluid,
    )
    gHTES.mode = gHTES_mode
    gHTES.flowrate_per_well_prod = gHTES_flowrate["P"]
    gHTES.flowrate_per_well_inj = gHTES_flowrate["I"]

    finance = {
        "lifetime": 30,
        "elec_price": 0.025,
        "inflation": 0.025,
        "irr": 0.10,
        "debt_frac": 0.60,
        "debt_IR": 0.08,
        "tax_rate": 0.28,
        "deprec": [0.20, 0.32, 0.20, 0.14, 0.14],
        "annual_cost": [1.0, 0.0, 0.0],
        "construc_IR": 0.0,
        "OnM": 0.02,
        "ITC": 0.0,
    }
    econ = economics_class(finance)

    econ.elec_price_hourly = load_electricity_prices(location, year)
    econ.median_price = float(np.median(econ.elec_price_hourly))
    econ.charge_price = 0.9999 * econ.median_price
    econ.discharge_price = 1.0001 * econ.median_price

    Tamb = load_ambient_temperature(location)
    hours = 8760
    n_hours = nY * hours

    HE.Tamb = np.tile(Tamb, nY)
    HP.Tamb = np.tile(Tamb, nY)
    elec_prices = np.tile(econ.elec_price_hourly, nY)

    HE.Win = np.zeros(n_hours, dtype=float)
    HE.Wout = np.zeros(n_hours, dtype=float)
    HE.Qin = np.zeros(n_hours, dtype=float)
    HE.Qout = np.zeros(n_hours, dtype=float)
    HE.eff = np.zeros(n_hours, dtype=float)
    HE.COP = np.zeros(n_hours, dtype=float)
    HE.Tamb = HE.Tamb.copy()

    HP.Win = np.zeros(n_hours, dtype=float)
    HP.Wout = np.zeros(n_hours, dtype=float)
    HP.Qin = np.zeros(n_hours, dtype=float)
    HP.Qout = np.zeros(n_hours, dtype=float)
    HP.eff = np.zeros(n_hours, dtype=float)
    HP.COP = np.zeros(n_hours, dtype=float)
    HP.Tamb = HP.Tamb.copy()

    gCTES.power = np.zeros(n_hours, dtype=float)
    gCTES.energy = np.zeros(n_hours, dtype=float)
    gHTES.power = np.zeros(n_hours, dtype=float)
    gHTES.energy = np.zeros(n_hours, dtype=float)

    dT = 1.0

    gCTES.charge_production.T = gCTES.Tinit
    gCTES.charge_production.p = 10.0
    gCTES.charge_production.calc_fluid_props("pT")

    gCTES.charge_injection.T = CB["Tmin"]
    gCTES.charge_injection.p = 30.0
    gCTES.charge_injection.calc_fluid_props("pT")

    gHTES.charge_production.T = gHTES.Tinit
    gHTES.charge_production.p = 10.0
    gHTES.charge_production.calc_fluid_props("pT")

    gHTES.charge_injection.T = CB["Tmax"]
    gHTES.charge_injection.q = 0.0
    gHTES.charge_injection.calc_fluid_props("qT")
    if gHTES.charge_injection.p < 30.0:
        gHTES.charge_injection.p = 30.0
        gHTES.charge_injection.calc_fluid_props("pT")

    gCTES.discharge_production.T = CB["Tmin"]
    gCTES.discharge_production.p = 10.0
    gCTES.discharge_production.calc_fluid_props("pT")

    gCTES.discharge_injection.T = gCTES.Tinit
    gCTES.discharge_injection.p = 30.0
    gCTES.discharge_injection.calc_fluid_props("pT")

    gHTES.discharge_production.T = CB["Tmax"]
    gHTES.discharge_production.q = 0.0
    gHTES.discharge_production.calc_fluid_props("qT")
    if gHTES.discharge_production.p < 30.0:
        gHTES.discharge_production.p = 30.0
        gHTES.discharge_production.calc_fluid_props("pT")

    gHTES.discharge_injection.T = gHTES.Tinit
    gHTES.discharge_injection.p = 30.0
    gHTES.discharge_injection.calc_fluid_props("pT")

    for i in range(1, n_hours):
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

    Ncold_source_well = max(gCTES.charge_prod_Nwell, gCTES.discharge_inj_Nwell)
    Cold_source_Drilling_Cost = DrillingCost(
        Ncold_source_well,
        0,
        gCTES.depth,
        200,
        "Small",
        1,
        1.5,
        "Deviated",
        "Liner",
    )
    Cold_source_Well_Cost = Cold_source_Drilling_Cost.well_cost()
    Total_Cold_source_Drilling_Cost = Cold_source_Drilling_Cost.total_dc(Cold_source_Well_Cost)

    ResTemp = gCTES.Tinit
    Pflowrate = gCTES.flowrate_per_well_prod * gCTES.charge_production.rho / 1000.0
    Cold_source_ProdPumping_Estimation = ProductionPumpingCost(
        ResTemp,
        Pflowrate,
        gCTES.charge_prod_Nwell,
        6370,
        gCTES.depth,
        200,
        "Small",
        "Lineshaft",
        "Liner",
        1.553,
    )
    Step1 = Cold_source_ProdPumping_Estimation.head_prod_top()
    Step2 = Cold_source_ProdPumping_Estimation.head_suction(Step1)
    Step3 = Cold_source_ProdPumping_Estimation.suction_depth(Step2)
    Step4 = Cold_source_ProdPumping_Estimation.casing_friction(Step3, Step1)
    Step5 = Cold_source_ProdPumping_Estimation.pump_power(Step3, Step4)
    Step6 = Cold_source_ProdPumping_Estimation.pump_cost(Step5, Step3)
    Cold_source_ProdPumping_Cost_Duty = Cold_source_ProdPumping_Estimation.total_pump_duty_cost(Step5, Step6)

    InjTemp = gCTES.Tinit
    Iflowrate = gCTES.flowrate_per_well_inj * gCTES.discharge_injection.rho / 1000.0
    PressureThermalSource = gCTES.discharge_injection.p * 14.5038
    Cold_source_InjPumping_Estimation = InjectionPumpingCost(
        ResTemp,
        InjTemp,
        Iflowrate,
        Pflowrate,
        PressureThermalSource,
        gCTES.discharge_inj_Nwell,
        7645,
        gCTES.depth,
        200,
        "Small",
        "Liner",
        1.533,
        "Charge",
    )
    Step7 = Cold_source_InjPumping_Estimation.head_suction()
    Step8 = Cold_source_InjPumping_Estimation.head_injection(Step7)
    Step9 = Cold_source_InjPumping_Estimation.pump_power(Step8)
    Step10 = Cold_source_InjPumping_Estimation.pump_cost(Step9)
    Cold_source_InjPumping_Cost_Duty = Cold_source_InjPumping_Estimation.total_pump_duty_cost(Step9, Step10)

    LengthofFlowline = 300.0
    PipingUnitCost = 256.98
    TotalNumberofWells = Ncold_source_well
    Cold_source_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * TotalNumberofWells

    Cold_source_WellFieldMaintenance = 0.015 * (Total_Cold_source_Drilling_Cost + Cold_source_FlowLineCost)
    Cold_source_PumpMaintenance = Cold_source_ProdPumping_Estimation.pump_maintenance_cost(Step3, Step6)
    NumberProductionWells = Ncold_source_well
    ProductionRateperWell = Pflowrate
    MakeupWaterUnitCost = 0.65
    SubsurfaceWaterLoss = 0.001
    Cold_source_MakeupWaterSubsurface = (
        MakeupWaterUnitCost
        * NumberProductionWells
        * (ProductionRateperWell * 18.0917 * 34.2857 * 365.0)
        * SubsurfaceWaterLoss
    )

    Ncold_sink_well = max(gCTES.discharge_prod_Nwell, gCTES.charge_inj_Nwell)
    Cold_sink_Drilling_Cost = DrillingCost(
        Ncold_sink_well,
        0,
        gCTES.depth,
        200,
        "Small",
        1,
        1.5,
        "Deviated",
        "Liner",
    )
    Cold_sink_Well_Cost = Cold_sink_Drilling_Cost.well_cost()
    Total_Cold_sink_Drilling_Cost = Cold_sink_Drilling_Cost.total_dc(Cold_sink_Well_Cost)

    ResTemp = CB["Tmin"]
    Pflowrate = gCTES.flowrate_per_well_prod * gCTES.discharge_production.rho / 1000.0
    Cold_sink_ProdPumping_Estimation = ProductionPumpingCost(
        ResTemp,
        Pflowrate,
        gCTES.discharge_prod_Nwell,
        6370,
        gCTES.depth,
        200,
        "Small",
        "Lineshaft",
        "Liner",
        1.553,
    )
    Step1 = Cold_sink_ProdPumping_Estimation.head_prod_top()
    Step2 = Cold_sink_ProdPumping_Estimation.head_suction(Step1)
    Step3 = Cold_sink_ProdPumping_Estimation.suction_depth(Step2)
    Step4 = Cold_sink_ProdPumping_Estimation.casing_friction(Step3, Step1)
    Step5 = Cold_sink_ProdPumping_Estimation.pump_power(Step3, Step4)
    Step6 = Cold_sink_ProdPumping_Estimation.pump_cost(Step5, Step3)
    Cold_sink_ProdPumping_Cost_Duty = Cold_sink_ProdPumping_Estimation.total_pump_duty_cost(Step5, Step6)

    InjTemp = CB["Tmin"]
    Iflowrate = gCTES.flowrate_per_well_inj * gCTES.charge_injection.rho / 1000.0
    PressureThermalSource = gCTES.charge_injection.p * 14.5038
    Cold_sink_InjPumping_Estimation = InjectionPumpingCost(
        ResTemp,
        InjTemp,
        Iflowrate,
        Pflowrate,
        PressureThermalSource,
        gCTES.discharge_inj_Nwell,
        7645,
        gCTES.depth,
        200,
        "Small",
        "Liner",
        1.533,
        "Charge",
    )
    Step7 = Cold_sink_InjPumping_Estimation.head_suction()
    Step8 = Cold_sink_InjPumping_Estimation.head_injection(Step7)
    Step9 = Cold_sink_InjPumping_Estimation.pump_power(Step8)
    Step10 = Cold_sink_InjPumping_Estimation.pump_cost(Step9)
    Cold_sink_InjPumping_Cost_Duty = Cold_sink_InjPumping_Estimation.total_pump_duty_cost(Step9, Step10)

    Cold_sink_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * Ncold_sink_well
    Cold_sink_WellFieldMaintenance = 0.015 * (Total_Cold_sink_Drilling_Cost + Cold_sink_FlowLineCost)
    Cold_sink_PumpMaintenance = Cold_sink_ProdPumping_Estimation.pump_maintenance_cost(Step3, Step6)
    Cold_sink_MakeupWaterSubsurface = (
        MakeupWaterUnitCost
        * Ncold_sink_well
        * (ProductionRateperWell * 18.0917 * 34.2857 * 365.0)
        * SubsurfaceWaterLoss
    )

    Nhot_source_well = max(gHTES.charge_prod_Nwell, gHTES.discharge_inj_Nwell)
    Hot_source_Drilling_Cost = DrillingCost(
        Nhot_source_well,
        0,
        gHTES.depth,
        200,
        "Small",
        1,
        1.5,
        "Deviated",
        "Liner",
    )
    Hot_source_Well_Cost = Hot_source_Drilling_Cost.well_cost()
    Total_Hot_source_Drilling_Cost = Hot_source_Drilling_Cost.total_dc(Hot_source_Well_Cost)

    ResTemp = gHTES.Tinit
    Pflowrate = gHTES.flowrate_per_well_prod * gHTES.charge_production.rho / 1000.0
    Hot_source_ProdPumping_Estimation = ProductionPumpingCost(
        ResTemp,
        Pflowrate,
        gHTES.charge_prod_Nwell,
        6370,
        gHTES.depth,
        200,
        "Small",
        "Lineshaft",
        "Liner",
        1.553,
    )
    Step1 = Hot_source_ProdPumping_Estimation.head_prod_top()
    Step2 = Hot_source_ProdPumping_Estimation.head_suction(Step1)
    Step3 = Hot_source_ProdPumping_Estimation.suction_depth(Step2)
    Step4 = Hot_source_ProdPumping_Estimation.casing_friction(Step3, Step1)
    Step5 = Hot_source_ProdPumping_Estimation.pump_power(Step3, Step4)
    Step6 = Hot_source_ProdPumping_Estimation.pump_cost(Step5, Step3)
    Hot_source_ProdPumping_Cost_Duty = Hot_source_ProdPumping_Estimation.total_pump_duty_cost(Step5, Step6)

    InjTemp = gHTES.Tinit
    Iflowrate = gHTES.flowrate_per_well_inj * gHTES.discharge_injection.rho / 1000.0
    PressureThermalSource = gHTES.discharge_injection.p * 14.5038
    Hot_source_InjPumping_Estimation = InjectionPumpingCost(
        ResTemp,
        InjTemp,
        Iflowrate,
        Pflowrate,
        PressureThermalSource,
        gHTES.discharge_inj_Nwell,
        7645,
        gHTES.depth,
        200,
        "Small",
        "Liner",
        1.533,
        "Charge",
    )
    Step7 = Hot_source_InjPumping_Estimation.head_suction()
    Step8 = Hot_source_InjPumping_Estimation.head_injection(Step7)
    Step9 = Hot_source_InjPumping_Estimation.pump_power(Step8)
    Step10 = Hot_source_InjPumping_Estimation.pump_cost(Step9)
    Hot_source_InjPumping_Cost_Duty = Hot_source_InjPumping_Estimation.total_pump_duty_cost(Step9, Step10)

    Hot_source_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * Nhot_source_well
    Hot_source_WellFieldMaintenance = 0.015 * (Total_Hot_source_Drilling_Cost + Hot_source_FlowLineCost)
    Hot_source_PumpMaintenance = Hot_source_ProdPumping_Estimation.pump_maintenance_cost(Step3, Step6)
    Hot_source_MakeupWaterSubsurface = (
        MakeupWaterUnitCost
        * Nhot_source_well
        * (ProductionRateperWell * 18.0917 * 34.2857 * 365.0)
        * SubsurfaceWaterLoss
    )

    Nhot_sink_well = max(gHTES.discharge_prod_Nwell, gHTES.charge_inj_Nwell)
    Hot_sink_Drilling_Cost = DrillingCost(
        Nhot_sink_well,
        0,
        gHTES.depth,
        200,
        "Small",
        1,
        1.5,
        "Deviated",
        "Liner",
    )
    Hot_sink_Well_Cost = Hot_sink_Drilling_Cost.well_cost()
    Total_Hot_sink_Drilling_Cost = Hot_sink_Drilling_Cost.total_dc(Hot_sink_Well_Cost)

    ResTemp = CB["Tmax"]
    Pflowrate = gHTES.flowrate_per_well_prod * gHTES.discharge_production.rho / 1000.0
    Hot_sink_ProdPumping_Estimation = ProductionPumpingCost(
        ResTemp,
        Pflowrate,
        gHTES.discharge_prod_Nwell,
        6370,
        gHTES.depth,
        200,
        "Small",
        "Lineshaft",
        "Liner",
        1.553,
    )
    Step1 = Hot_sink_ProdPumping_Estimation.head_prod_top()
    Step2 = Hot_sink_ProdPumping_Estimation.head_suction(Step1)
    Step3 = Hot_sink_ProdPumping_Estimation.suction_depth(Step2)
    Step4 = Hot_sink_ProdPumping_Estimation.casing_friction(Step3, Step1)
    Step5 = Hot_sink_ProdPumping_Estimation.pump_power(Step3, Step4)
    Step6 = Hot_sink_ProdPumping_Estimation.pump_cost(Step5, Step3)
    Hot_sink_ProdPumping_Cost_Duty = Hot_sink_ProdPumping_Estimation.total_pump_duty_cost(Step5, Step6)

    InjTemp = CB["Tmax"]
    Iflowrate = gHTES.flowrate_per_well_inj * gHTES.charge_injection.rho / 1000.0
    PressureThermalSource = gHTES.charge_injection.p * 14.5038
    Hot_sink_InjPumping_Estimation = InjectionPumpingCost(
        ResTemp,
        InjTemp,
        Iflowrate,
        Pflowrate,
        PressureThermalSource,
        gHTES.charge_inj_Nwell,
        7645,
        gHTES.depth,
        200,
        "Small",
        "Liner",
        1.533,
        "Charge",
    )
    Step7 = Hot_sink_InjPumping_Estimation.head_suction()
    Step8 = Hot_sink_InjPumping_Estimation.head_injection(Step7)
    Step9 = Hot_sink_InjPumping_Estimation.pump_power(Step8)
    Step10 = Hot_sink_InjPumping_Estimation.pump_cost(Step9)
    Hot_sink_InjPumping_Cost_Duty = Hot_sink_InjPumping_Estimation.total_pump_duty_cost(Step9, Step10)

    Hot_sink_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * Nhot_sink_well
    Hot_sink_WellFieldMaintenance = 0.015 * (Total_Hot_sink_Drilling_Cost + Hot_sink_FlowLineCost)
    Hot_sink_PumpMaintenance = Hot_sink_ProdPumping_Estimation.pump_maintenance_cost(Step3, Step6)
    Hot_sink_MakeupWaterSubsurface = (
        MakeupWaterUnitCost
        * Nhot_sink_well
        * (ProductionRateperWell * 18.0917 * 34.2857 * 365.0)
        * SubsurfaceWaterLoss
    )

    SubsurfaceCapitalCost = (
        Total_Exploration_Cost
        + FieldDevPlantPermitting
        + Total_Hot_source_Drilling_Cost
        + Hot_source_ProdPumping_Cost_Duty[1]
        + Hot_source_InjPumping_Cost_Duty[1]
        + Hot_source_FlowLineCost
        + Total_Hot_sink_Drilling_Cost
        + Hot_sink_ProdPumping_Cost_Duty[1]
        + Hot_sink_InjPumping_Cost_Duty[1]
        + Hot_sink_FlowLineCost
        + Total_Cold_source_Drilling_Cost
        + Cold_source_ProdPumping_Cost_Duty[1]
        + Cold_source_InjPumping_Cost_Duty[1]
        + Cold_source_FlowLineCost
        + Total_Cold_sink_Drilling_Cost
        + Cold_sink_ProdPumping_Cost_Duty[1]
        + Cold_sink_InjPumping_Cost_Duty[1]
        + Cold_sink_FlowLineCost
    )
    AnnualTaxandInsurance = 0.0075 * SubsurfaceCapitalCost

    SubsurfaceOandMCost = (
        Hot_source_WellFieldMaintenance
        + Hot_source_PumpMaintenance
        + Hot_source_MakeupWaterSubsurface
        + Hot_sink_WellFieldMaintenance
        + Hot_sink_PumpMaintenance
        + Hot_sink_MakeupWaterSubsurface
        + Cold_source_WellFieldMaintenance
        + Cold_source_PumpMaintenance
        + Cold_source_MakeupWaterSubsurface
        + Cold_sink_WellFieldMaintenance
        + Cold_sink_PumpMaintenance
        + Cold_sink_MakeupWaterSubsurface
        + AnnualTaxandInsurance
    )

    econ.subsurface_capital_cost = SubsurfaceCapitalCost
    econ.OnM_subsurface = SubsurfaceOandMCost
    econ.surface_capital_cost = HE.total_cost + HP.total_cost
    econ.OnM_surface = econ.OnM * econ.surface_capital_cost

    charging_hours = int(np.count_nonzero(HP.Win[(nY - 1) * hours : nY * hours] > 0))
    discharging_hours = int(np.count_nonzero(HE.Wout[(nY - 1) * hours : nY * hours] > 0))

    cold_charge_production_pump = charging_hours * Cold_source_ProdPumping_Cost_Duty[0] / 1e6
    cold_charge_injection_pump = charging_hours * Cold_sink_InjPumping_Cost_Duty[0] / 1e6
    hot_charge_production_pump = charging_hours * Hot_source_ProdPumping_Cost_Duty[0] / 1e6
    hot_charge_injection_pump = charging_hours * Hot_sink_InjPumping_Cost_Duty[0] / 1e6

    cold_discharge_production_pump = discharging_hours * Cold_sink_ProdPumping_Cost_Duty[0] / 1e6
    cold_discharge_injection_pump = discharging_hours * Cold_source_InjPumping_Cost_Duty[0] / 1e6
    hot_discharge_production_pump = discharging_hours * Hot_sink_ProdPumping_Cost_Duty[0] / 1e6
    hot_discharge_injection_pump = discharging_hours * Hot_source_InjPumping_Cost_Duty[0] / 1e6

    econ.Ein = (
        HP.Win_tot
        + cold_charge_production_pump
        + cold_charge_injection_pump
        + hot_charge_injection_pump
        + hot_charge_production_pump
    )
    econ.Eout = (
        HE.Wout_tot
        - cold_discharge_production_pump
        - cold_discharge_injection_pump
        - hot_discharge_injection_pump
        - hot_discharge_production_pump
    )
    CB["RTeff_real"] = econ.Eout / econ.Ein if econ.Ein != 0 else np.nan

    econ.calc_fcr()
    econ.calc_revenue(
        HP.Win[(nY - 1) * hours : nY * hours],
        HE.Wout[(nY - 1) * hours : nY * hours],
    )
    econ.calc_levelized_cost("S")

    Ccap = np.array(
        [
            Total_Exploration_Cost,
            FieldDevPlantPermitting,
            Total_Hot_source_Drilling_Cost,
            Hot_source_ProdPumping_Cost_Duty[1],
            Hot_source_InjPumping_Cost_Duty[1],
            Hot_source_FlowLineCost,
            Total_Hot_sink_Drilling_Cost,
            Hot_sink_ProdPumping_Cost_Duty[1],
            Hot_sink_InjPumping_Cost_Duty[1],
            Hot_sink_FlowLineCost,
            Total_Cold_source_Drilling_Cost,
            Cold_source_ProdPumping_Cost_Duty[1],
            Cold_source_InjPumping_Cost_Duty[1],
            Cold_source_FlowLineCost,
            Total_Cold_sink_Drilling_Cost,
            Cold_sink_ProdPumping_Cost_Duty[1],
            Cold_sink_InjPumping_Cost_Duty[1],
            Cold_sink_FlowLineCost,
            HE.total_cost,
            HP.total_cost,
        ],
        dtype=float,
    )

    LCOS_mat = np.array(
        [
            Ccap * econ.FCR / 1e6,
            econ.OnM_subsurface / 1e6,
            econ.OnM_surface / 1e6,
            econ.elec_cost / 1e6,
        ]
    )

    GeoTES_output = np.array(
        [
            econ.LCOS,
            econ.Ein,
            econ.Eout,
            CB["RTeff"],
            CB["RTeff_real"],
            Total_Exploration_Cost,
            FieldDevPlantPermitting,
            SubsurfaceCapitalCost,
            SubsurfaceOandMCost,
            econ.total_capital_cost,
            econ.OnM_total,
        ],
        dtype=float,
    )

    if save_figs == 1:
        formats = ["svg", "png"]
        fig1 = plt.figure(1)
        plt.bar(np.arange(len(Ccap)), Ccap / 1e6)
        plt.xticks(np.arange(len(Ccap)))
        plt.ylabel("Capital cost, M$")
        save_fig(fig1, PROJECT_ROOT / "Outputs" / "capital_cost", formats)
        plt.close(fig1)

        fig2 = plt.figure(2)
        plt.bar(np.arange(LCOS_mat.shape[1]), LCOS_mat[0, :])
        plt.ylabel("LCOS, $/kWh-e")
        save_fig(fig2, PROJECT_ROOT / "Outputs" / "LCOS", formats)
        plt.close(fig2)

    return GeoTES_output


def main() -> None:
    results = run_GeoTES_TEA_v2()
    print("CB_geoTES_v2 results:")
    print(results)


if __name__ == "__main__":
    main()
