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
    if not Path(path).is_absolute():
        path = PROJECT_ROOT / path
    return np.genfromtxt(path, delimiter=",", skip_header=skip_rows, usecols=[column_index])


def load_electricity_prices(location: str, year: int) -> np.ndarray:
    if location == "Imperial CA":
        if loadmat is None:
            raise ImportError("scipy is required to read MAT files for Imperial CA prices")
        mat_data = loadmat(PROJECT_ROOT / "data" / "caliPrices.mat")
        return np.asarray(mat_data["cali"]["margCost"]).ravel()

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


def run_GeoTES_TEA_R125(input1: float, input2: float) -> np.ndarray:
    write_out = 0
    save_figs = 0

    location = "ERCOT West"
    year = 2021
    nY = 3
    recov_fac = 0.95

    HE_type = "HE"
    HE_design = {
        "Wout": 10.0,
        "T0": 25.0,
        "eff": 0.177,
        "TIT": -1.0,
        "Qin": -1.0,
        "fan": input1 * 0.30875 / 25.416,
        "Qrej": 10.0 * 27.442 / 25.416,
    }
    HE_foff = PROJECT_ROOT / "data" / "example_off_design_v1.xlsx"
    HE_cost = {"power_block": 1000.0, "HX": 50.0, "fan": 500.0}
    HE = thermo_cycle_class(HE_type, HE_design, str(HE_foff), HE_cost)
    HE.fan0 = HE_design["fan"]

    HP_type = "HP"
    HPmult = 1.0
    HP_design = {
        "COP": 2.9,
        "Win": HPmult * 22.836,
        "T0": 25.0,
        "COT": -1.0,
        "Qout": -1.0,
        "fan": 0.0,
        "Qrej": 0.0,
    }
    HP_foff = PROJECT_ROOT / "data" / "example_off_design_HP_v1.xlsx"
    HP_cost = {"power_block": 1000.0, "HX": 0.0, "fan": 0.0}
    HP = thermo_cycle_class(HP_type, HP_design, str(HP_foff), HP_cost)

    # Adjust HE.Qout0 to account for heat rejection to environment, following MATLAB logic.
    HE.Qout0 = HE.Qin0 / (HP.Qout0 / HP.Qin0)

    CB = {"Tmax": 162.2, "Tmin": 5.0}
    CB["RTeff"] = HE.eff0 * HP.COP0

    gCTES_recovery = recov_fac
    gCTES_Tinit = 25.0
    gCTES_flowrate = {"P": 100.0, "I": 100.0}
    gCTES_Qmax = 10000.0
    gCTES_props = {
        "rho": 2000.0,
        "cp": 710.0,
        "void": 0.3,
        "depth": 1000.0,
        "thickness": 100.0,
        "productivity": input2,
        "injectivity": input2,
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
    gCTES.depth = gCTES_props["depth"]
    gCTES.thickness = gCTES_props["thickness"]
    gCTES.productivity = gCTES_props["productivity"]
    gCTES.injectivity = gCTES_props["injectivity"]

    gHTES_recovery = recov_fac
    gHTES_Tinit = 50.0
    gHTES_flowrate = {"P": 100.0, "I": 100.0}
    gHTES_Qmax = 10000.0
    gHTES_props = {
        "rho": 2000.0,
        "cp": 710.0,
        "void": 0.3,
        "depth": 1000.0,
        "thickness": 100.0,
        "productivity": input2,
        "injectivity": input2,
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
    gHTES.depth = gHTES_props["depth"]
    gHTES.thickness = gHTES_props["thickness"]
    gHTES.productivity = gHTES_props["productivity"]
    gHTES.injectivity = gHTES_props["injectivity"]

    finance = {
        "lifetime": 30,
        "elec_price": 0.025,
        "inflation": 0.025,
        "irr": 0.10,
        "debt_frac": 0.60,
        "debt_IR": 0.08,
        "tax_rate": 0.2984,
        "deprec": [0.20, 0.32, 0.20, 0.14, 0.14],
        "annual_cost": [1.0, 0.0, 0.0],
        "construc_IR": 0.0,
        "OnM": 0.015,
        "ITC": 0.40,
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

    gCTES.charge_production.T = gCTES.Tinit
    gCTES.charge_production.p = 2.0
    gCTES.charge_production.calc_fluid_props("pT")

    gCTES.charge_injection.T = CB["Tmin"]
    gCTES.charge_injection.p = 2.0
    gCTES.charge_injection.calc_fluid_props("pT")

    gHTES.charge_production.T = gHTES.Tinit
    gHTES.charge_production.p = 7.0
    gHTES.charge_production.calc_fluid_props("pT")

    gHTES.charge_injection.T = CB["Tmax"]
    gHTES.charge_injection.q = 0.0
    gHTES.charge_injection.calc_fluid_props("qT")

    gCTES.discharge_production.T = CB["Tmin"]
    gCTES.discharge_production.p = 2.0
    gCTES.discharge_production.calc_fluid_props("pT")

    gCTES.discharge_injection.T = gCTES.Tinit
    gCTES.discharge_injection.p = 2.0
    gCTES.discharge_injection.calc_fluid_props("pT")

    gHTES.discharge_production.T = CB["Tmax"]
    gHTES.discharge_production.q = 0.0
    gHTES.discharge_production.calc_fluid_props("qT")

    gHTES.discharge_injection.T = gHTES.Tinit
    gHTES.discharge_injection.p = gHTES.discharge_production.p
    gHTES.discharge_injection.calc_fluid_props("pT")

    if HPmult >= 1.0:
        Ndis = 12
        Nchg = int(np.ceil(Ndis / HPmult))
        Nstr = 24 - Ndis - Nchg
        ophour = np.concatenate((np.ones(Ndis, dtype=float), -np.ones(Nchg, dtype=float), np.zeros(Nstr, dtype=float)))
    else:
        Nchg = int(np.ceil(24.0 / (HPmult + 1.0)))
        Ndis = 24 - Nchg
        ophour = np.concatenate((np.ones(Ndis, dtype=float), -np.ones(Nchg, dtype=float)))

    opmode = "hour"
    hour = 1  # 0-based indexing: MATLAB starts at 2 and wraps to 1, so Python starts at index 1

    for i in range(1, n_hours):
        gCTES.energy[i] = gCTES.energy[i - 1]
        gHTES.energy[i] = gHTES.energy[i - 1]

        if opmode == "price":
            if elec_prices[i] <= econ.charge_price:
                dispatch = -1.0
            elif elec_prices[i] > econ.discharge_price:
                dispatch = 1.0
            else:
                dispatch = 0.0
        else:
            dispatch = ophour[hour]

        if dispatch < 0:
            HP.Win[i] = HP.Win0
            HP.interpolate_off_design(i)

            gHTES.power[i] = HP.Qout[i]
            gHTES.energy[i] = gHTES.energy[i - 1] + gHTES.power[i] * 1.0 * gHTES.recovery

            gCTES.power[i] = -HP.Qin0 * (gHTES.power[i] / HP.Qout0)
            gCTES.energy[i] = gCTES.energy[i - 1] + gCTES.power[i] * 1.0 * gCTES.recovery

        elif dispatch > 0:
            Qh = HE.Qin0
            if Qh * 1.0 < gHTES.energy[i - 1]:
                gHTES.power[i] = -Qh
            else:
                gHTES.power[i] = -gHTES.energy[i - 1] / 1.0
            gHTES.energy[i] = gHTES.energy[i - 1] + gHTES.power[i] * 1.0

            HE.Qin[i] = -gHTES.power[i]
            HE.interpolate_off_design(i)

            gCTES.power[i] = -HE.Qout0 * (gHTES.power[i] / HE.Qin0)
            gCTES.energy[i] = gCTES.energy[i - 1] + gCTES.power[i] * 1.0 * gCTES.recovery

        hour += 1
        if hour == 24:
            hour = 0

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
        gCTES.thickness,
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
        gCTES.productivity,
        gCTES.depth,
        gCTES.thickness,
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
        gCTES.injectivity,
        gCTES.depth,
        gCTES.thickness,
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
        gCTES.thickness,
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
        gCTES.productivity,
        gCTES.depth,
        gCTES.thickness,
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
        gCTES.charge_inj_Nwell,
        gCTES.injectivity,
        gCTES.depth,
        gCTES.thickness,
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
        gHTES.thickness,
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
        gHTES.productivity,
        gHTES.depth,
        gHTES.thickness,
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
        gHTES.injectivity,
        gHTES.depth,
        gHTES.thickness,
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
        gHTES.thickness,
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
        gHTES.productivity,
        gHTES.depth,
        gHTES.thickness,
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
        gHTES.injectivity,
        gHTES.depth,
        gHTES.thickness,
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
    econ.surface_capital_cost = HP.total_cost
    econ.OnM_surface = econ.OnM * econ.surface_capital_cost

    charge_cold_pump = Cold_source_ProdPumping_Cost_Duty[1] / 1e3 + Cold_sink_InjPumping_Cost_Duty[1] / 1e3
    charge_hot_pump = Hot_source_ProdPumping_Cost_Duty[1] / 1e3 + Hot_sink_InjPumping_Cost_Duty[1] / 1e3
    charge_cold_wells = gCTES.charge_prod_Nwell + gCTES.charge_inj_Nwell
    charge_hot_wells = gHTES.charge_prod_Nwell + gHTES.charge_inj_Nwell

    discharge_cold_pump = Cold_sink_ProdPumping_Cost_Duty[1] / 1e3 + Cold_source_InjPumping_Cost_Duty[1] / 1e3
    discharge_hot_pump = Hot_sink_ProdPumping_Cost_Duty[1] / 1e3 + Hot_source_InjPumping_Cost_Duty[1] / 1e3
    discharge_cold_wells = gCTES.discharge_prod_Nwell + gCTES.discharge_inj_Nwell
    discharge_hot_wells = gHTES.discharge_prod_Nwell + gHTES.discharge_inj_Nwell

    econ.Ein = (
        HP.Win_tot
        + charge_cold_pump
        + charge_hot_pump
        + discharge_cold_pump
        + discharge_hot_pump
    )
    econ.Qout = HE.Qin_tot

    econ.calc_fcr()
    econ.calc_revenue(
        HP.Win[(nY - 1) * hours : nY * hours],
        HE.Wout[(nY - 1) * hours : nY * hours],
    )
    econ.charge_cost = 0.0
    econ.calc_levelized_cost("H")

    econ.surface_capital_cost = HE.total_cost + HP.total_cost
    econ.OnM_surface = econ.OnM * econ.surface_capital_cost
    econ.Ein = HP.Win_tot + charge_cold_pump + charge_hot_pump
    econ.Eout = (
        HE.Wout_tot
        - discharge_cold_pump
        - discharge_hot_pump
        - HE.fan0 * HE.Wout0 / 1e3
    )
    CB["RTeff_real"] = econ.Eout / econ.Ein if econ.Ein != 0 else np.nan

    econ.calc_fcr()
    econ.calc_revenue(
        HP.Win[(nY - 1) * hours : nY * hours],
        HE.Wout[(nY - 1) * hours : nY * hours],
    )
    econ.charge_cost = 0.0
    econ.calc_levelized_cost("S")

    econ.LCOS_ITC = np.nan
    econ.LCOH_ITC = np.nan

    GeoTES_output = np.array(
        [
            input1,
            input2,
            charge_cold_pump,
            charge_hot_pump,
            charge_cold_wells,
            charge_hot_wells,
            discharge_cold_pump,
            discharge_hot_pump,
            discharge_cold_wells,
            discharge_hot_wells,
            HE.fan0 * HE.Wout0,
            100.0
            * (HE.Wout0 - HE.fan0 * HE.Wout0 - discharge_cold_pump - discharge_hot_pump)
            / (HP.Win0 + charge_cold_pump + charge_hot_pump),
            econ.LCOS,
            econ.LCOS_ITC,
            econ.LCOH,
            econ.LCOH_ITC,
            econ.total_capital_cost,
            econ.OnM_total,
        ],
        dtype=float,
    )

    return GeoTES_output


def main() -> None:
    input1_values = np.linspace(1.0, 5.0, int(round((5.0 - 1.0) / 0.05)) + 1)
    input2_values = [2736.0, 8208.0, 13680.0]
    param_out = np.zeros((len(input2_values), len(input1_values), 18), dtype=float)

    for q_idx, input2_value in enumerate(input2_values):
        for p_idx, input1_value in enumerate(input1_values):
            param_out[q_idx, p_idx, :] = run_GeoTES_TEA_R125(input1_value, input2_value)

    plt.figure(71)
    for q_idx in range(param_out.shape[0]):
        plt.plot(input1_values, param_out[q_idx, :, 11], label=f"input2={input2_values[q_idx]}")
    plt.xlabel("input1")
    plt.ylabel("GeoTES output 12")
    plt.legend()
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
