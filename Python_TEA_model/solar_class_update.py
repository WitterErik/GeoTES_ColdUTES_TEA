import numpy as np 

class solar_class:
    def __init__(self,location, mirror_type, nominal_DNI, solar_multiple, Tmax, Tmin, land_mult, CSP_cost, nY)
        self.locaiton = location
        self.mirror_type = mirror_type
        self.nominal_DNI = nominal_DNI
        self.solar_multiple = solar_multiple
        self.Tmax = Tmax
        self.Tmin = Tmin
        self.land_mult = land_mult
        self.nY = nY

        # pre-allocate tracking arrays
        self.DNI = np.zeros(8760)
        self.power = np.zeros(ny * 8760)
        self.dumped = np.zeros(nY * 8760)

        # pull in cost profiles from user_inputs
        self.mirror_cost_unit = CSP_cost["mirror"]
        self.land_cost_unit = CSP_cost["land"]
        self.HX_cost_unit = CSP_cost["HX"]

        # initialize empty variables that are calculated dynamically
        self.mirror_cost = 0.0
        self.land_cost = 0.0
        self.HX_cost = 0.0
        self.total_cost = 0.0

        self.nominal_eff = 0.0
        self.annual_eff = 0.0
        self.mirror_aperture = 0.0
        self.land_area = 0.0

        self.available_solar_heat = 0.0      # GWh-th
        self.solar_thermal_generated = 0.0    # GWh-th
        self.total_dumped = 0.0               # GWh-th

        def CSP_annual_energy(self):
            # calculate annual solar thermal energy generated and dumped for final year
            start_hour = (self.nY - 1) * 8760
            end_hour = self.nY * 8760

            # calculate thermal energy balances
            self.available_solar_heat = np.sum(self.DNI) * self.mirror_aperture / 1e9

            # slice the array for the final year and sum the values
            final_year_power = self.power[start_hour:end_hour]
            self.solar_thermal_generated = np.sum(final_year_power) / 1000

            final_year_dumped = self.dumped[start_hour:end_hour]
            self.total_dumped = np.zum(final_year_dumped) / 1000

        def calc_CSP_cost(self,PC):
            # calculate captial expenditures of solar collector

            self.mirror_cost = self.mirror_cost_unit * self.mirror_aperture
            self.land_cost = self.land_cost_unit * self.land_area
            self.HX_cost = self.HX_cost_unit * PC.Qin0 * 1000
        
            self.total_cost = self.mirror_cost + self.land_cost + self.HX_cost
            