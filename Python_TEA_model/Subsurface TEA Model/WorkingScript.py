from ExplorationCost import ExplorationCost
from DrillingCost import DrillingCost
from ProductionPumpingCost import ProductionPumpingCost
from InjectionPumpingCost import InjectionPumpingCost


def main():
    exploration_cost = ExplorationCost("Greenfield", 3, 20000, 1.2)
    total_exploration_cost = exploration_cost.exploration_cost_calc()
    print(f"Total Exploration Cost = ${total_exploration_cost}")

    ppi_multiplier = 1.175
    field_dev_plant_permitting = 1_000_000.0 * ppi_multiplier

    drilling_cost = DrillingCost(
        4,
        5,
        2500,
        500,
        "Large",
        1.0,
        2.2,
        "Vertical",
        "Openhole",
    )
    well_cost = drilling_cost.well_cost()
    total_drilling_cost = drilling_cost.total_dc(well_cost)
    print(f"Total Drilling Cost = ${total_drilling_cost}")

    prod_pumping = ProductionPumpingCost(
        190,
        110,
        4,
        2500,
        2500,
        500,
        "Large",
        "Lineshaft",
        "Openhole",
        1.553,
    )
    step1 = prod_pumping.head_prod_top()
    step2 = prod_pumping.head_suction(step1)
    step3 = prod_pumping.suction_depth(step2)
    step4 = prod_pumping.casing_friction(step3, step1)
    step5 = prod_pumping.pump_power(step3, step4)
    step6 = prod_pumping.pump_cost(step5, step3)
    prod_pumping_cost_duty = prod_pumping.total_pump_duty_cost(step5, step6)

    inj_pumping = InjectionPumpingCost(
        190,
        70,
        146.67,
        110,
        187.25,
        2.5,
        3000,
        2500,
        500,
        "Large",
        "Openhole",
        1.533,
        "Discharge",
    )
    step7 = inj_pumping.head_suction()
    step8 = inj_pumping.head_injection(step7)
    step9 = inj_pumping.pump_power(step8)
    step10 = inj_pumping.pump_cost(step9)
    inj_pumping_cost_duty = inj_pumping.total_pump_duty_cost(step9, step10)

    length_of_flowline = 750.0
    piping_unit_cost = 256.98
    total_number_of_wells = 11
    flow_line_cost = length_of_flowline * 3.28084 * piping_unit_cost * total_number_of_wells

    subsurface_capital_cost = (
        total_exploration_cost
        + field_dev_plant_permitting
        + total_drilling_cost
        + step6
        + step10
        + flow_line_cost
    )
    print(f"Subsurface Capital Cost = ${subsurface_capital_cost}")

    wellfield_maintenance = 0.015 * (total_drilling_cost + flow_line_cost)
    pump_maintenance = prod_pumping.pump_maintenance_cost(step3, step6)

    oil_saturation = 0.0
    number_production_wells = 4
    production_rate_per_well = 110.0
    makeup_water_unit_cost = 0.65
    subsurface_water_loss = oil_saturation + 0.05
    makeup_water_subsurface = (
        makeup_water_unit_cost
        * number_production_wells
        * (production_rate_per_well * 18.0917 * 34.2857 * 365.0)
        * subsurface_water_loss
    )

    property_tax_rate = 0.0075
    annual_tax_and_insurance = property_tax_rate * subsurface_capital_cost

    subsurface_om_cost = (
        wellfield_maintenance
        + pump_maintenance
        + makeup_water_subsurface
        + annual_tax_and_insurance
    )
    print(f"Subsurface O&M Cost = ${subsurface_om_cost}")


if __name__ == "__main__":
    main()
