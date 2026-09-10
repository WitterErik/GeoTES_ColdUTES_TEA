import math

import numpy as np

from fluid_class import fluid_class

# NOTE: This module assumes a Python equivalent of calc_fluid_props is defined
# in the same package and imported where this class is used.


class TES_class:
    def __init__(
        self,
        duration,
        PC_Qin,
        fluid,
        Thot,
        Tcld,
        tau,
        max_tank_vol,
        ins,
        TES_cost,
    ):
        self.duration = float(duration)
        self.power_out = float(PC_Qin)
        self.hot_fluid = fluid_class(fluid)
        self.cold_fluid = fluid_class(fluid)
        self.hot_fluid.T = float(Thot)
        self.cold_fluid.T = float(Tcld)
        self.tau = float(tau)
        self.max_tank_vol = float(max_tank_vol)

        self.power = np.zeros(2 * 8760, dtype=float)
        self.energy = np.zeros(2 * 8760, dtype=float)

        self.ins_k = float(ins["k"])
        self.ins_rho = float(ins["rho"])

        self.fluid_cost_unit = float(TES_cost["fluid"])
        self.tank_cost_corr = float(TES_cost["tank"])
        self.insulation_cost_unit = float(TES_cost["insulation"])

        self.energy_capacity = self.duration * self.power_out

        self.energy_in_tot = 0.0
        self.energy_out_tot = 0.0
        self.eff = 0.0

        self.fluid_mass = 0.0
        self.tank1_volume = 0.0
        self.tank2_volume = 0.0
        self.Ntank1 = 1
        self.Ntank2 = 1

        self.ins1_volume = 0.0
        self.ins2_volume = 0.0

        self.fluid_cost = 0.0
        self.tank1_cost = 0.0
        self.tank2_cost = 0.0
        self.insulation1_cost = 0.0
        self.insulation2_cost = 0.0
        self.total_cost = 0.0

    def tank_sizes(self):
        self.hot_fluid.calc_fluid_props("T")
        self.cold_fluid.calc_fluid_props("T")

        self.fluid_mass = (
            self.energy_capacity * 3600e3
            / (
                self.hot_fluid.cp * self.hot_fluid.T
                - self.cold_fluid.cp * self.cold_fluid.T
            )
        )

        self.tank1_volume = 1.1 * self.fluid_mass / self.hot_fluid.rho
        self.tank2_volume = 1.1 * self.fluid_mass / self.cold_fluid.rho

        if self.tank1_volume > self.max_tank_vol:
            self.Ntank1 = int(math.ceil(self.tank1_volume / self.max_tank_vol))
            self.tank1_volume = self.tank1_volume / self.Ntank1
        else:
            self.Ntank1 = 1

        if self.tank2_volume > self.max_tank_vol:
            self.Ntank2 = int(math.ceil(self.tank2_volume / self.max_tank_vol))
            self.tank2_volume = self.tank2_volume / self.Ntank2
        else:
            self.Ntank2 = 1

        phi = 1.0
        AD = (4.0 * self.tank1_volume / (math.pi * phi)) ** (1.0 / 3.0)
        AR = 0.5 * AD
        AL = AD * phi
        AA = math.pi * AD * (AL + AD / 4.0)
        AA = 8.0 * AA / 5.0

        tau_s = self.tau * 24.0 * 3600.0
        UA = self.tank1_volume * self.hot_fluid.rho * self.hot_fluid.cp / (tau_s * AA)

        tins = AR * (math.exp(self.ins_k / (AR * UA)) - 1.0)
        self.ins1_volume = math.pi * tins * (2.0 + tins) * AL
        self.ins1_volume += 2.0 * math.pi * tins * (AR + tins) ** 2

        AD = (4.0 * self.tank2_volume / (math.pi * phi)) ** (1.0 / 3.0)
        AR = 0.5 * AD
        AL = AD * phi
        AA = math.pi * AD * (AL + AD / 4.0)
        AA = 8.0 * AA / 5.0

        tau_s = self.tau * 24.0 * 3600.0
        UA = self.tank2_volume * self.cold_fluid.rho * self.cold_fluid.cp / (tau_s * AA)

        tins = AR * (math.exp(self.ins_k / (AR * UA)) - 1.0)
        self.ins2_volume = math.pi * tins * (2.0 + tins) * AL
        self.ins2_volume += 2.0 * math.pi * tins * (AR + tins) ** 2

        return self

    def TES_annual_energy(self):
        hours = 8760
        hours2 = 2 * hours
        power_slice = self.power[hours:hours2]

        self.energy_in_tot = float(np.sum(power_slice[power_slice > 0]) / 1000.0)
        self.energy_out_tot = float(-np.sum(power_slice[power_slice < 0]) / 1000.0)
        self.eff = self.energy_out_tot / self.energy_in_tot if self.energy_in_tot != 0.0 else 0.0

        return self

    def calc_TES_cost(self):
        self.fluid_cost = self.fluid_cost_unit * self.fluid_mass
        self.insulation1_cost = self.insulation_cost_unit * self.ins1_volume * self.Ntank1
        self.insulation2_cost = self.insulation_cost_unit * self.ins2_volume * self.Ntank2

        if self.tank_cost_corr == 0.0:
            self.tank1_cost = 3829.0 * self.tank1_volume ** 0.557 * self.Ntank1
            self.tank2_cost = 3829.0 * self.tank2_volume ** 0.557 * self.Ntank2
        else:
            raise NotImplementedError("Tank cost correction mode not implemented")

        self.total_cost = (
            self.fluid_cost
            + self.insulation1_cost
            + self.insulation2_cost
            + self.tank1_cost
            + self.tank2_cost
        )

        return self
