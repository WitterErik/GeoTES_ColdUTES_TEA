import math

import numpy as np

from fluid_class import fluid_class


class geoTES_class:
    def __init__(self, recovery, Tinit, flowrate, Qmax, props, fluid, nY=2):
        self.recovery = float(recovery)
        self.Tinit = float(Tinit)
        self.flowrate_per_well = float(flowrate)
        self.Qmax = float(Qmax)
        self.nY = int(nY)

        self.rho = float(props["rho"])
        self.cp = float(props["cp"])
        self.void = float(props["void"])

        self.charge_production = fluid_class(fluid)
        self.charge_injection = fluid_class(fluid)
        self.discharge_production = fluid_class(fluid)
        self.discharge_injection = fluid_class(fluid)

        self.charge_prod_Nwell = 0
        self.charge_inj_Nwell = 0
        self.discharge_prod_Nwell = 0
        self.discharge_inj_Nwell = 0

        self.power = np.zeros(self.nY * 8760, dtype=float)
        self.energy = np.zeros(self.nY * 8760, dtype=float)

        self.energy_in_tot = 0.0
        self.energy_out_tot = 0.0
        self.eff = 0.0
        self.energy_capacity = 0.0
        self.mass = 0.0
        self.volume = 0.0
        self.side_length = 0.0
        self.net_energy = 0.0

    def geoTES_size(self):
        hours = 8760
        hours2 = self.nY * hours
        start = (self.nY - 1) * hours

        if self.charge_injection.T > self.charge_production.T:
            self.energy_capacity = np.max(self.energy[start:hours2]) / 1000.0
        else:
            self.energy_capacity = -np.min(self.energy[start:hours2]) / 1000.0

        en_cap_J = self.energy_capacity * 3600e9
        self.mass = en_cap_J / (self.cp * abs(self.charge_injection.T - self.charge_production.T))
        self.volume = self.mass / self.rho / (1.0 - self.void)
        self.side_length = self.volume ** (1.0 / 3.0)
        self.net_energy = (self.energy[hours2 - 1] - self.energy[(self.nY - 1) * hours]) / 1000.0

        return self

    def geoTES_well_flows(self):
        hours = 8760
        hours2 = 2 * hours

        if self.charge_injection.T > self.charge_production.T:
            max_charge_power = np.max(self.power[hours:hours2])
            max_discharge_power = -np.min(self.power[hours:hours2])
        else:
            max_charge_power = -np.min(self.power[hours:hours2])
            max_discharge_power = np.max(self.power[hours:hours2])

        if max_charge_power == 0.0:
            self.charge_production.mdot = 0.0
            self.charge_injection.mdot = 0.0
        else:
            self.charge_production.mdot = (
                max_charge_power * 1000.0 / abs(self.charge_injection.h - self.charge_production.h)
            )
            self.charge_injection.mdot = self.charge_production.mdot

        self.charge_injection.calc_mdot_vdot("vdot")
        self.charge_production.calc_mdot_vdot("vdot")

        if max_discharge_power == 0.0:
            self.discharge_production.mdot = 0.0
            self.discharge_injection.mdot = 0.0
        else:
            self.discharge_production.mdot = (
                max_discharge_power * 1000.0 / abs(self.discharge_injection.h - self.discharge_production.h)
            )
            self.discharge_injection.mdot = self.discharge_production.mdot

        self.discharge_injection.calc_mdot_vdot("vdot")
        self.discharge_production.calc_mdot_vdot("vdot")

        self.charge_prod_Nwell = int(
            math.ceil(self.charge_production.vdot * 1000.0 / self.flowrate_per_well)
        )
        self.charge_inj_Nwell = int(
            math.ceil(self.charge_injection.vdot * 1000.0 / self.flowrate_per_well)
        )
        self.discharge_prod_Nwell = int(
            math.ceil(self.discharge_production.vdot * 1000.0 / self.flowrate_per_well)
        )
        self.discharge_inj_Nwell = int(
            math.ceil(self.discharge_injection.vdot * 1000.0 / self.flowrate_per_well)
        )

        return self

    def geoTES_annual_energy(self):
        hours = 8760
        hours2 = self.nY * hours
        start = (self.nY - 1) * hours
        pow_slice = self.power[start:hours2]

        self.energy_in_tot = float(np.sum(pow_slice[pow_slice > 0]) / 1000.0)
        self.energy_out_tot = float(-np.sum(pow_slice[pow_slice < 0]) / 1000.0)
        self.eff = self.energy_out_tot / self.energy_in_tot if self.energy_in_tot != 0 else 0.0

        return self
