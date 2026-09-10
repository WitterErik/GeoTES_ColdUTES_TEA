import numpy as np


class solar_class:
    def __init__(
        self,
        location,
        mirror_type,
        nominal_DNI,
        solar_multiple,
        initial_size,
        Tmax,
        Tmin,
        land_mult,
        CSP_cost,
        nY=2,
    ):
        self.location = location
        self.mirror_type = mirror_type
        self.nominal_DNI = float(nominal_DNI)
        self.solar_multiple = float(solar_multiple)
        self.initial_size = float(initial_size)
        self.Tmax = float(Tmax)
        self.Tmin = float(Tmin)

        self.land_mult = float(land_mult)
        self.nY = int(nY)

        self.DNI = np.zeros(8760, dtype=float)
        self.power = np.zeros(self.nY * 8760, dtype=float)
        self.dumped = np.zeros(self.nY * 8760, dtype=float)

        self.mirror_cost_unit = float(CSP_cost["mirror"])
        self.land_cost_unit = float(CSP_cost["land"])
        self.HX_cost_unit = float(CSP_cost["HX"])

        self.mirror_cost = 0.0
        self.land_cost = 0.0
        self.HX_cost = 0.0
        self.total_cost = 0.0

        self.nominal_eff = 0.0
        self.annual_eff = 0.0
        self.mirror_aperture = 0.0
        self.land_area = 0.0

        self.available_solar_heat = 0.0
        self.solar_thermal_generated = 0.0
        self.total_dumped = 0.0

    def CSP_annual_energy(self):
        hours = 8760
        hours2 = self.nY * hours
        start = (self.nY - 1) * hours

        self.available_solar_heat = float(np.sum(self.DNI) * self.mirror_aperture / 1e9)
        self.solar_thermal_generated = float(np.sum(self.power[start:hours2]) / 1000.0)
        self.total_dumped = float(np.sum(self.dumped[start:hours2]) / 1000.0)

        return self

    def calc_CSP_cost(self, PC):
        self.mirror_cost = self.mirror_cost_unit * self.mirror_aperture
        self.land_cost = self.land_cost_unit * self.land_area
        self.HX_cost = self.HX_cost_unit * PC.Qin0 * 1000.0
        self.total_cost = self.mirror_cost + self.land_cost + self.HX_cost
        return self
