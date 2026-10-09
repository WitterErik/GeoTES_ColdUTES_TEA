# initialization file for variables
import user_inputs
import sys
from fluid_class_update import fluid_class

FLOWLINE_LENGTH_M = user_inputs.engineering["flowline_length_m"]
PIPING_UNIT_COST_USD_FT = user_inputs.engineering["piping_cost_usd_ft"]
M_TO_FT = user_inputs.engineering["m_to_ft"]
PPI_MULTIPLIER = user_inputs.engineering["ppi_multiplier"]
BASE_PERMITTING_COST = user_inputs.engineering["base_permitting_cost"]
PROPERTY_TAX_RATE = user_inputs.finance["property_tax_rate"]
MAKEUP_WATER_UNIT_COST = 0.65
OIL_SATURATION = 0.0
SUBSURFACE_WATER_LOSS_BASE = 0.001

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
    charge_production.T = user_inputs.gtes_settings["Tinit"]
    charge_production.p = 40                                    # 40 bar
    
    charge_injection = fluid_class(fluid_type)
    charge_injection.T = user_inputs.csp_specs["csp_tmax"]
    charge_injection.q = 0                                      # Quality = 0 (subcooled liquid)
    charge_injection.p = 40

    # 2. Discharging States
    discharge_production = fluid_class(fluid_type)
    discharge_production.T = user_inputs.csp_specs["csp_tmax"]
    discharge_production.q = 0                                  # Quality = 0
    
    discharge_injection = fluid_class(fluid_type)
    discharge_injection.T = user_inputs.gtes_settings["Tinit"]
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
        user_inputs.subsurface_dir,
        user_inputs.utility_dir,
        user_inputs.base_dir / "SAM",
        user_inputs.base_dir / "data"
    ]
    for folder in dependencies:
        if folder.exists() and str(folder) not in sys.path:
            sys.path.append(str(folder))
