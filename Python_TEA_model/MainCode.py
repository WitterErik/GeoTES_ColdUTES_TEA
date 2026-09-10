# translating PRM matlab code to python

import numpy as np 
import pandas as pd
import shutil
import sys

import user_inputs
import initialization
from solar_modules import solar_class


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

def main():
    # create output folder if it does not exist
    user_inputs.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Verified output directory exists at: {user_inputs.output_dir}")


    # set up classes and run simulation
    location = user_inputs.system["location"]
    nY = user_inputs.system["nY'"]

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
    # csp_system = solar_class(location, mirror_type, nominal_dni, solar_multiple, ...)

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

    
    # When saving output data/plots, write them directly to your output directory:
    # plot_path = config.OUTPUT_DIR / "solar_production_profile.png"
    # plt.savefig(plot_path)


if __name__ == "__main__":
    main()
