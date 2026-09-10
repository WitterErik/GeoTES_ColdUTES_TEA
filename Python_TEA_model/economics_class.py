import numpy as np
import matplotlib.pyplot as plt


class economics_class:
    def __init__(self, inputs):
        get = inputs.get if isinstance(inputs, dict) else lambda key: getattr(inputs, key)

        self.lifetime = float(get("lifetime"))
        self.elec_price = float(get("elec_price"))
        self.inflation = float(get("inflation"))
        self.irr = float(get("irr"))
        self.debt_frac = float(get("debt_frac"))
        self.debt_IR = float(get("debt_IR"))
        self.tax_rate = float(get("tax_rate"))
        self.deprec = np.array(get("deprec"), dtype=float)
        self.annual_cost = np.array(get("annual_cost"), dtype=float)
        self.construc_IR = float(get("construc_IR"))
        self.OnM = float(get("OnM"))

        self.RROE = 0.0
        self.RINT = 0.0
        self.WACC = 0.0
        self.CRF = 0.0
        self.PVDEP = 0.0
        self.PFF = 0.0
        self.CFF = 0.0

        self.elec_price_hourly = None
        self.median_price = None
        self.charge_price = None
        self.discharge_price = None

        self.charge_cost_hourly = None
        self.discharge_revenue_hourly = None
        self.charge_cost = 0.0
        self.discharge_revenue = 0.0
        self.net_revenue = 0.0

        self.Ein = 0.0
        self.Eout = 0.0
        self.Qout = 0.0
        self.surface_capital_cost = 0.0
        self.subsurface_capital_cost = 0.0
        self.total_capital_cost = 0.0
        self.total_capital_cost_ITC = 0.0
        self.OnM_surface = 0.0
        self.OnM_subsurface = 0.0
        self.OnM_total = 0.0
        self.ITC = float(get("ITC", 0.0))
        self.elec_cost = 0.0
        self.FCR = 0.0
        self.LCOS = 0.0
        self.LCOE = 0.0
        self.LCOH = 0.0
        self.LCOS_ITC = 0.0
        self.LCOE_ITC = 0.0
        self.LCOH_ITC = 0.0

    def calc_fcr(self):
        self.RROE = (1 + self.irr) / (1 + self.inflation) - 1.0
        self.RINT = (1 + self.debt_IR) / (1 + self.inflation) - 1.0

        self.WACC = ((1 + self.inflation) * (1 + self.RROE) - 1) * (1 - self.debt_frac) + 1
        self.WACC = self.WACC + self.debt_frac * (
            ((1 + self.RINT) * (1 + self.inflation) - 1) * (1 - self.tax_rate)
        )
        self.WACC = self.WACC / (1 + self.inflation) - 1.0

        self.CRF = self.WACC / (1.0 - (1.0 / ((1 + self.WACC) ** self.lifetime)))

        self.PVDEP = 0.0
        for i, depreciation in enumerate(self.deprec, start=1):
            self.PVDEP += depreciation / (((1 + self.WACC) * (1 + self.inflation)) ** i)

        self.PFF = (1 - self.tax_rate * self.PVDEP) / (1.0 - self.tax_rate)

        self.CFF = 0.0
        for i, annual_cost in enumerate(self.annual_cost, start=1):
            self.CFF += (
                (((1 + self.construc_IR) ** (i - 0.5) - 1) * (1 - self.tax_rate) + 1)
                * annual_cost
            )

        self.FCR = self.CRF * self.PFF * self.CFF
        return self

    def calc_levelized_cost(self, mode: str):
        self.total_capital_cost = self.surface_capital_cost + self.subsurface_capital_cost
        self.total_capital_cost_ITC = (1.0 - self.ITC) * self.total_capital_cost
        self.OnM_total = self.OnM_surface + self.OnM_subsurface
        self.elec_cost = self.charge_cost if self.charge_cost > 0.0 else self.elec_price * self.Ein * 1e6

        if mode == "E":
            self.LCOE = (
                self.total_capital_cost * self.FCR
                + self.OnM_total
                + self.elec_cost
            ) / (self.Eout * 1e6)
            self.LCOE_ITC = (
                self.total_capital_cost_ITC * self.FCR
                + self.OnM_total
                + self.elec_cost
            ) / (self.Eout * 1e6)
        elif mode == "S":
            self.LCOS = (
                self.total_capital_cost * self.FCR
                + self.OnM_total
                + self.elec_cost
            ) / (self.Eout * 1e6)
            self.LCOS_ITC = (
                self.total_capital_cost_ITC * self.FCR
                + self.OnM_total
                + self.elec_cost
            ) / (self.Eout * 1e6)
        elif mode == "H":
            self.LCOH = (
                self.total_capital_cost * self.FCR
                + self.OnM_total
                + self.elec_cost
            ) / (self.Qout * 1e6)
            self.LCOH_ITC = (
                self.total_capital_cost_ITC * self.FCR
                + self.OnM_total
                + self.elec_cost
            ) / (self.Qout * 1e6)
        else:
            raise ValueError(f"Unsupported mode: {mode}")

        return self

    def calc_revenue(self, Win, Wout):
        self.charge_cost_hourly = np.multiply(self.elec_price_hourly, Win)
        self.discharge_revenue_hourly = np.multiply(self.elec_price_hourly, Wout)

        self.charge_cost = float(np.sum(self.charge_cost_hourly))
        self.discharge_revenue = float(np.sum(self.discharge_revenue_hourly))
        self.net_revenue = self.discharge_revenue - self.charge_cost
        return self
    
    '''
    def plot_revenue(self):
        if self.charge_cost_hourly is None or self.discharge_revenue_hourly is None:
            raise RuntimeError("Revenue hourly arrays are not available yet.")

        hours = np.arange(len(self.charge_cost_hourly))
        plt.figure(figsize=(12, 5))
        plt.plot(hours, self.charge_cost_hourly, label="Charge cost hourly")
        plt.plot(hours, self.discharge_revenue_hourly, label="Discharge revenue hourly")
        plt.xlabel("Hour")
        plt.ylabel("Cost / revenue")
        plt.legend()
        plt.tight_layout()
        plt.show()
    '''