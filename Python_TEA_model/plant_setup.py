"""Construct and initialize the model's major component objects."""

from types import SimpleNamespace

import user_inputs
import initialization

from economics_class_update import economics_class
from fluid_class_update import calc_fluid_props
from geoTES_class_update import geoTES_class
from solar_class_update import solar_class
from thermo_cycle_class_update import thermo_cycle_class


def initialize_plant():
    """Build component classes and initialize all four GeoTES fluid boundaries."""
    location = user_inputs.system["location"]
    n_years = int(user_inputs.system["nY"])

    csp_specs = user_inputs.csp_specs
    csp = solar_class(
        location,
        csp_specs["mirror_type"],
        csp_specs["nominal_dni"],
        csp_specs["solar_multiple"],
        csp_specs["initial_size"],
        csp_specs["csp_tmax"],
        csp_specs["csp_tmin"],
        csp_specs["csp_land_mult"],
        user_inputs.csp_costs,
        n_years,
    )

    power_cycle = thermo_cycle_class(
        user_inputs.ltpc_type,
        user_inputs.ltpc_design,
        str(user_inputs.ltpc_foff),
        user_inputs.ltpc_costs,
        n_years,
    )

    settings = user_inputs.gtes_settings
    geotes = geoTES_class(
        settings["recovery"],
        settings["Tinit"],
        user_inputs.gtes_flowrate,
        settings["Qmax"],
        user_inputs.gtes_props,
        settings["fluid"],
        settings["mode"],
        n_years,
    )

    (
        geotes.charge_production,
        geotes.charge_injection,
        geotes.discharge_production,
        geotes.discharge_injection,
    ) = initialization.initialize_gtes_states()

    geotes.charge_production = calc_fluid_props(geotes.charge_production, "pT")
    geotes.charge_injection = calc_fluid_props(geotes.charge_injection, "pT")
    geotes.discharge_production = calc_fluid_props(geotes.discharge_production, "qT")
    geotes.discharge_injection = calc_fluid_props(geotes.discharge_injection, "pT")

    economics = economics_class(user_inputs.finance)

    return SimpleNamespace(
        location=location,
        n_years=n_years,
        total_hours=n_years * 8760,
        csp=csp,
        power_cycle=power_cycle,
        geotes=geotes,
        economics=economics,
    )
