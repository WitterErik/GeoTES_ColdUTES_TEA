import numpy as np
import pandas as pd
from scipy.interpolate import RectBivariateSpline

class thermo_cycle_class:
    # simulates thermodnamic power cycle (HE = Heat Engine or HP = Heat pump)
    # off-design hourly performance and cost evalulations

    def __init__(self,PC_type, PC_design, PC_foff, PC_cost, nY):
        self.type = PC_type
        self.nY = nY 
        self.fname = PC_foff 

        # default property initialization
        self.Wout0 = 0.0
        self.Win0 = 0.0
        self.Qin0 = 0.0
        self.Qout0 = 0.0
        self.Qrej0 = 0.0
        self.eff0 = 0.0
        self.COP0 = 0.0
        self.Tamb0 = 25.0
        self.fan0 = 0.0
        self.Tmax = 0.0

        # parse costs 
        self.power_block_cost_unit = PC_cost.get("power_block", 0.0)
        self.HX_cost_unit = PC_cost.get("HX", 0.0)
        self.fan_cost_unit = PC_cost.get("fan", 0.0)

        # design parameter formulations
        T0 = PC_design.get("T0", 25.0)
        Qrej = PC_design.get("Qrej", 0.0)
        fan_val = PC_design.get("fan", 0.0)

        if self.type == 'HE':
            self.Wout0 = PC_design.get("Wout", 0.0)
            self.Tamb0 = T0
            self.Qrej0 = Qrej
            self.fan0 = fan_val

            tit = PC_design.get("TIT", 0.0)
            qin = PC_design.get("Qin", 0.0)
            eff = PC_design.get("eff", 0.0)

            if tit > 0:
                self.Tmax = tit
                # Curzon-Ahlborn efficiency equation matching your code
                self.eff0 = (1.0 - np.sqrt((self.Tamb0 + 273.15) / (self.Tmax + 273.15))) * 0.98 * 0.9
                self.Qin0 = self.Wout0 / self.eff0
            elif qin > 0:
                self.Qin0 = qin
                self.eff0 = self.Wout0 / self.Qin0
            elif eff > 0:
                self.eff0 = eff
                self.Qin0 = self.Wout0 / self.eff0

            self.Qout0 = self.Qin0 - self.Wout0

        elif self.type == 'HP':
            self.Win0 = PC_design.get("Win", 0.0)
            self.Tamb0 = T0
            self.Qrej0 = Qrej
            self.fan0 = fan_val

            cot = PC_design.get("COT", 0.0)
            qout = PC_design.get("Qout", 0.0)
            cop = PC_design.get("COP", 0.0)

            if cot > 0:
                self.Tmax = cot
                # Carnot heat pump COP
                self.COP0 = 1.0 / (1.0 - ((self.Tamb0 + 273.15) / (self.Tmax + 273.15)))
                self.Qout0 = self.Win0 * self.COP0
            elif qout > 0:
                self.Qout0 = qout
                self.COP0 = self.Qout0 / self.Win0
            elif cop > 0:
                self.COP0 = cop
                self.Qout0 = self.Win0 * self.COP0

            self.Qin0 = self.Qout0 - self.Win0


        # pre-allocate arrays
        total_hours = nY * 8760
        self.Win = np.zeros(total_hours)
        self.Wout = np.zeros(total_hours)
        self.Qin = np.zeros(total_hours)
        self.Qout = np.zeros(total_hours)
        self.eff = np.zeros(total_hours)
        self.COP = np.zeros(total_hours)
        self.Tamb = np.zeros(total_hours)

        # 3. Read and Build Off-design Mesh Grid Interpolation Matrices
        try:
            # Replaces MATLAB's readmatrix
            if self.fname.endswith('.xlsx') or self.fname.endswith('.xls'):
                off_data = pd.read_excel(self.fname, header=None).values
            else:
                off_data = np.loadtxt(self.fname)
        except Exception as e:
            raise FileNotFoundError(f"❌ Failed to load off-design datasheet: {self.fname}. Error: {e}")

        nrow, ncol = off_data.shape

        # Extract independent axes coordinates
        # Row 0 contains Ambient Temp ratios (excluding the top-left index [0,0])
        self.T0_axes = off_data[0, 1:ncol]
        # Column 0 contains Power / Heat input ratios (excluding the top-left index [0,0])
        self.y_axes = off_data[1:nrow, 0]

        # Extract dependent payload matrix (Z-axis variables to interpolate)
        self.Z_payload = off_data[1:nrow, 1:ncol]

        # Create Meshgrids matching MATLAB arrangements
        self.T0_off, self.Qin_off = np.meshgrid(self.T0_axes, self.y_axes)
        
        if self.type == 'HE':
            self.Wout_off = self.Z_payload
            # Setup Spline solver: RectBivariateSpline is highly robust on uniform grid coordinate axes
            self.spline_solver = RectBivariateSpline(self.y_axes, self.T0_axes, self.Wout_off)
        elif self.type == 'HP':
            self.Qout_off = self.Z_payload
            self.spline_solver = RectBivariateSpline(self.y_axes, self.T0_axes, self.Qout_off)

        # 4. Total and Cost initialization placeholders
        self.Qin_tot = 0.0
        self.Wout_tot = 0.0
        self.Win_tot = 0.0
        self.Qout_tot = 0.0
        self.capacity_factor = 0.0

        self.power_block_cost = 0.0
        self.HX_cost = 0.0
        self.fan_cost = 0.0
        self.total_cost = 0.0

    def PC_annual_energy(self):
        """Calculates total annual energy tracking variables and active capacity factors."""
        start_hour = (self.nY - 1) * 8760
        end_hour = self.nY * 8760

        if self.type == 'HE':
            self.Qin_tot = np.sum(self.Qin[start_hour:end_hour]) / 1000.0
            self.Wout_tot = np.sum(self.Wout[start_hour:end_hour]) / 1000.0
            self.capacity_factor = self.Wout_tot * 1000.0 / (self.Wout0 * 24.0 * 365.0)
        elif self.type == 'HP':
            self.Win_tot = np.sum(self.Win[start_hour:end_hour]) / 1000.0
            self.Qout_tot = np.sum(self.Qout[start_hour:end_hour]) / 1000.0
            self.capacity_factor = self.Qout_tot * 1000.0 / (self.Qout0 * 24.0 * 365.0)

    def interpolate_off_design(self, i):
        """
        Interpolates off-design performance values at timestep 'i' 
        using 2D Bivariate Splines.
        """
        x_req = self.Tamb[i] / self.Tamb0

        if self.type == 'HE':
            y_req = self.Qin[i] / self.Qin0
            if y_req <= 0:
                self.Wout[i] = 0.0
            else:
                # RectBivariateSpline takes inputs as: solver(y, x)
                # We extract the scalar element using [0][0]
                interpolated_fraction = self.spline_solver(y_req, x_req)[0][0]
                self.Wout[i] = self.Wout0 * interpolated_fraction

        elif self.type == 'HP':
            y_req = self.Win[i] / self.Win0
            if y_req <= 0:
                self.Qout[i] = 0.0
            else:
                interpolated_fraction = self.spline_solver(y_req, x_req)[0][0]
                self.Qout[i] = self.Qout0 * interpolated_fraction

    def calc_PC_cost(self):
        """Calculates component-level Capital expenditures ($) of the Power Cycle."""
        if self.type == 'HE':
            self.power_block_cost = self.power_block_cost_unit * self.Wout0 * 1000.0
            self.HX_cost = self.HX_cost_unit * self.Qrej0 * 1000.0
            self.fan_cost = self.fan_cost_unit * self.fan0 * self.Wout0 * 1000.0
        elif self.type == 'HP':
            self.power_block_cost = self.power_block_cost_unit * self.Win0 * 1000.0
            self.HX_cost = self.HX_cost_unit * self.Qrej0 * 1000.0
            self.fan_cost = self.fan_cost_unit * self.fan0 * self.Win0 * 1000.0

        self.total_cost = self.power_block_cost + self.HX_cost + self.fan_cost
