# initialization file for variables
import user_inputs
import sys
from fluid_class_update import fluid_class

class FluidState:
    """Helper class to represent the thermodynamic state of a working fluid."""
    def __init__(self, T=None, p=None, q=None):
        self.T = T
        self.p = p
        self.q = q

def initialize_gtes_states():
    """
    Initializes and returns starting thermodynamic fluid states for the gTES.
    Pulls operational temperature boundaries from user_inputs.py.
    """
    fluid_type = user_inputs.gtes_settings["fluid"]

    # 1. Charging States
    # Initializes custom fluid_class instances (supports CoolProp & Tabular Salts)
    charge_production = fluid_class(fluid_type)
    charge_production.T = user_inputs.gtes_settings["t_init"]  # Starts at Reservoir Temp (50 C)
    charge_production.p = 40                                    # 40 bar
    
    charge_injection = fluid_class(fluid_type)
    charge_injection.T = user_inputs.csp_specs["csp_tmax"]      # Heated to Max Solar Temp (250 C)
    charge_injection.q = 0                                      # Quality = 0 (subcooled liquid)
    charge_injection.p = 40

    # 2. Discharging States
    discharge_production = fluid_class(fluid_type)
    discharge_production.T = user_inputs.csp_specs["csp_tmax"]  # Produced at Max Solar Temp (250 C)
    discharge_production.q = 0                                  # Quality = 0
    
    discharge_injection = fluid_class(fluid_type)
    discharge_injection.T = user_inputs.gtes_settings["t_init"] # Injected back at Reservoir Temp (50 C)
    discharge_injection.p = 40

    return charge_production, charge_injection, discharge_production, discharge_injection


# ==========================================
# 3. Environmental Dependencies Setup
# ==========================================
def setup_environmental_paths():
    """
    Appends required subdirectories (Subsurface, utility, etc.) 
    to sys.path so they can be imported inside main.py.
    """
    dependencies = [
        user_inputs.base_dir / "Subsurface",
        user_inputs.base_dir / "utility",
        user_inputs.base_dir / "SAM",
        user_inputs.base_dir / "data"
    ]
    for folder in dependencies:
        if folder.exists() and str(folder) not in sys.path:
            sys.path.append(str(folder))
