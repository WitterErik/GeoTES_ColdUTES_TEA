"""Fluid-property helpers for the split GeoTES model."""

from __future__ import annotations

import numpy as np

import user_inputs

try:
    import CoolProp.CoolProp as CP
except ImportError:
    CP = None


class fluid_class:
    """Thermodynamic fluid state backed by CoolProp or a tabular fluid file."""

    def __init__(self, fluid_name: str):
        self.fluid = fluid_name
        self.type = "cp"
        self.fname = None
        self.tab = None

        custom_files = {
            "nitrate salt": "SolarSalt.dat",
            "chloride salt": "ChlorideSalt.dat",
            "therminol vp1": "TherminolVP1.dat",
        }
        custom_name = custom_files.get(fluid_name.lower())
        if custom_name:
            self.type = "tab"
            self.fname = user_inputs.data_dir / custom_name
            if not self.fname.exists():
                raise FileNotFoundError(f"Fluid data file not found: {self.fname}")
            self.tab = np.loadtxt(self.fname)
        elif CP is None:
            raise ImportError("CoolProp is required for this fluid; install CoolProp first.")

        self.p = 0.0
        self.T = 0.0
        self.h = 0.0
        self.s = 0.0
        self.q = 0.0
        self.cp = 0.0
        self.rho = 0.0
        self.mdot = 0.0
        self.vdot = 0.0

    def calc_fluid_props(self, mode: str):
        """Calculate the remaining state properties in place and return this state."""
        if self.type == "tab":
            temperature = np.atleast_1d(np.asarray(self.T, dtype=float))
            temp_k = temperature + 273.15
            self.h = np.interp(temp_k, self.tab[:, 0], self.tab[:, 1]) / 1000.0
            self.rho = np.interp(temp_k, self.tab[:, 0], self.tab[:, 2])
            self.s = np.interp(temp_k, self.tab[:, 0], self.tab[:, 3]) / 1000.0
            self.cp = np.interp(temp_k, self.tab[:, 0], self.tab[:, 4]) / 1000.0
            self.T = temperature
            self._scalarize_properties()
            return self

        if CP is None:
            raise ImportError("CoolProp is required to calculate fluid properties.")

        property_pair = mode.lower()
        if property_pair not in {"pt", "tp", "pq", "qp", "ph", "hp", "qt", "tq"}:
            raise ValueError(f"Unsupported fluid property input pair: {mode}")

        p, temperature, quality, enthalpy = self._broadcast_inputs()
        results = {name: np.zeros(len(p), dtype=float) for name in ("p", "T", "h", "s", "q", "cp", "rho")}

        for i in range(len(p)):
            if property_pair in {"pt", "tp"}:
                inputs = ("P", p[i] * 1e5, "T", temperature[i] + 273.15)
            elif property_pair in {"pq", "qp"}:
                inputs = ("P", p[i] * 1e5, "Q", quality[i])
            elif property_pair in {"ph", "hp"}:
                inputs = ("P", p[i] * 1e5, "H", enthalpy[i] * 1000.0)
            else:
                inputs = ("T", temperature[i] + 273.15, "Q", quality[i])

            results["T"][i] = CP.PropsSI("T", *inputs, self.fluid) - 273.15
            results["p"][i] = CP.PropsSI("P", *inputs, self.fluid) / 1e5
            results["h"][i] = CP.PropsSI("H", *inputs, self.fluid) / 1000.0
            results["s"][i] = CP.PropsSI("S", *inputs, self.fluid) / 1000.0
            results["q"][i] = CP.PropsSI("Q", *inputs, self.fluid)
            results["rho"][i] = CP.PropsSI("D", *inputs, self.fluid)
            results["cp"][i] = CP.PropsSI("CPMASS", *inputs, self.fluid) / 1000.0

        for name, values in results.items():
            setattr(self, name, float(values[0]) if len(values) == 1 else values)
        return self

    def _broadcast_inputs(self):
        arrays = [
            np.atleast_1d(np.asarray(value, dtype=float))
            for value in (self.p, self.T, self.q, self.h)
        ]
        size = max(map(len, arrays))
        return [np.full(size, array[0]) if len(array) == 1 else array for array in arrays]

    def _scalarize_properties(self):
        for name in ("T", "p", "h", "s", "q", "cp", "rho"):
            value = getattr(self, name)
            if isinstance(value, np.ndarray) and value.size == 1:
                setattr(self, name, float(value[0]))

    def calc_mdot_vdot(self, mode: str):
        """Convert between mass and volumetric flow rates in place."""
        if mode == "vdot":
            if np.any(np.asarray(self.rho) == 0):
                raise ZeroDivisionError("Fluid density must be nonzero to calculate volumetric flow.")
            self.vdot = np.asarray(self.mdot) / np.asarray(self.rho)
        elif mode == "mdot":
            self.mdot = np.asarray(self.vdot) * np.asarray(self.rho)
        else:
            raise ValueError(f"Unsupported flow conversion mode: {mode}")
        if np.size(self.vdot) == 1:
            self.vdot = float(np.asarray(self.vdot).item())
        if np.size(self.mdot) == 1:
            self.mdot = float(np.asarray(self.mdot).item())
        return self


def calc_fluid_props(fluid, mode: str):
    """Compatibility helper that calculates properties and returns the fluid state."""
    return fluid.calc_fluid_props(mode)


def calc_mdot_vdot(fluid, mode: str):
    """Compatibility helper that converts a fluid state's flow rate."""
    return fluid.calc_mdot_vdot(mode)