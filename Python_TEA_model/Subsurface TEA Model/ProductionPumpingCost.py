import math


class ProductionPumpingCost:
    """Estimate production pumping requirements and costs for subsurface wells."""

    def __init__(
        self,
        reservoir_temperature,
        well_flow_rate,
        number_production_wells,
        productivity,
        depth,
        production_thickness,
        well_type,
        pump_type,
        completion,
        ppi_multiplier,
    ):
        self.reservoir_temperature = float(reservoir_temperature)
        self.well_flow_rate = float(well_flow_rate)
        self.number_production_wells = int(number_production_wells)
        self.well_productivity = float(productivity)
        self.well_depth = float(depth)
        self.production_thickness = float(production_thickness)
        self.well_type = str(well_type)
        self.pump_type = str(pump_type)
        self.completion = str(completion)
        self.well_temp_loss = 0.0005
        self.ppi_multiplier = float(ppi_multiplier)
        self.total_pumping_duty = 0.0
        self.total_pumping_cost = 0.0

    def head_prod_top(self) -> float:
        if self.well_type == "Small" and self.completion == "Openhole":
            well_diameter = 8.5
        elif self.well_type == "Small" and self.completion == "Liner":
            well_diameter = 7.0
        elif self.well_type == "Large" and self.completion == "Openhole":
            well_diameter = 12.25
        else:
            well_diameter = 9.625

        prod_thickness_ft = self.production_thickness * 3.28084
        res_temperature_f = self.reservoir_temperature * 1.8 + 32
        well_temp_loss_fft = self.well_temp_loss * 1.8 / 3.28083
        t_surf = 52.88

        if self.completion == "Openhole":
            surface_roughness = 0.02
        else:
            surface_roughness = 0.001

        rho_surf = (
            -1.7845e-10 * t_surf ** 4
            + 2.0215e-07 * t_surf ** 3
            - 0.00012456 * t_surf ** 2
            + 0.0072343 * t_surf
            + 62.329
        ) * 16.01846
        p_surf = 1.01325
        tau_t = (self.reservoir_temperature - ((t_surf - 32.0) / 1.8)) / self.well_depth
        cp = 4.64e-10
        ct = 9e-4 / (30.796 * self.reservoir_temperature ** -0.552)
        phydrostatic = p_surf + 1.0 / cp * (
            math.exp(rho_surf * 9.807 * cp * (self.well_depth - (0.5 * ct * tau_t * self.well_depth ** 2)) / 100000.0) - 1.0
        )
        phydropsi = 14.50377 * phydrostatic
        drawdown = self.well_flow_rate * 7936.64 / self.well_productivity
        p_bottomhole = phydropsi - drawdown

        tavg_f = res_temperature_f - 0.5 * well_temp_loss_fft * prod_thickness_ft
        psatwater = (
            -2.55175e-12 * tavg_f ** 5
            + 2.41218e-08 * tavg_f ** 4
            - 9.19096e-06 * tavg_f ** 3
            + 0.001969537 * tavg_f ** 2
            - 0.197885257 * tavg_f
            + 8.089410675
        )
        rho = 1.0 / (
            1.40682e-18 * tavg_f ** 6
            - 2.69957e-15 * tavg_f ** 5
            + 2.17758e-12 * tavg_f ** 4
            - 9.15282e-10 * tavg_f ** 3
            + 2.2418e-7 * tavg_f ** 2
            - 2.3968e-5 * tavg_f
            + 0.017070952
        )
        pressure_ratio = (p_bottomhole - 0.5 * rho * prod_thickness_ft / 144.0) / psatwater
        rho_corrected = rho * (1.0 + (7.15037e-19 * tavg_f ** 5.91303) * (pressure_ratio - 1.0))
        viscosity = 407.22 * tavg_f ** (-1.194) / 3600.0
        viscosity_corrected = viscosity * (1.0 + (4.02401e-18 * tavg_f ** 5.736882) * (pressure_ratio - 1.0))
        velocity = (
            (self.well_flow_rate * 7936.64 / rho_corrected) / 3600.0
        ) / (math.pi * (well_diameter / 12.0) ** 2 / 4.0)
        reynolds_num = rho * velocity * (well_diameter / 12.0) / viscosity_corrected
        a_const = -2.0 * math.log10((surface_roughness / (well_diameter / 12.0)) / 3.7 + 12.0 / reynolds_num)
        b_const = -2.0 * math.log10((surface_roughness / (well_diameter / 12.0)) / 3.7 + (2.51 * a_const) / reynolds_num)
        c_const = -2.0 * math.log10((surface_roughness / (well_diameter / 12.0)) / 3.7 + (2.51 * b_const) / reynolds_num)
        friction_factor = (a_const - (b_const - a_const) ** 2 / (c_const - 2.0 * b_const + a_const)) ** -2
        delta_p_friction = (rho * prod_thickness_ft * ((friction_factor * 1.0 / (well_diameter / 12.0)) * (velocity ** 2) / (2.0 * 32.174))) / 144.0
        return p_bottomhole - delta_p_friction - (rho_corrected * prod_thickness_ft / 144.0)

    def head_suction(self, pump_head_prod_top: float) -> float:
        if self.well_type == "Small":
            casing_int_diameter = 9.625 - (2 * 0.4375)
        else:
            casing_int_diameter = 13.625 - (2 * 0.5625)

        well_depth_ft = self.well_depth * 3.28084
        prod_thickness_ft = self.production_thickness * 3.28084
        column_depth = well_depth_ft - prod_thickness_ft
        res_temperature_f = self.reservoir_temperature * 1.8 + 32
        well_temp_loss_fft = self.well_temp_loss * 1.8 / 3.28083
        p_excess = 50.0

        twellhead = res_temperature_f - well_temp_loss_fft * well_depth_ft
        psatwellhead = (
            -2.55175e-12 * twellhead ** 5
            + 2.41218e-08 * twellhead ** 4
            - 9.19096e-06 * twellhead ** 3
            + 0.001969537 * twellhead ** 2
            - 0.197885257 * twellhead
            + 8.089410675
        )
        surface_roughness = 0.00015

        tavg_f = res_temperature_f - 0.5 * well_temp_loss_fft * column_depth
        rho = 1.0 / (
            1.40682e-18 * tavg_f ** 6
            - 2.69957e-15 * tavg_f ** 5
            + 2.17758e-12 * tavg_f ** 4
            - 9.15282e-10 * tavg_f ** 3
            + 2.2418e-7 * tavg_f ** 2
            - 2.3968e-5 * tavg_f
            + 0.017070952
        )
        psatwater = (
            -2.55175e-12 * tavg_f ** 5
            + 2.41218e-08 * tavg_f ** 4
            - 9.19096e-06 * tavg_f ** 3
            + 0.001969537 * tavg_f ** 2
            - 0.197885257 * tavg_f
            + 8.089410675
        )
        pressure_ratio = 0.5 * (pump_head_prod_top + psatwater) / psatwater
        rho_corrected = rho * (1.0 + (7.15037e-19 * tavg_f ** 5.91303) * (pressure_ratio - 1.0))
        viscosity = 407.22 * tavg_f ** (-1.194) / 3600.0
        viscosity_corrected = viscosity * (1.0 + (4.02401e-18 * tavg_f ** 5.736882) * (pressure_ratio - 1.0))
        velocity = (
            (self.well_flow_rate * 7936.64 / rho_corrected) / 3600.0
        ) / (math.pi * (casing_int_diameter / 12.0) ** 2 / 4.0)
        reynolds_num = rho_corrected * velocity * (casing_int_diameter / 12.0) / viscosity_corrected
        a_const = -2.0 * math.log10((surface_roughness / (casing_int_diameter / 12.0)) / 3.7 + 12.0 / reynolds_num)
        b_const = -2.0 * math.log10((surface_roughness / (casing_int_diameter / 12.0)) / 3.7 + (2.51 * a_const) / reynolds_num)
        c_const = -2.0 * math.log10((surface_roughness / (casing_int_diameter / 12.0)) / 3.7 + (2.51 * b_const) / reynolds_num)
        friction_factor = (a_const - (b_const - a_const) ** 2 / (c_const - 2.0 * b_const + a_const)) ** -2

        pavailable = (pump_head_prod_top - p_excess - psatwellhead) * 144.0
        head_friction_loss = ((friction_factor * 1.0 / (casing_int_diameter / 12.0)) * (velocity ** 2) / (2.0 * 32.174))
        head_available = (pavailable / rho_corrected) / (1.0 + head_friction_loss)
        return head_available

    def suction_depth(self, pump_head_suction: float) -> float:
        prod_thickness_ft = self.production_thickness * 3.28084
        return (self.well_depth * 3.28084) - prod_thickness_ft - pump_head_suction

    def casing_friction(self, suction_depth: float, pump_head_prod_top: float) -> float:
        if self.well_type == "Small":
            pump_casing_diameter = 7.0 - 0.944
        else:
            pump_casing_diameter = 9.625 - 0.944

        well_depth_ft = self.well_depth * 3.28084
        prod_thickness_ft = self.production_thickness * 3.28084
        column_depth = well_depth_ft - prod_thickness_ft
        res_temperature_f = self.reservoir_temperature * 1.8 + 32
        well_temp_loss_fft = self.well_temp_loss * 1.8 / 3.28083
        surface_roughness = 0.00015
        tavg_f = res_temperature_f - 0.5 * well_temp_loss_fft * column_depth
        rho = 1.0 / (
            1.40682e-18 * tavg_f ** 6
            - 2.69957e-15 * tavg_f ** 5
            + 2.17758e-12 * tavg_f ** 4
            - 9.15282e-10 * tavg_f ** 3
            + 2.2418e-7 * tavg_f ** 2
            - 2.3968e-5 * tavg_f
            + 0.017070952
        )
        psatwater = (
            -2.55175e-12 * tavg_f ** 5
            + 2.41218e-08 * tavg_f ** 4
            - 9.19096e-06 * tavg_f ** 3
            + 0.001969537 * tavg_f ** 2
            - 0.197885257 * tavg_f
            + 8.089410675
        )
        pressure_ratio = 0.5 * (pump_head_prod_top + psatwater) / psatwater
        rho_corrected = rho * (1.0 + (7.15037e-19 * tavg_f ** 5.91303) * (pressure_ratio - 1.0))
        viscosity = 407.22 * tavg_f ** (-1.194) / 3600.0
        viscosity_corrected = viscosity * (1.0 + (4.02401e-18 * tavg_f ** 5.736882) * (pressure_ratio - 1.0))
        velocity = (
            (self.well_flow_rate * 7936.64 / rho_corrected) / 3600.0
        ) / (math.pi * (pump_casing_diameter / 12.0) ** 2 / 4.0)
        reynolds_num = rho_corrected * velocity * (pump_casing_diameter / 12.0) / viscosity_corrected
        a_const = -2.0 * math.log10((surface_roughness / (pump_casing_diameter / 12.0)) / 3.7 + 12.0 / reynolds_num)
        b_const = -2.0 * math.log10((surface_roughness / (pump_casing_diameter / 12.0)) / 3.7 + (2.51 * a_const) / reynolds_num)
        c_const = -2.0 * math.log10((surface_roughness / (pump_casing_diameter / 12.0)) / 3.7 + (2.51 * b_const) / reynolds_num)
        friction_factor = (a_const - (b_const - a_const) ** 2 / (c_const - 2.0 * b_const + a_const)) ** -2
        friction_head = suction_depth * ((friction_factor * 1.0 / (pump_casing_diameter / 12.0)) * (velocity ** 2) / (2.0 * 32.174))
        return friction_head

    def pump_power(self, suction_depth: float, casing_friction_head: float) -> float:
        pump_lift = suction_depth + casing_friction_head
        pump_power_ideal = ((self.well_flow_rate * 7936.64 / 60.0) * pump_lift) / 33000.0
        if self.pump_type == "ESP":
            pump_efficiency = 0.68
        elif self.pump_type == "Lineshaft":
            pump_efficiency = 0.68
        else:
            pump_efficiency = 0.675
        pump_power_real = pump_power_ideal / pump_efficiency
        return pump_power_real * 0.7457

    def pump_cost(self, pump_power_kw: float, suction_depth: float) -> float:
        if self.pump_type == "ESP":
            pumping_unit_cost = 1500.0 * (pump_power_kw / 0.7457) ** 0.7 + 5750.0 * (pump_power_kw / 0.7457) ** 0.2
        elif self.pump_type == "Lineshaft":
            pumping_unit_cost = 1750.0 * (pump_power_kw / 0.7457) ** 0.7 + 5750.0 * (pump_power_kw / 0.7457) ** 0.2
        else:
            pumping_unit_cost = 0.8

        workover_cost = 10_000.0
        pump_casing_unit_cost = 44.74
        installation_unit_cost = 5.0
        pump_casing_cost = pump_casing_unit_cost * suction_depth
        pump_installation_cost = pump_casing_cost + workover_cost + installation_unit_cost * suction_depth
        return pumping_unit_cost * self.ppi_multiplier + pump_installation_cost

    def total_pump_duty_cost(self, pumping_power: float, pumping_cost: float):
        self.total_pumping_duty = pumping_power * self.number_production_wells
        self.total_pumping_cost = pumping_cost * self.number_production_wells
        #print(f"Total Production Pumping Cost = ${self.total_pumping_cost}")
        #print(f"Total Production Pumping Duty = {self.total_pumping_duty} kW")
        return self.total_pumping_duty, self.total_pumping_cost

    def pump_maintenance_cost(self, suction_depth: float, pumping_cost: float) -> float:
        workover_cost = 10_000.0
        pump_casing_unit_cost = 44.74
        installation_unit_cost = 5.0
        pump_casing_cost = pump_casing_unit_cost * suction_depth
        pump_installation_cost = pump_casing_cost + workover_cost + installation_unit_cost * suction_depth
        pump_replacement_unit_cost = pumping_cost - pump_installation_cost
        pump_reinstall_cost = pump_installation_cost - pump_casing_cost
        pump_rework_unit_cost = pump_replacement_unit_cost + pump_reinstall_cost

        if self.pump_type == "ESP":
            operating_life = 2.0
            lubricating_oil_unit_cost = 0.0
        elif self.pump_type == "Lineshaft":
            operating_life = 3.0
            lubricating_oil_unit_cost = 4300.0 * self.ppi_multiplier
        else:
            operating_life = 2.0
            lubricating_oil_unit_cost = 0.0

        lubricating_oil_cost = lubricating_oil_unit_cost * suction_depth / 500.0
        return (pump_rework_unit_cost * self.number_production_wells) / operating_life + lubricating_oil_cost
