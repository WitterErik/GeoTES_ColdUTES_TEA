import math
from pathlib import Path

import numpy as np
from scipy.interpolate import RectBivariateSpline


class thermo_cycle_class:
    def __init__(self, PC_type, PC_design, PC_foff, PC_cost, nY=2):
        get = PC_design.get if isinstance(PC_design, dict) else lambda key: getattr(PC_design, key)

        self.type = PC_type
        self.nY = int(nY)

        self.Win0 = 0.0
        self.Wout0 = 0.0
        self.Qin0 = 0.0
        self.Qout0 = 0.0
        self.Qrej0 = float(get("Qrej", 0.0))
        self.eff0 = 0.0
        self.COP0 = 0.0
        self.Tamb0 = float(get("T0"))
        self.fan0 = float(get("fan", 0.0))

        self.Win = np.zeros(self.nY * 8760, dtype=float)
        self.Wout = np.zeros(self.nY * 8760, dtype=float)
        self.Qin = np.zeros(self.nY * 8760, dtype=float)
        self.Qout = np.zeros(self.nY * 8760, dtype=float)
        self.eff = np.zeros(self.nY * 8760, dtype=float)
        self.COP = np.zeros(self.nY * 8760, dtype=float)
        self.Tamb = np.zeros(self.nY * 8760, dtype=float)

        self.Tmax = 0.0
        self.Tmin = 0.0
        self.mdot = 0.0

        self.fname = PC_foff
        self.T0_off = None
        self.Qin_off = None
        self.Win_off = None
        self.Wout_off = None
        self.Qout_off = None
        self._off_interp = None

        self.Qin_tot = 0.0
        self.Wout_tot = 0.0
        self.Win_tot = 0.0
        self.Qout_tot = 0.0
        self.capacity_factor = 0.0

        self.power_block_cost_unit = float(PC_cost["power_block"])
        self.HX_cost_unit = float(PC_cost["HX"])
        self.fan_cost_unit = float(PC_cost.get("fan", 0.0))

        self.power_block_cost = 0.0
        self.HX_cost = 0.0
        self.fan_cost = 0.0
        self.total_cost = 0.0

        if self.type == "HE":
            self.Wout0 = float(get("Wout"))
            if float(get("TIT", 0.0)) > 0.0:
                self.Tmax = float(get("TIT"))
                self.eff0 = 1.0 - math.sqrt((self.Tamb0 + 273.15) / (self.Tmax + 273.15))
                self.Qin0 = self.Wout0 / self.eff0
            elif float(get("Qin", 0.0)) > 0.0:
                self.Qin0 = float(get("Qin"))
                self.eff0 = self.Wout0 / self.Qin0
            elif float(get("eff", 0.0)) > 0.0:
                self.eff0 = float(get("eff"))
                self.Qin0 = self.Wout0 / self.eff0
            self.Qout0 = self.Qin0 - self.Wout0
        elif self.type == "HP":
            self.Win0 = float(get("Win"))
            if float(get("COT", 0.0)) > 0.0:
                self.Tmax = float(get("COT"))
                self.COP0 = 1.0 / (1.0 - ((self.Tamb0 + 273.15) / (self.Tmax + 273.15)))
                self.Qout0 = self.Win0 * self.COP0
            elif float(get("Qout", 0.0)) > 0.0:
                self.Qout0 = float(get("Qout"))
                self.COP0 = self.Qout0 / self.Win0
            elif float(get("COP", 0.0)) > 0.0:
                self.COP0 = float(get("COP"))
                self.Qout0 = self.Win0 * self.COP0
            self.Qin0 = self.Qout0 - self.Win0
        else:
            raise ValueError(f"Unsupported cycle type: {self.type}")

        self._load_off_design_data()

    def _load_off_design_data(self):
        fname = Path(self.fname)
        if not fname.exists() and not fname.is_absolute():
            fname = Path(__file__).resolve().parent / self.fname

        if not fname.exists():
            raise FileNotFoundError(f"Off-design file not found: {self.fname}")

        if fname.suffix.lower() in {'.xlsx', '.xls'}:
            try:
                import pandas as pd
            except ImportError as exc:
                raise ImportError(
                    "pandas is required to load Excel off-design files. "
                    "Install it with 'pip install pandas' or provide a CSV file."
                ) from exc

            off_data = pd.read_excel(fname, header=None).to_numpy(dtype=float)
        else:
            try:
                off_data = np.genfromtxt(fname, delimiter=",")
            except ValueError:
                off_data = np.genfromtxt(fname, delimiter=None)

        if off_data.ndim != 2 or off_data.shape[0] < 2 or off_data.shape[1] < 2:
            raise ValueError(f"Off-design data must be a 2D matrix with at least 2 rows and 2 columns: {self.fname}")

        self.T0_off = off_data[0, 1:]
        self.Qin_off = off_data[1:, 0]

        if self.type == "HE":
            self.Wout_off = off_data[1:, 1:]
            self._off_interp = RectBivariateSpline(
                self.Qin_off,
                self.T0_off,
                self.Wout_off,
                kx=3,
                ky=3,
            )
        else:
            self.Win_off = off_data[1:, 0]
            self.Qout_off = off_data[1:, 1:]
            self._off_interp = RectBivariateSpline(
                self.Win_off,
                self.T0_off,
                self.Qout_off,
                kx=3,
                ky=3,
            )

    def PC_annual_energy(self):
        n = np.arange(8760, 2 * 8760)

        if self.type == "HE":
            self.Qin_tot = float(np.sum(self.Qin[n]) / 1000.0)
            self.Wout_tot = float(np.sum(self.Wout[n]) / 1000.0)
            self.capacity_factor = self.Wout_tot * 1000.0 / (self.Wout0 * 24.0 * 365.0)
        elif self.type == "HP":
            self.Win_tot = float(np.sum(self.Win[n]) / 1000.0)
            self.Qout_tot = float(np.sum(self.Qout[n]) / 1000.0)
            self.capacity_factor = self.Qout_tot * 1000.0 / (self.Qout0 * 24.0 * 365.0)
        else:
            raise ValueError(f"Unsupported cycle type: {self.type}")

        return self

    def interpolate_off_design(self, i: int):
        x_req = float(self.Tamb[i] / self.Tamb0)

        if self.type == "HE":
            y_req = float(self.Qin[i] / self.Qin0)
            if y_req <= 0.0:
                self.Wout[i] = 0.0
            else:
                y_req = np.clip(y_req, self.Qin_off[0], self.Qin_off[-1])
                x_req = np.clip(x_req, self.T0_off[0], self.T0_off[-1])
                self.Wout[i] = float(self.Wout_off_interp(y_req, x_req)) * self.Wout0
        elif self.type == "HP":
            y_req = float(self.Win[i] / self.Win0)
            if y_req <= 0.0:
                self.Qout[i] = 0.0
            else:
                y_req = np.clip(y_req, self.Win_off[0], self.Win_off[-1])
                x_req = np.clip(x_req, self.T0_off[0], self.T0_off[-1])
                self.Qout[i] = float(self._off_interp(y_req, x_req)[0, 0]) * self.Qout0
        else:
            raise ValueError(f"Unsupported cycle type: {self.type}")

        return self

    def calc_PC_cost(self):
        if self.type == "HE":
            self.power_block_cost = self.power_block_cost_unit * self.Wout0 * 1000.0
            hx_quantity = self.Qrej0 if self.Qrej0 > 0.0 else self.Qout0
            self.HX_cost = self.HX_cost_unit * hx_quantity * 1000.0
            self.fan_cost = self.fan_cost_unit * self.fan0 * self.Wout0 * 1000.0
        elif self.type == "HP":
            self.power_block_cost = self.power_block_cost_unit * self.Win0 * 1000.0
            hx_quantity = self.Qrej0 if self.Qrej0 > 0.0 else self.Qout0
            self.HX_cost = self.HX_cost_unit * hx_quantity * 1000.0
            self.fan_cost = self.fan_cost_unit * self.fan0 * self.Win0 * 1000.0
        else:
            raise ValueError(f"Unsupported cycle type: {self.type}")

        self.total_cost = self.power_block_cost + self.HX_cost + self.fan_cost
        return self

    def Wout_off_interp(self, y, x):
        return self._off_interp(y, x)[0, 0]
