import os
import sys
from pathlib import Path
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np

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


def main() -> None:
    save_figs = 1
    output_dir = Path("Outputs")
    ensure_output_folder(output_dir)

    # System level inputs
    location = "Imperial CA"

    # CSP inputs
    mirror_type = "Parabolic trough"
    nominal_DNI = 950.0  # W/m2
    solar_multiple = 7.1
    initial_size = 100.0  # MW-e - estimate energy flows for a large system
    CSP_Tmax = 565.0  # Max temperature, C
    CSP_Tmin = 300.0  # Min temperature, C
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
    )

    # High-temperature power cycle inputs
    HTPC_type = "HE"
    HTPC_design = {
        "Wout": 10.0,
        "T0": 15.0,
        "TIT": CSP_Tmax - 10.0,
    }
    HTPC_foff = str(project_root / "data" / "example_off_design.xlsx")

    HTPC_cost = {
        "power_block": 1000.0,
        "HX": 250.0,
    }
    HTPC = thermo_cycle_class(HTPC_type, HTPC_design, HTPC_foff, HTPC_cost)

    # Low-temperature power cycle inputs
    LTPC_type = "HE"
    LTPC_design = {
        "Wout": 10.0,
        "T0": 15.0,
        "TIT": 200.0,
    }
    LTPC_foff = str(project_root / "data" / "example_off_design.xlsx")
    LTPC_cost = {
        "power_block": 1000.0,
        "HX": 250.0,
    }
    LTPC = thermo_cycle_class(LTPC_type, LTPC_design, LTPC_foff, LTPC_cost)

    # High-temperature thermal storage inputs
    TES_duration = 2.0
    TES_fluid = "nitrate salt"
    TES_Thot = CSP_Tmax
    TES_Tcld = CSP_Tmin
    TES_Qloss = 1.0
    TES_max_tank_vol = 50000.0
    ins = {"k": 0.08, "rho": 150.0}

    TES_cost = {
        "fluid": 1.0,
        "tank": 0.0,
        "insulation": 50.0,
    }
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

    # Low-temperature thermal storage (geoTES) inputs
    reversible_wells = True
    gTES_recovery = 0.85
    gTES_Tinit = 50.0
    gTES_flowrate = 60.0
    gTES_Qmax = 1000.0
    gTES_props = {"rho": 2000.0, "cp": 800.0, "void": 0.25}
    gTES_fluid = "water"

    gTES = geoTES_class(
        gTES_recovery,
        gTES_Tinit,
        gTES_flowrate,
        gTES_Qmax,
        gTES_props,
        gTES_fluid,
    )

    # Financial inputs
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

    # Specify fluid properties for the production and injection wells
    gTES.charge_production.T = gTES.Tinit
    gTES.charge_production.p = 10.0
    gTES.charge_production.calc_fluid_props("pT")

    gTES.charge_injection.T = LTPC.Tmax
    gTES.charge_injection.q = 0.0
    gTES.charge_injection.calc_fluid_props("qT")

    gTES.discharge_production.T = LTPC.Tmax
    gTES.discharge_production.q = 0.0
    gTES.discharge_production.calc_fluid_props("qT")

    gTES.discharge_injection.T = gTES.Tinit
    gTES.discharge_injection.p = 10.0
    gTES.discharge_injection.calc_fluid_props("pT")

    out = call_SAM(CSP, HTPC)
    CSP.mirror_aperture = out.mirror_area
    CSP.land_area = out.land_area
    CSP.nominal_eff = out.nominal_eff
    CSP.annual_eff = out.annual_eff
    CSP.DNI = out.DNI

    hours = 8760
    hours2 = 2 * hours

    # Build 2-year data from the 1-year results.
    CSP.power = np.concatenate((out.field_thermal_power, out.field_thermal_power))
    CSP.power = np.maximum(CSP.power, 0.0)
    HTPC.Tamb = np.concatenate((out.Tamb, out.Tamb))
    LTPC.Tamb = HTPC.Tamb.copy()

    # Ensure hour-by-hour state arrays are initialized for Python.
    HTPC.Qin = np.zeros(hours2, dtype=float)
    TES.power = np.zeros(hours2, dtype=float)
    TES.energy = np.zeros(hours2, dtype=float)
    gTES.power = np.zeros(hours2, dtype=float)
    gTES.energy = np.zeros(hours2, dtype=float)

    HTPC.Qin[0] = CSP.power[0]
    HTPC.interpolate_off_design(0)

    for i in range(1, hours2):
        TES.energy[i] = TES.energy[i - 1]
        gTES.energy[i] = gTES.energy[i - 1]

        if CSP.power[i] > HTPC.Qin0:
            HTPC.Qin[i] = HTPC.Qin0
            HTPC.interpolate_off_design(i)

            dP = CSP.power[i] - HTPC.Qin0
            dTES = TES.energy_capacity - TES.energy[i - 1]
            if dTES > dP:
                TES.power[i] = dP
                TES.energy[i] = TES.energy[i - 1] + dP
            else:
                TES.power[i] = dTES
                TES.energy[i] = TES.energy_capacity
                dP -= TES.power[i]
                if dP < gTES.Qmax:
                    gTES.power[i] = dP
                else:
                    gTES.power[i] = gTES.Qmax
                    CSP.dumped[i] = dP - gTES.Qmax
                gTES.energy[i] = gTES.energy[i - 1] + gTES.power[i] * gTES.recovery
        else:
            dP = HTPC.Qin0 - CSP.power[i]
            if dP < TES.energy[i - 1]:
                TES.power[i] = -dP
                TES.energy[i] = TES.energy[i - 1] - dP
                HTPC.Qin[i] = HTPC.Qin0
                HTPC.interpolate_off_design(i)
            else:
                TES.power[i] = -TES.energy[i - 1]
                TES.energy[i] = 0.0
                HTPC.Qin[i] = CSP.power[i] - TES.power[i]
                HTPC.interpolate_off_design(i)

                dW = HTPC.Wout0 - HTPC.Wout[i]
                dQ = dW / LTPC.eff0

                if dQ >= LTPC.Qin0:
                    gTES.power[i] = -min(LTPC.Qin0, gTES.energy[i - 1])
                else:
                    gTES.power[i] = -min(dQ, gTES.energy[i - 1])

                gTES.energy[i] = gTES.energy[i - 1] + gTES.power[i]
                LTPC.Qin[i] = -gTES.power[i]
                LTPC.interpolate_off_design(i)

    gTES.geoTES_size()
    gTES.geoTES_well_flows()

    CSP.CSP_annual_energy()
    HTPC.PC_annual_energy()
    LTPC.PC_annual_energy()
    gTES.geoTES_annual_energy()
    TES.TES_annual_energy()

    CSP.calc_CSP_cost(HTPC)
    HTPC.calc_PC_cost()
    LTPC.calc_PC_cost()
    TES.calc_TES_cost()

    Exploration_Cost = ExplorationCost("Greenfield", 3, 20000, 1.2)
    Total_Exploration_Cost = Exploration_Cost.exploration_cost_calc()

    PPImultiplier = 1.175
    FieldDevPlantPermitting = 1_000_000.0 * PPImultiplier

    Charge_Drilling_Cost = DrillingCost(
        gTES.charge_prod_Nwell,
        gTES.charge_inj_Nwell,
        2500,
        500,
        "Large",
        1,
        2.2,
        "Vertical",
        "Openhole",
    )
    Charge_Well_Cost = Charge_Drilling_Cost.well_cost()
    Total_Charge_Drilling_Cost = Charge_Drilling_Cost.total_dc(Charge_Well_Cost)

    ResTemp = gTES.Tinit
    Pflowrate = gTES.flowrate_per_well * gTES.charge_production.rho / 1000.0
    Charge_ProdPumping_Estimation = ProductionPumpingCost(
        ResTemp,
        Pflowrate,
        gTES.charge_prod_Nwell,
        2500,
        2500,
        500,
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

    InjTemp = LTPC.Tmax
    Iflowrate = gTES.flowrate_per_well * gTES.charge_injection.rho / 1000.0
    PressureThermalSource = gTES.charge_injection.p * 14.5038
    Charge_InjPumping_Estimation = InjectionPumpingCost(
        ResTemp,
        InjTemp,
        Iflowrate,
        Pflowrate,
        PressureThermalSource,
        gTES.charge_inj_Nwell,
        3000,
        2500,
        500,
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
    TotalNumberofWells = gTES.charge_prod_Nwell + gTES.charge_inj_Nwell
    Charge_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * TotalNumberofWells

    Charge_WellFieldMaintenance = 0.015 * (Total_Charge_Drilling_Cost + Charge_FlowLineCost)
    Charge_PumpMaintenance = Charge_ProdPumping_Estimation.pump_maintenance_cost(Step3, Step6)

    OilSaturation = 0.0
    NumberProductionWells = gTES.charge_prod_Nwell
    ProductionRateperWell = Pflowrate
    MakeupWaterUnitCost = 0.65
    SubsurfaceWaterLoss = OilSaturation + 0.05
    Charge_MakeupWaterSubsurface = (
        MakeupWaterUnitCost
        * NumberProductionWells
        * (ProductionRateperWell * 18.0917 * 34.2857 * 365.0)
        * SubsurfaceWaterLoss
    )

    Discharge_Drilling_Cost = DrillingCost(
        gTES.discharge_prod_Nwell,
        gTES.discharge_inj_Nwell,
        2500,
        500,
        "Large",
        1,
        2.2,
        "Vertical",
        "Openhole",
    )
    Discharge_Well_Cost = Discharge_Drilling_Cost.well_cost()
    Total_Discharge_Drilling_Cost = 0.0 if reversible_wells else Discharge_Drilling_Cost.total_dc(Discharge_Well_Cost)

    ResTemp = gTES.Tinit
    Pflowrate = gTES.flowrate_per_well * gTES.discharge_production.rho / 1000.0
    Discharge_ProdPumping_Estimation = ProductionPumpingCost(
        ResTemp,
        Pflowrate,
        gTES.discharge_prod_Nwell,
        2500,
        2500,
        500,
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

    InjTemp = gTES.Tinit
    Iflowrate = gTES.flowrate_per_well * gTES.discharge_injection.rho / 1000.0
    PressureThermalSource = gTES.discharge_injection.p * 14.5038
    Discharge_InjPumping_Estimation = InjectionPumpingCost(
        ResTemp,
        InjTemp,
        Iflowrate,
        Pflowrate,
        PressureThermalSource,
        gTES.discharge_inj_Nwell,
        3000,
        2500,
        500,
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
    if reversible_wells:
        Discharge_InjPumping_Cost_Duty = [0.0, 0.0]

    Discharge_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * (gTES.discharge_prod_Nwell + gTES.discharge_inj_Nwell)
    if reversible_wells:
        Discharge_FlowLineCost = 0.0

    Discharge_WellFieldMaintenance = 0.015 * (Total_Discharge_Drilling_Cost + Discharge_FlowLineCost)
    Discharge_PumpMaintenance = Discharge_ProdPumping_Estimation.pump_maintenance_cost(Step3, Step6)

    NumberProductionWells = gTES.discharge_prod_Nwell
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
    econ.surface_capital_cost = (
        CSP.total_cost + TES.total_cost + HTPC.total_cost + LTPC.total_cost
    )
    econ.OnM_surface = econ.OnM * econ.surface_capital_cost
    econ.Ein = 0.0
    econ.Eout = HTPC.Wout_tot + LTPC.Wout_tot

    econ.calc_fcr()
    econ.calc_levelized_cost("E")

    print("\nPOWER OUTPUTS\n")
    print(f"Maximum solar power generated             = {np.max(CSP.power):6.2f} MW-th")
    print(f"High-temp power cycle power output        = {HTPC.Wout0:6.2f} MW-e")
    print(
        f"Average high-temp power cycle output      = {np.mean(HTPC.Wout[hours:hours2][HTPC.Wout[hours:hours2] > 0]):6.2f} MW-e"
    )
    print(f"Low-temp power cycle power output         = {LTPC.Wout0:6.2f} MW-e")
    print(
        f"Average low-temp power cycle output       = {np.mean(LTPC.Wout[hours:hours2][LTPC.Wout[hours:hours2] > 0]):6.2f} MW-e"
    )
    print(f"Max. thermal power into subsurface        = {np.max(gTES.power[hours:hours2]):6.2f} MW-th")
    print(f"Max. thermal power out of subsurface      = {-np.min(gTES.power[hours:hours2]):6.2f} MW-th")
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
    print(f"Electricity generated by low-temp. cycle  = {LTPC.Wout_tot:6.2f} GWh-e\n")
    print(f"Total electricity generateion             = {(HTPC.Wout_tot + LTPC.Wout_tot):6.2f} GWh-e\n")
    print(f"Heat delivered to geoTES                  = {gTES.energy_in_tot:6.2f} GWh-th")
    print(f"Heat extracted from geoTES                = {gTES.energy_out_tot:6.2f} GWh-th\n")
    print(
        f"Charge production pump consumption        = {np.count_nonzero(gTES.power[hours:hours2] > 0) * Charge_ProdPumping_Cost_Duty[0] / 1e6:6.2f} GWh-e"
    )
    print(
        f"Charge injection pump consumption         = {np.count_nonzero(gTES.power[hours:hours2] > 0) * Charge_InjPumping_Cost_Duty[0] / 1e6:6.2f} GWh-e"
    )
    print(
        f"Discharge production pump consumption     = {np.count_nonzero(gTES.power[hours:hours2] < 0) * Discharge_ProdPumping_Cost_Duty[0] / 1e6:6.2f} GWh-e"
    )
    print(
        f"Discharge injection pump consumption      = {np.count_nonzero(gTES.power[hours:hours2] < 0) * Discharge_InjPumping_Cost_Duty[0] / 1e6:6.2f} GWh-e\n"
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
    print(f"Solar field cost                = {CSP.total_cost / 1e6:6.2f} M$")
    print(f"High-temp. thermal storage cost = {TES.total_cost / 1e6:6.2f} M$")
    print(f"High-temp. power cycle cost     = {HTPC.total_cost / 1e6:6.2f} M$")
    print(f"Low-temp. power cycle cost      = {LTPC.total_cost / 1e6:6.2f} M$\n")
    print(f"Surface capital cost              = {econ.surface_capital_cost / 1e6:6.2f} M$")
    print(f"Surface O&M cost                = {econ.OnM_surface / 1e6:6.2f} M$\n")

    print("TOTAL COST RESULTS\n")
    print(f"Total capital cost              = {econ.total_capital_cost / 1e6:6.2f} M$")
    print(f"LCOE                            = {econ.LCOE:6.2f} $/kWh-e\n")

    # Plotting with matplotlib
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
            CSP.total_cost,
            TES.total_cost,
            HTPC.total_cost,
            LTPC.total_cost,
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
        "CSP",
        "TES",
        "High-temp. power cycle",
        "Low-temp power cycle",
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

    LCOE_mat = np.concatenate(
        (
            Ccap * econ.FCR * 1e6,
            np.array([econ.OnM_subsurface, econ.OnM_surface]),
        )
    )
    LCOE_mat = LCOE_mat / econ.Eout / 1e6
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
        "CSP",
        "TES",
        "High-temp. power cycle",
        "Low-temp power cycle",
        "Subsurface O&M",
        "Surface O&M",
    ]

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.bar(np.arange(len(LCOE_mat)), LCOE_mat)
    ax.set_xticks(np.arange(len(LCOE_mat)))
    ax.set_xticklabels(xlab, rotation=45, ha="right")
    ax.set_ylabel("LCOE, $/kWh-e")
    ax.set_title("LCOE contribution breakdown")
    plt.tight_layout()
    fig.savefig(output_dir / "LCOE.png", dpi=300)
    plt.close(fig)

    n1 = np.arange(hours + 24 * 27, hours + 24 * 31 + 1)
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(n1, CSP.power[n1], label="Solar heat")
    ax.plot(n1, TES.power[n1], label="Heat to HT-TES")
    ax.plot(n1, HTPC.Qin[n1], label="Heat to HT power cycle")
    ax.plot(n1, gTES.power[n1], label="Heat to geoTES")
    ax.plot(n1, LTPC.Qin[n1], label="Heat to LT power cycle")
    ax.set_title("January 27")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Heat, MWh-th")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.3), ncol=2)
    plt.tight_layout()
    fig.savefig(output_dir / "January_power_flows.png", dpi=300)
    plt.close(fig)

    day_of_year_aug1 = datetime(2022, 8, 1).timetuple().tm_yday
    day_of_year_aug4 = datetime(2022, 8, 4).timetuple().tm_yday
    n2 = np.arange(hours + 24 * day_of_year_aug1, hours + 24 * day_of_year_aug4 + 1)
    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(n2, CSP.power[n2], label="Solar heat")
    ax.plot(n2, TES.power[n2], label="Heat to HT-TES")
    ax.plot(n2, HTPC.Qin[n2], label="Heat to HT power cycle")
    ax.plot(n2, gTES.power[n2], label="Heat to geoTES")
    ax.plot(n2, LTPC.Qin[n2], label="Heat to LT power cycle")
    ax.set_title("August 4")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Heat, MWh-th")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.3), ncol=2)
    plt.tight_layout()
    fig.savefig(output_dir / "August_power_flows.png", dpi=300)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(np.arange(hours), gTES.energy[hours:] / 1000)
    ax.set_xlim(0, hours)
    ax.set_title("Energy in geoTES")
    ax.set_xlabel("Hour of the year")
    ax.set_ylabel("Energy in geoTES, GWh-th")
    plt.tight_layout()
    fig.savefig(output_dir / "geoTES_SOC.png", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    main()
