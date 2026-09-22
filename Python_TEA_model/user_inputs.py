# user inputs file

from pathlib import Path

base_dir = Path(__file__).resolve().parent
subsurface_dir = base_dir / "Subsurface"
utility_dir = base_dir / "utility"
SAM_dir = base_dir / "SAM"
data_dir = base_dir / "data"

output_dir = base_dir / "Outputs"

# ==========================================
# system and simulation parameters
# ==========================================
system = {
    "location": "Antelope Hills, CA",
    "nY": 2,                 # number of years to run simulation
    "save_figs": True,      # true to save plots
}

# ==========================================
# operating hours and seasons
# ==========================================
#  month-day definitions (non-leap year)
jan, feb, mar, apr, may, jun, jul, aug, sep, oct, nov, dec = 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31

# Seasonal simulation phases (start and end hours)
phases = {
    "phase1":[1, (jan + feb + mar) * 24 + 1],
    "phase2": [1,(jan + feb + mar)*24+1, (jan + feb + mar + apr + may + jun + jul + aug + sep) * 24 + 1],
    "phase3": [
        ((jan + feb + mar + apr + may + jun + jul + aug + sep) * 24 + 1),
        (jan + feb + mar + apr + may + jun + jul + aug + sep + oct + nov + dec) * 24 + 1
    ]
}

# daily operating hours of interest
operating_hours = {
    "op_hour1": list(range(17, 23)),
    "op_hour2": list(range(17, 23)),
    "op_hour3": list(range(17, 23))
}

# ==========================================
#### CSP inputs
# ==========================================
csp_specs = {
    "mirror_type": "Parabolic trough",
    "nominal_dni": 950,          # Nominal Direct Normal Irradiance, W/m2
    "solar_multiple": 2.5,
    "csp_tmax": 250,             # Max temperature, C
    "csp_tmin": 100,             # Min temperature, C
    "csp_land_mult": 1.1,
}

# Cost sub-dictionary
csp_costs = {
    "mirror": 105,               # Mirror cost, $/m2
    "land": 20,                  # Site improvements, $/m2
    "hx": 250                    # Heat exchanger to high-temp TES, $/kWh-th
}

# ==========================================
# Low-Temperature Power Cycle (LTPC) Settings
# ==========================================
ltpc_type = "HE"  # Type of power cycle [heat engine]

ltpc_design = {
    "Wout": 199,    # Power output, MW-e
    "T0": 25,       # Design ambient temperature, C
    "TIT": 250,     # Turbine inlet temperature, C (Eff/Qin calculated from this)
    "fan": 0.1
}

# Use PATHLIB to safely resolve the excel file location dynamically on Windows or Linux
ltpc_foff = data_dir / "example_off_design.xlsx" 

ltpc_costs = {
    "power_block": 750,  # power block, $/kW-e
    "HX": 250,           # heat exchanger between TES and power block, $/kWh-th
    "fan": 500           # air fan cost, $/kW-e
}

# ==========================================
# Low temp GeoTES inputs
# ==========================================
reversible_wells = False        # Are charge production wells used as discharge injection wells (and charge injection wells used as discharge production wells)

gtes_settings = {
    "recovery" : 0.95 ,           # Fraction of input thermal energy that is recovered
    "Tinit" : 50,                 # Initial reservoir temperature, C
    "Qmax" : 920.63,              # Maximum charging power input, MWh-th"
    "fluid" : 'water',            # type of fluid
    "mode": "separate"            # three modes, separate, continuous, push-pull   
}

# define the production and injection flow rates in L/s
gtes_flowrate = {
    "production" : 40,
    "injection" : 80
}

gtes_props = {
    "rho": 2000,           # Rock density, kg/m3
    "cp": 800,             # Rock heat capacity, J/kg.K
    "void": 0.32,          # Porosity
    "depth": 500,          # Well depth, m
    "thickness": 100       # Production thickness, m
}


# ==========================================
# Financial and economic inputs
# ==========================================
# ==========================================
finance = {
    "lifetime": 50,        # Lifetime in years
    "elec_price": 0.05,    # Electricity price - dollars per kWhe.
    "inflation": 0.025,    # Inflation
    "irr": 0.10,           # Internal Rate of Return
    "debt_frac": 0.60,     # Project debt fraction
    "debt_ir": 0.08,       # Debt interest rate
    "tax_rate": 0.28,      # Tax rate
    "deprec": [0.20, 0.32, 0.20, 0.14, 0.14],  # Depreciation array
    "annual_cost": [1.0, 0.0, 0.0],            # Capital cost incurred in which years
    "construc_ir": 0.0,    # Construction interest rate
    "onm": 0.015,          # Operations & maintenance fraction of total capital cost
    "itc": 0.4             # Investment tax credit
}

# ============================================
# Wellfield, Exploration, and Piping Constants
# ============================================
exploration_specs = {
    "field_type": "Greenfield",
    "wells_count": 3,
    "target_depth": 20000,
    "cost_multiplier": 1.2
}

engineering = {
    "flowline_length_m": 300,      # pipe meters per well
    "piping_cost_usd_ft": 256.98,  # Piping unit cost
    "m_to_ft": 3.28084,            # Unit conversion factor
    "ppi_multiplier": 1.175,       # Legal/permitting inflation scaling
    "base_permitting_cost": 1000000 # GETEM base permitting cost ($)
}

# ==========================================
# Financial / Economic Inputs
# ==========================================
finance = {
    "lifetime": 50,
    "elec_price": 0.05,
    "inflation": 0.025,
    "irr": 0.10,
    "debt_frac": 0.60,
    "debt_ir": 0.08,
    "tax_rate": 0.28,
    "deprec": [0.20, 0.32, 0.20, 0.14, 0.14],
    "annual_cost": [1.0, 0.0, 0.0],
    "construc_ir": 0.0,
    "onm_rate": 0.015,
    "itc_rate": 0.4,
    "property_tax_rate": 0.0075,
}

# LCOH Baselines / Comparison offsets
finance_baseline_offsets = {
    "lcoh_csp_offset": 923.49e6,
    "lcoh_om_offset": 13.85e6,
    "lcoh_sub_cap_offset": 95.42e6,
    "lcoh_sub_om_offset": 2.80e6,
    "lcoh_ein_offset": 62.5886,
}
}
