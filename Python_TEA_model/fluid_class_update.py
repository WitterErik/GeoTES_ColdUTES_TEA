import numpy as np
from pathlib import Path
import user_inputs

try:
    import CoolProp.CoolProp as CP
except ImportError:
    print(" CoolProp library not found! Please install CoolProps")
    CP = None

class fluid_class:
    # simulates physical thermodynamic states for fluids and custom fluids

    def __init__(self,fluid_name):
        self.fluid = fluid_name
        self.type = 'cp'
        self.fname = None
        self.tab = None

        # map custom tabular salts and fluids
        fluid_lower = self.fluid.lower()
        if fluid_lower == 'nitrate salt':
            self.type = 'tab'
            self.fname = user_inputs.data_dir/"SolarSalt.dat"
        elif fluid_lower == 'chloride salt':
            self.type = 'tab'
            self.fname = user_inputs.data_dir/"ChlorideSalt.dat"
        elif fluid_lower == 'therminol vp1':
            self.type = 'tab'
            self.fname = user_inputs.data_dir/"TherminolVP1.dat"
        else:
            self.type = 'cp'

        # initialize coolprop
        if self.type == 'cp':
            if CP is None:
                raise ImportError("CoolProp is required for this fluid but is not installed")
            try:
                CP.PropsSI('T','P',101325,'Q',0,'Water')
            except Exception as e:
                print('CoolProp verification failed: {e}')
        elif self.type == 'tab':
            # resolve path name and location
            if self.fname.exists():
                self.tab = np.loadtxt(self.fname)
            else:
                raise FileNotFoundError(f" Customer fluid data file not found at {self.fname}")

        # pre-allocate property fields
        self.p = 0.0     # Pressure, bar
        self.T = 0.0     # Temperature, C
        self.h = 0.0     # Enthalpy, kJ/kg
        self.s = 0.0     # Entropy, kJ/kg.K
        self.q = 0.0     # Vapor quality
        self.cp = 0.0    # Heat capacity, kJ/kg.K
        self.rho = 0.0   # Density, kg/m3
        self.mdot = 0.0  # Mass flow rate, kg/s
        self.vdot = 0.0  # Volumetric flow rate, m3/s

        def calc_fluid_props(self,mode):
            """
        Solves for all remaining thermodynamic state variables based on input variables.
        Updates self properties in-place.
        """
        # Ensure values are numpy arrays to handle both single values and vectors cleanly
        p_arr = np.atleast_1d(self.p)
        T_arr = np.atleast_1d(self.T)
        q_arr = np.atleast_1d(self.q)
        h_arr = np.atleast_1d(self.h)

        n_elements = max(len(p_arr), len(T_arr), len(q_arr), len(h_arr))

        # Re-initialize property arrays to match the input vector sizes
        self.s = np.zeros(n_elements)
        self.h = np.zeros(n_elements)
        self.q = np.zeros(n_elements)
        self.rho = np.zeros(n_elements)
        self.cp = np.zeros(n_elements)
        self.T = np.zeros(n_elements)
        self.p = np.zeros(n_elements)

        if self.type == 'cp':
            for i in range(n_elements):
                # Fetch target slice elements safely
                p_val = p_arr[i] if i < len(p_arr) else p_arr[0]
                T_val = T_arr[i] if i < len(T_arr) else T_arr[0]
                q_val = q_arr[i] if i < len(q_arr) else q_arr[0]
                h_val = h_arr[i] if i < len(h_arr) else h_arr[0]

                if mode in ['pT', 'Tp']:
                    p_pa = p_val * 1e5
                    T_k = T_val + 273.15
                    self.s[i] = CP.PropsSI('S', 'P', p_pa, 'T', T_k, self.fluid) / 1e3
                    self.h[i] = CP.PropsSI('H', 'P', p_pa, 'T', T_k, self.fluid) / 1e3
                    self.q[i] = CP.PropsSI('Q', 'P', p_pa, 'T', T_k, self.fluid)
                    self.rho[i] = CP.PropsSI('D', 'P', p_pa, 'T', T_k, self.fluid)
                    self.cp[i] = CP.PropsSI('CPMASS', 'P', p_pa, 'T', T_k, self.fluid) / 1e3
                    self.p[i] = p_val
                    self.T[i] = T_val

                elif mode in ['pq', 'qp']:
                    p_pa = p_val * 1e5
                    self.s[i] = CP.PropsSI('S', 'P', p_pa, 'Q', q_val, self.fluid) / 1e3
                    self.h[i] = CP.PropsSI('H', 'P', p_pa, 'Q', q_val, self.fluid) / 1e3
                    self.T[i] = CP.PropsSI('T', 'P', p_pa, 'Q', q_val, self.fluid) - 273.15
                    self.rho[i] = CP.PropsSI('D', 'P', p_pa, 'Q', q_val, self.fluid)
                    self.cp[i] = CP.PropsSI('CPMASS', 'P', p_pa, 'Q', q_val, self.fluid) / 1e3
                    self.p[i] = p_val
                    self.q[i] = q_val

                elif mode in ['ph', 'hp']:
                    p_pa = p_val * 1e5
                    h_j = h_val * 1e3
                    self.q[i] = CP.PropsSI('Q', 'P', p_pa, 'H', h_j, self.fluid)
                    self.s[i] = CP.PropsSI('S', 'P', p_pa, 'H', h_j, self.fluid) / 1e3
                    self.T[i] = CP.PropsSI('T', 'P', p_pa, 'H', h_j, self.fluid) - 273.15
                    self.rho[i] = CP.PropsSI('D', 'P', p_pa, 'H', h_j, self.fluid)
                    self.cp[i] = CP.PropsSI('CPMASS', 'P', p_pa, 'H', h_j, self.fluid) / 1e3
                    self.p[i] = p_val
                    self.h[i] = h_val

                elif mode in ['Tq', 'qT']:
                    T_k = T_val + 273.15
                    self.s[i] = CP.PropsSI('S', 'Q', q_val, 'T', T_k, self.fluid) / 1e3
                    self.h[i] = CP.PropsSI('H', 'Q', q_val, 'T', T_k, self.fluid) / 1e3
                    self.p[i] = CP.PropsSI('P', 'Q', q_val, 'T', T_k, self.fluid) / 1e5
                    self.rho[i] = CP.PropsSI('D', 'Q', q_val, 'T', T_k, self.fluid)
                    self.cp[i] = CP.PropsSI('CPMASS', 'Q', q_val, 'T', T_k, self.fluid) / 1e3
                    self.T[i] = T_val
                    self.q[i] = q_val

        elif self.type == 'tab':
            # Custom salts interpolation sequence
            # tab columns: [0]: Temp (K), [1]: h (J/kg), [2]: rho (kg/m3), [3]: s (J/kgK), [4]: cp (J/kgK)
            for i in range(n_elements):
                T_val = T_arr[i] if i < len(T_arr) else T_arr[0]
                T_k = T_val + 273.15

                # np.interp requires independent variable (T_k) to be sorted
                self.h[i] = np.interp(T_k, self.tab[:, 0], self.tab[:, 1]) / 1e3
                self.s[i] = np.interp(T_k, self.tab[:, 0], self.tab[:, 3]) / 1e3
                self.rho[i] = np.interp(T_k, self.tab[:, 0], self.tab[:, 2])
                self.cp[i] = np.interp(T_k, self.tab[:, 0], self.tab[:, 4]) / 1e3
                self.T[i] = T_val

        # If it was a single scalar input, convert arrays back to clean scalar float numbers
        if n_elements == 1:
            self.p = float(self.p[0])
            self.T = float(self.T[0])
            self.h = float(self.h[0])
            self.s = float(self.s[0])
            self.q = float(self.q[0])
            self.cp = float(self.cp[0])
            self.rho = float(self.rho[0])

    def calc_mdot_vdot(self, mode):
        """Converts flow rates in-place."""
        if mode == 'vdot':
            self.vdot = self.mdot / self.rho
        elif mode == 'mdot':
            self.mdot = self.vdot * self.rho
        else:
            raise NotImplementedError(f"Flow rate conversion mode '{mode}' is not implemented.")