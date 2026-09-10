from pathlib import Path

import numpy as np

try:
    from CoolProp.CoolProp import PropsSI
except ImportError:
    PropsSI = None


class fluid_class:
    def __init__(self, fluid_name: str):
        self.fluid = fluid_name
        self.type = None
        self.handle = None
        self.fname = None
        self.tab = None

        self.p = 0.0
        self.T = 0.0
        self.h = 0.0
        self.s = 0.0
        self.q = 0.0
        self.cp = 0.0
        self.rho = 0.0
        self.mdot = 0.0
        self.vdot = 0.0

        if self.fluid == "nitrate salt":
            self.type = "tab"
            self.fname = Path("data/SolarSalt.dat")
        elif self.fluid == "chloride salt":
            self.type = "tab"
            self.fname = Path("data/ChlorideSalt.dat")
        elif self.fluid == "Therminol VP1":
            self.type = "tab"
            self.fname = Path("data/TherminolVP1.dat")
        else:
            self.type = "cp"

        if self.type == "cp":
            if PropsSI is None:
                raise ImportError("CoolProp is required for fluid_class with cp fluids")
            PropsSI("T", "P", 101325, "Q", 0, "Water")
        else:
            data_dir = Path(__file__).resolve().parent / "data"
            if not self.fname.is_absolute():
                candidate = data_dir / self.fname.name
                if candidate.exists():
                    self.fname = candidate
                elif self.fname.exists():
                    self.fname = self.fname
                else:
                    self.fname = candidate

            if not self.fname.exists():
                raise FileNotFoundError(f"Fluid data file not found: {self.fname}")

            self.tab = np.loadtxt(self.fname, comments='%', delimiter=None)

    def calc_fluid_props(self, mode: str):
        if self.type == "cp":
            if PropsSI is None:
                raise ImportError("CoolProp is required for calc_fluid_props")

            if mode in {"pT", "Tp"}:
                self.s = PropsSI("S", "P", self.p * 1e5, "T", self.T + 273.15, self.fluid) / 1e3
                self.h = PropsSI("H", "P", self.p * 1e5, "T", self.T + 273.15, self.fluid) / 1e3
                self.q = PropsSI("Q", "P", self.p * 1e5, "T", self.T + 273.15, self.fluid)
                self.rho = PropsSI("D", "P", self.p * 1e5, "T", self.T + 273.15, self.fluid)
                self.cp = PropsSI("CPMASS", "P", self.p * 1e5, "T", self.T + 273.15, self.fluid) / 1e3

            elif mode in {"pq", "qp"}:
                self.s = PropsSI("S", "P", self.p * 1e5, "Q", self.q, self.fluid) / 1e3
                self.h = PropsSI("H", "P", self.p * 1e5, "Q", self.q, self.fluid) / 1e3
                self.T = PropsSI("T", "P", self.p * 1e5, "Q", self.q, self.fluid) - 273.15
                self.rho = PropsSI("D", "P", self.p * 1e5, "Q", self.q, self.fluid)
                self.cp = PropsSI("CPMASS", "P", self.p * 1e5, "Q", self.q, self.fluid) / 1e3

            elif mode in {"ph", "hp"}:
                self.q = PropsSI("Q", "P", self.p * 1e5, "H", self.h * 1e3, self.fluid)
                self.s = PropsSI("S", "P", self.p * 1e5, "H", self.h * 1e3, self.fluid) / 1e3
                self.T = PropsSI("T", "P", self.p * 1e5, "H", self.h * 1e3, self.fluid) - 273.15
                self.rho = PropsSI("D", "P", self.p * 1e5, "H", self.h * 1e3, self.fluid)
                self.cp = PropsSI("CPMASS", "P", self.p * 1e5, "H", self.h * 1e3, self.fluid) / 1e3

            elif mode in {"Tq", "qT"}:
                self.s = PropsSI("S", "Q", self.q, "T", self.T + 273.15, self.fluid) / 1e3
                self.h = PropsSI("H", "Q", self.q, "T", self.T + 273.15, self.fluid) / 1e3
                self.p = PropsSI("P", "Q", self.q, "T", self.T + 273.15, self.fluid) / 1e5
                self.rho = PropsSI("D", "Q", self.q, "T", self.T + 273.15, self.fluid)
                self.cp = PropsSI("CPMASS", "Q", self.q, "T", self.T + 273.15, self.fluid) / 1e3

            else:
                raise ValueError(f"Mode '{mode}' not implemented for cp fluid")

        else:
            if self.tab is None:
                raise RuntimeError("Fluid tabular data is not loaded")

            if mode == "T":
                T_K = self.T + 273.15
                self.h = np.interp(T_K, self.tab[:, 0], self.tab[:, 1]) / 1e3
                self.s = np.interp(T_K, self.tab[:, 0], self.tab[:, 3]) / 1e3
                self.rho = np.interp(T_K, self.tab[:, 0], self.tab[:, 2])
                self.cp = np.interp(T_K, self.tab[:, 0], self.tab[:, 4]) / 1e3
            else:
                raise ValueError(f"Mode '{mode}' not implemented for tabular fluid")

        return self

    def calc_mdot_vdot(self, mode: str):
        if mode == "vdot":
            self.vdot = self.mdot / self.rho
        elif mode == "mdot":
            self.mdot = self.vdot * self.rho
        else:
            raise ValueError(f"Mode '{mode}' not implemented for flow conversion")

        return self
