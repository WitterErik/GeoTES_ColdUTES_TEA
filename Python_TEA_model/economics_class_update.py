import numpy as np

class economics_class:
    """
    Solves Weighted Average Cost of Capital (WACC), Fixed Charge Rate (FCR), 
    and Levelized Cost profiles (LCOE, LCOS, LCOH) using SAM-aligned economic models.
    """
    def __init__(self, inputs):
        # 1. Parse high-level economic inputs from configuration dictionaries
        # (Using .get() with fallback defaults matching standard assumptions)
        self.lifetime = inputs.get("lifetime", 50)
        self.elec_price = inputs.get("elec_price", 0.05)
        self.inflation = inputs.get("inflation", 0.025)
        self.irr = inputs.get("irr", 0.10)
        self.debt_frac = inputs.get("debt_frac", 0.60)
        self.debt_IR = inputs.get("debt_ir", 0.08)  # Accommodates both capitalizations
        self.tax_rate = inputs.get("tax_rate", 0.28)
        self.deprec = inputs.get("deprec", [0.20, 0.32, 0.20, 0.14, 0.14])
        self.annual_cost = inputs.get("annual_cost", [1.0, 0.0, 0.0])
        self.construc_IR = inputs.get("construc_ir", 0.0)
        self.OnM = inputs.get("onm_rate", inputs.get("OnM", 0.015))  # Accommodates both capitalizations
        self.ITC = inputs.get("itc_rate", inputs.get("ITC", 0.4))

        # 2. Initialize internal parameter tracking properties
        self.RROE = 0.0
        self.RINT = 0.0
        self.WACC = 0.0
        self.CRF = 0.0
        self.PVDEP = 0.0
        self.PFF = 0.0
        self.CFF = 0.0
        self.FCR = 0.0

        self.Ein = 0.0   # Annual electricity inputs, GWh
        self.Eout = 0.0  # Annual electricity generation outputs, GWh
        self.Qout = 0.0  # Annual thermal heat outputs, GWh

        self.surface_capital_cost = 0.0
        self.subsurface_capital_cost = 0.0
        self.total_capital_cost = 0.0
        self.total_capital_cost_ITC = 0.0

        self.OnM_surface = 0.0
        self.OnM_subsurface = 0.0
        self.OnM_total = 0.0

        # Revenue and operations parameters (Dynamic placeholders)
        self.charge_cost = 0.0
        self.discharge_revenue = 0.0
        self.net_revenue = 0.0
        self.elec_cost = 0.0
        self.elec_price_hourly = np.zeros(8760)

        # Levelized Output Metrics
        self.LCOE, self.LCOE_ITC = 0.0, 0.0
        self.LCOS, self.LCOS_ITC = 0.0, 0.0
        self.LCOH, self.LCOH_ITC = 0.0, 0.0

    def calc_fcr(self):
        """
        Calculates Fixed Charge Rate (FCR) based on Weighted Average Cost of Capital (WACC),
        Capital Recovery Factor (CRF), and present values of depreciation schedule cash flows.
        """
        self.RROE = (1.0 + self.irr) / (1.0 + self.inflation) - 1.0
        self.RINT = (1.0 + self.debt_IR) / (1.0 + self.inflation) - 1.0
        
        # Calculate nominal WACC
        self.WACC = ((1.0 + self.inflation) * (1.0 + self.RROE) - 1) * (1.0 - self.debt_frac) + 1.0
        self.WACC += self.debt_frac * ((1.0 + self.RINT) * (1.0 + self.inflation) - 1.0) * (1.0 - self.tax_rate)
        self.WACC = self.WACC / (1.0 + self.inflation) - 1.0

        # Capital Recovery Factor
        self.CRF = self.WACC / (1.0 - (1.0 / (1.0 + self.WACC)**self.lifetime))

        # Present Value of Depreciation (PVDEP)
        # Note: Exponent is set to (i + 1) to offset Python's 0-based range indexing
        self.PVDEP = 0.0
        for i in range(len(self.deprec)):
            self.PVDEP += self.deprec[i] / (((1.0 + self.WACC) * (1.0 + self.inflation)) ** (i + 1))

        # Project Financing Factor (PFF)
        self.PFF = (1.0 - self.tax_rate * self.PVDEP) / (1.0 - self.tax_rate)

        # Construction Financing Factor (CFF)
        # Note: Exponent adjusts to (i + 1) to replicate MATLAB's (1 to N) compounding cash flows
        self.CFF = 0.0
        for i in range(len(self.annual_cost)):
            year_val = i + 1
            compounding_term = ((1.0 + self.construc_IR) ** (year_val - 0.5) - 1.0) * (1.0 - self.tax_rate) + 1.0
            self.CFF += compounding_term * self.annual_cost[i]

        # Overall Fixed Charge Rate (FCR)
        self.FCR = self.CRF * self.PFF * self.CFF

    def calc_levelized_cost(self, mode):
        """
        Calculates LCOE, LCOS, or LCOH based on target mode inputs.
        """
        self.total_capital_cost = self.surface_capital_cost + self.subsurface_capital_cost
        self.total_capital_cost_ITC = (1.0 - self.ITC) * self.total_capital_cost
        self.OnM_total = self.OnM_surface + self.OnM_subsurface

        # 1. Resolve charging electricity fuel costs
        # Safely checks if charge_cost exists and is positive
        charge_cost_val = getattr(self, 'charge_cost', 0.0)
        if charge_cost_val > 0:
            self.elec_cost = charge_cost_val
        else:
            # Estimate from standard mean utility electricity pricing (converted GWh to kWh-equivalent scale)
            self.elec_cost = self.elec_price * self.Ein * 1e6

        # 2. Dispatch Levelizer Calculations
        denominator = self.Eout * 1e6 if mode in ['E', 'S'] else self.Qout * 1e6
        
        # Avoid division-by-zero checks on un-executed simulations
        if denominator == 0:
            return

        capital_charge_base = self.total_capital_cost * self.FCR
        capital_charge_itc = self.total_capital_cost * self.FCR * (1.0 - self.ITC)

        if mode == 'E':
            self.LCOE = (capital_charge_base + self.OnM_total + self.elec_cost) / denominator
            self.LCOE_ITC = (capital_charge_itc + self.OnM_total + self.elec_cost) / denominator
        elif mode == 'S':
            self.LCOS = (capital_charge_base + self.OnM_total + self.elec_cost) / denominator
            self.LCOS_ITC = (capital_charge_itc + self.OnM_total + self.elec_cost) / denominator
        elif mode == 'H':
            self.LCOH = (capital_charge_base + self.OnM_total + self.elec_cost) / denominator
            self.LCOH_ITC = (capital_charge_itc + self.OnM_total + self.elec_cost) / denominator

    def calc_revenue(self, Win, Wout):
        """
        Calculates dynamic hourly charging expenses, discharging revenues, 
        and net arbitrage revenue margins based on custom electric tariff arrays.
        """
        # Element-by-element vector multiplication in NumPy is written with simple * operators
        self.charge_cost_hourly = self.elec_price_hourly * Win
        self.discharge_revenue_hourly = self.elec_price_hourly * Wout

        self.charge_cost = np.sum(self.charge_cost_hourly)
        self.discharge_revenue = np.sum(self.discharge_revenue_hourly)
        self.net_revenue = self.discharge_revenue - self.charge_cost