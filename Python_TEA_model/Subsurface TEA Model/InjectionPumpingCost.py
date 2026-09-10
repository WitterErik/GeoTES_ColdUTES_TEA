import math


class InjectionPumpingCost:
    """Estimate injection pumping duty and cost for subsurface injection wells."""

    def __init__(
        self,
        reservoir_temperature,
        injection_temperature,
        injection_flow_rate,
        production_flow_rate,
        pressure_thermal_source,
        number_injection_wells,
        injectivity,
        depth,
        production_thickness,
        well_type,
        completion,
        ppi_multiplier,
        operation_mode,
    ):
        self.reservoir_temperature = float(reservoir_temperature)
        self.injection_temperature = float(injection_temperature)
        self.injection_flow_rate = float(injection_flow_rate)
        self.production_flow_rate = float(production_flow_rate)
        self.pressure_thermal_source = float(pressure_thermal_source)
        self.number_injection_wells = int(number_injection_wells)
        self.well_injectivity = float(injectivity)
        self.well_depth = float(depth)
        self.production_thickness = float(production_thickness)
        self.well_type = str(well_type)
        self.completion = str(completion)
        self.well_temp_loss = 0.0005
        self.ppi_multiplier = float(ppi_multiplier)
        self.operation_mode = str(operation_mode)
        self.total_pumping_duty = 0.0
        self.total_pumping_cost = 0.0

    def head_suction(self) -> float:
        if self.well_type == "Small":
            casing_int_diameter = 9.625 - (2 * 0.4375)
        else:
            casing_int_diameter = 13.625 - (2 * 0.5625)

        well_depth_ft = self.well_depth * 3.28084
        prod_thickness_ft = self.production_thickness * 3.28084
        column_depth = well_depth_ft - prod_thickness_ft
        res_temperature_f = self.reservoir_temperature * 1.8 + 32
        inj_temperature_f = self.injection_temperature * 1.8 + 32
        well_temp_loss_fft = self.well_temp_loss * 1.8 / 3.28083
        prod_inj_ratio = self.production_flow_rate / self.injection_flow_rate
        p_excess = 50.0
        delta_p_plant = 40.0

        twellhead = res_temperature_f - well_temp_loss_fft * well_depth_ft
        psatwellhead = (
            -2.55175e-12 * twellhead ** 5
            + 2.41218e-08 * twellhead ** 4
            - 9.19096e-06 * twellhead ** 3
            + 0.001969537 * twellhead ** 2
            - 0.197885257 * twellhead
            + 8.089410675
        )

        if self.operation_mode == "Charge":
            pwellhead = self.pressure_thermal_source
        else:
            pwellhead = psatwellhead + p_excess - delta_p_plant

        surface_roughness = 0.00015
        tavg_f = inj_temperature_f + (0.5 * well_temp_loss_fft * prod_inj_ratio * column_depth)
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
        pressure_ratio = 0.5 * ((rho * column_depth / 144.0) + pwellhead) / psatwater
        rho_corrected = rho * (1.0 + (7.15037e-19 * tavg_f ** 5.91303) * (pressure_ratio - 1.0))
        viscosity = 407.22 * tavg_f ** (-1.194) / 3600.0
        viscosity_corrected = viscosity * (1.0 + (4.02401e-18 * tavg_f ** 5.736882) * (pressure_ratio - 1.0))
        velocity = (
            (self.injection_flow_rate * 7936.64 / rho_corrected) / 3600.0
        ) / (math.pi * (casing_int_diameter / 12.0) ** 2 / 4.0)
        reynolds_num = rho_corrected * velocity * (casing_int_diameter / 12.0) / viscosity_corrected
        a_const = -2.0 * math.log10((surface_roughness / (casing_int_diameter / 12.0)) / 3.7 + 12.0 / reynolds_num)
        b_const = -2.0 * math.log10((surface_roughness / (casing_int_diameter / 12.0)) / 3.7 + (2.51 * a_const) / reynolds_num)
        c_const = -2.0 * math.log10((surface_roughness / (casing_int_diameter / 12.0)) / 3.7 + (2.51 * b_const) / reynolds_num)
        friction_factor = (a_const - (b_const - a_const) ** 2 / (c_const - 2.0 * b_const + a_const)) ** -2
        head_friction_loss = ((friction_factor * 1.0 / (casing_int_diameter / 12.0)) * (velocity ** 2) / (2.0 * 32.174))
        p_friction_loss = head_friction_loss * column_depth * rho_corrected / 144.0
        return pwellhead + rho_corrected * column_depth / 144.0 - p_friction_loss

    def head_injection(self, pump_head_suction: float) -> float:
        if self.well_type == "Small" and self.completion == "Openhole":
            well_diameter = 8.5
        elif self.well_type == "Small" and self.completion == "Liner":
            well_diameter = 7.0
        elif self.well_type == "Large" and self.completion == "Openhole":
            well_diameter = 12.25
        else:
            well_diameter = 9.625

        well_depth_ft = self.well_depth * 3.28084
        prod_thickness_ft = self.production_thickness * 3.28084
        column_depth = well_depth_ft - prod_thickness_ft
        inj_temperature_f = self.injection_temperature * 1.8 + 32
        well_temp_loss_fft = self.well_temp_loss * 1.8 / 3.28083
        prod_inj_ratio = self.production_flow_rate / self.injection_flow_rate
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
        phydrostatic = p_surf + 1.0 / cp * (math.exp(rho_surf * 9.807 * cp * (self.well_depth - (0.5 * ct * tau_t * self.well_depth ** 2)) / 100000.0) - 1.0)
        phydropsi = 14.50377 * phydrostatic
        buildup = self.injection_flow_rate * 7936.64 / self.well_injectivity

        tavg_f = inj_temperature_f + (well_temp_loss_fft * prod_inj_ratio * (column_depth + 0.5 * prod_thickness_ft))
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
        pressure_ratio = (pump_head_suction + 0.5 * rho * prod_thickness_ft / 144.0) / psatwater
        rho_corrected = rho * (1.0 + (7.15037e-19 * tavg_f ** 5.91303) * (pressure_ratio - 1.0))
        viscosity = 407.22 * tavg_f ** (-1.194) / 3600.0
        viscosity_corrected = viscosity * (1.0 + (4.02401e-18 * tavg_f ** 5.736882) * (pressure_ratio - 1.0))
        velocity = (
            (self.injection_flow_rate * 7936.64 / rho_corrected) / 3600.0
        ) / (math.pi * (well_diameter / 12.0) ** 2 / 4.0)
        reynolds_num = rho * velocity * (well_diameter / 12.0) / viscosity_corrected
        a_const = -2.0 * math.log10((surface_roughness / (well_diameter / 12.0)) / 3.7 + 12.0 / reynolds_num)
        b_const = -2.0 * math.log10((surface_roughness / (well_diameter / 12.0)) / 3.7 + (2.51 * a_const) / reynolds_num)
        c_const = -2.0 * math.log10((surface_roughness / (well_diameter / 12.0)) / 3.7 + (2.51 * b_const) / reynolds_num)
        friction_factor = (a_const - (b_const - a_const) ** 2 / (c_const - 2.0 * b_const + a_const)) ** -2
        head_friction_loss = ((friction_factor * 1.0 / (well_diameter / 12.0)) * (velocity ** 2) / (2.0 * 32.174))
        p_bottom_hole_no_pumping = pump_head_suction + rho_corrected * prod_thickness_ft / 144.0 - head_friction_loss
        excess_pressure = p_bottom_hole_no_pumping - phydropsi

        if excess_pressure - buildup > 1.0:
            inj_pump_head = 1.0
        else:
            inj_pump_head = buildup + 1.0 - excess_pressure

        rho_inj = 1.0 / (
            1.40682e-18 * inj_temperature_f ** 6
            - 2.69957e-15 * inj_temperature_f ** 5
            + 2.17758e-12 * inj_temperature_f ** 4
            - 9.15282e-10 * inj_temperature_f ** 3
            + 2.2418e-7 * inj_temperature_f ** 2
            - 2.3968e-5 * inj_temperature_f
            + 0.017070952
        )
        return inj_pump_head * 144.0 / rho_inj

    def pump_power(self, pump_head_injection: float) -> float:
        pump_power_ideal = (
            (self.injection_flow_rate * 7936.64 * self.number_injection_wells) * pump_head_injection
        ) / (60.0 * 33000.0)
        pump_efficiency = 0.68
        pump_power_real = pump_power_ideal / pump_efficiency
        return pump_power_real * 0.7457

    def pump_cost(self, pumping_power: float) -> float:
        pump_units = (pumping_power / 0.7457) / math.ceil(pumping_power / 2000.0)
        if pumping_power / 0.7457 < 2000.0:
            pumping_unit_cost = 1750.0 * (pumping_power / 0.7457) ** 0.7 + 3.0 * (pumping_power / 0.7457) ** -0.11
        else:
            pumping_unit_cost = pump_units * (
                1750.0 * ((pumping_power / 0.7457) / pump_units) ** 0.7
                + 3.0 * ((pumping_power / 0.7457) / pump_units) ** -0.11
            )
        return pumping_unit_cost * self.ppi_multiplier

    def total_pump_duty_cost(self, pumping_power: float, pumping_cost: float):
        self.total_pumping_duty = pumping_power
        self.total_pumping_cost = pumping_cost * self.number_injection_wells
        #print(f"Total Injection Pumping Cost = ${self.total_pumping_cost}")
        #print(f"Total Injection Pumping Duty = {self.total_pumping_duty} kW")
        return self.total_pumping_duty, self.total_pumping_cost
