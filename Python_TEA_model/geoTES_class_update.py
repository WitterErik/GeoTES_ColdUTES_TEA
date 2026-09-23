import numpy as np

class geoTES_class:
    def __init__(self, recovery, Tinit, flowrate, Qmax, props, fluid, mode, nY)

        self.recovery = recovery
        self.Tinit = Tinit
        self.nY = nY
        self.mode = mode
        self.Qmax = Qmax 

        # flow rate parsing
        if isinstance(flowrate, dict):
            self.flowrate_per_well_inj = flowrate.get("I",0.0)
            self.flowrate_per_well_prod = flowrate.get("P",0.0)
        else:
            self.flowrate_per_well_inj = flowrate
            self.flowrate_per_well_prod = flowrate

        self.rho = props.get("rho",0.0)
        self.cp = props.get("cp", 0.0)
        self.void = props.get("void", 0.0)
        self.depth = props.get("depth",0.0)
        self.thickness = props.get("thickeness",0.0)

        # injectivity and productivity properties
        self.productivity = props.get("productivity",0.0)
        self.injectivity = props.get("injectivity",0.0)

        # dynamic boundaries and working fluid classes
        try:
            from fluid_properties import fluid_class
            self.charge_production = fluid_class(fluid)
            self.charge_injection = fluid_class(fluid)
            self.discharge_production = fluid_class(fluid)
            self.discharge_injection = fluid_class(fluid)
        except ImportError:
            print("⚠️ fluid_class import failed. Instantiating basic state placeholders.")
            # Default placeholder object so dot notation works
            class BasicFluidPlaceholder:
                def __init__(self):
                    self.T, self.p, self.q, self.rho, self.h = 0.0, 0.0, 0.0, 0.0, 0.0
                    self.mdot, self.vdot = 0.0, 0.0
            self.charge_production = BasicFluidPlaceholder()
            self.charge_injection = BasicFluidPlaceholder()
            self.discharge_production = BasicFluidPlaceholder()
            self.discharge_injection = BasicFluidPlaceholder()

        # Pre-allocate tracking arrays using NumPy
        self.power = np.zeros(nY * 8760)
        self.energy = np.zeros(nY * 8760)

        # Placeholder fields for dynamically calculated properties
        self.energy_capacity = 0.0
        self.mass = 0.0
        self.volume = 0.0
        self.side_length = 0.0
        self.net_energy = 0.0

        self.charge_prod_Nwell = 0
        self.charge_inj_Nwell = 0
        self.discharge_prod_Nwell = 0
        self.discharge_inj_Nwell = 0

        self.energy_in_tot = 0.0
        self.energy_out_tot = 0.0
        self.eff = 0.0

    def geoTES_size(self):
        """
        Calculates physical sizing, mass, and volumetric bounds of the geo-TES.
        Saves values in-place directly to self.
        """
        start_hour = (self.nY - 1) * 8760
        end_hour = self.nY * 8760
        final_year_energy = self.energy[start_hour:end_hour]

        # Max/min evaluation matching original conditional check
        if self.charge_injection.T > self.charge_production.T:
            self.energy_capacity = np.max(final_year_energy) / 1000.0
        else:
            self.energy_capacity = -np.min(final_year_energy) / 1000.0

        # Energy Capacity in Joules
        en_cap_J = self.energy_capacity * 3600e9
        
        # Avoid division-by-zero errors in case temperature difference is 0
        temp_diff = abs(self.charge_injection.T - self.charge_production.T)
        if temp_diff > 0:
            self.mass = en_cap_J / (self.cp * temp_diff)
        else:
            self.mass = 0.0

        self.volume = self.mass / self.rho / (1 - self.void)
        self.side_length = self.volume ** (1/3)

        # Net change in reservoir energy content over the final year (GWh-th)
        self.net_energy = (self.energy[end_hour - 1] - self.energy[start_hour]) / 1000.0

    def geoTES_well_flows(self):
        """
        Determines peak mass and volumetric fluid flow rates, calculating
        required active and backup production/injection well counts.
        """
        start_hour = (self.nY - 1) * 8760
        end_hour = self.nY * 8760
        final_year_power = self.power[start_hour:end_hour]

        # Determine peak charging/discharging thermal capacities
        if self.charge_injection.T > self.charge_production.T:
            max_charge_power = np.max(final_year_power)
            max_discharge_power = -np.min(final_year_power)
        else:
            max_charge_power = -np.min(final_year_power)
            max_discharge_power = np.max(final_year_power)

        # Import property calculator helper
        try:
            from fluid_properties import calc_mdot_vdot
        except ImportError:
            # Fallback helper function in case it is not located yet
            def calc_mdot_vdot(fluid, mode):
                # mdot is converted to volume flow vdot using densities (rho)
                if fluid.rho > 0:
                    fluid.vdot = fluid.mdot / fluid.rho
                return fluid

        # 1. Evaluate Charging flows
        if max_charge_power == 0:
            self.charge_production.mdot = 0.0
            self.charge_injection.mdot = 0.0
            self.charge_production.vdot = 0.0
            self.charge_injection.vdot = 0.0
        else:
            h_diff_charge = abs(self.charge_injection.h - self.charge_production.h)
            self.charge_production.mdot = (max_charge_power * 1000.0 / h_diff_charge) if h_diff_charge > 0 else 0.0
            self.charge_injection.mdot = self.charge_production.mdot
            
            self.charge_injection = calc_mdot_vdot(self.charge_injection, 'vdot')
            self.charge_production = calc_mdot_vdot(self.charge_production, 'vdot')

        # 2. Evaluate Discharging flows
        if max_discharge_power == 0:
            self.discharge_production.mdot = 0.0
            self.discharge_injection.mdot = 0.0
            self.discharge_production.vdot = 0.0
            self.discharge_injection.vdot = 0.0
        else:
            h_diff_discharge = abs(self.discharge_injection.h - self.discharge_production.h)
            self.discharge_production.mdot = (max_discharge_power * 1000.0 / h_diff_discharge) if h_diff_discharge > 0 else 0.0
            self.discharge_injection.mdot = self.discharge_production.mdot
            
            self.discharge_injection = calc_mdot_vdot(self.discharge_injection, 'vdot')
            self.discharge_production = calc_mdot_vdot(self.discharge_production, 'vdot')

        # 3. Solve required well counts (ceil returns integer)
        # Multiplying vdot (m3/s) by 1000 converts to liters/sec (L/s)
        self.charge_prod_Nwell = int(np.ceil(self.charge_production.vdot * 1000.0 / self.flowrate_per_well_prod))
        self.charge_inj_Nwell = int(np.ceil(self.charge_injection.vdot * 1000.0 / self.flowrate_per_well_inj))
        self.discharge_prod_Nwell = int(np.ceil(self.discharge_production.vdot * 1000.0 / self.flowrate_per_well_prod))
        self.discharge_inj_Nwell = int(np.ceil(self.discharge_injection.vdot * 1000.0 / self.flowrate_per_well_inj))

    def geoTES_annual_energy(self):
        """Calculates total annual thermal input/output energy and thermal round-trip efficiency."""
        start_hour = (self.nY - 1) * 8760
        end_hour = self.nY * 8760
        pow_final_year = self.power[start_hour:end_hour]

        # Extract sums of incoming (positive) and outgoing (negative) powers
        incoming_power = pow_final_year[pow_final_year > 0]
        outgoing_power = pow_final_year[pow_final_year < 0]

        self.energy_in_tot = np.sum(incoming_power) / 1000.0
        self.energy_out_tot = -np.sum(outgoing_power) / 1000.0

        # Prevent division by zero if no energy is input
        self.eff = (self.energy_out_tot / self.energy_in_tot) if self.energy_in_tot > 0 else 0.0