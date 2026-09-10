# initialization file for variables
import user_inputs

class FluidState:
    """Helper class to represent the thermodynamic state of a working fluid."""
    def __init__(self, T=None, p=None, q=None):
        self.T = T
        self.p = p
        self.q = q

def initialize_gtes_states():
    """
    Initialize and return the starting thermodynamic states for the gTES system.
    Ties the starting temperatures to the values defined in user_inputs.py.
    """
    # Charging States
    charge_production = FluidState(
        T=user_inputs.gtes_settings["t_init"],  # Starts at Reservoir Initial Temp (50 C)
        p=40                               # 40 bar
    )
    
    charge_injection = FluidState(
        T=user_inputs.csp_specs["csp_tmax"],    # Heated to Max Solar Temperature (250 C)
        q=0,                               # Quality = 0 (subcooled liquid)
        p=40
    )

    # Discharging States
    discharge_production = FluidState(
        T=user_inputs.csp_specs["csp_tmax"],    # Produced at Max Solar Temperature (250 C)
        q=0                                # Quality = 0
    )

    discharge_injection = FluidState(
        T=user_inputs.gtes_settings["t_init"],  # Injected back at Reservoir Temp (50 C)
        p=40
    )

    return charge_production, charge_injection, discharge_production, discharge_injection
