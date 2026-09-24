from pathlib import Path
from types import SimpleNamespace

import numpy as np

from .ssccall import ssccall

sam_root = Path(__file__).resolve().parent
project_root = sam_root.parent


def _to_bool(value):
    return bool(value)


def call_SAM(CSP, PC):
    if CSP.location == 'Imperial CA':
        location_path = str(
            project_root / 'data' / 'imperial_ca_32.835205_-115.572398_psmv3_60_tmy.csv'
        )
    elif CSP.location == 'Antelope Hills CA':
        location_path = str(project_root / 'data' / 'north_antelope_hills_tmy.csv')
    else:
        raise ValueError(f'Unsupported CSP location: {CSP.location}')

    if CSP.solar_multiple > 2:
        SM = 2.0
        fac = CSP.solar_multiple / 2.0
    else:
        SM = float(CSP.solar_multiple)
        fac = 1.0

    ssccall('load')
    ssccall('module_exec_set_print', 0)
    data = ssccall('data_create')

    ssccall('data_set_string', data, 'file_name', location_path)
    ssccall('data_set_number', data, 'I_bn_des', CSP.nominal_DNI)
    ssccall('data_set_number', data, 'T_loop_in_des', CSP.Tmin)
    ssccall('data_set_number', data, 'T_loop_out', CSP.Tmax)
    ssccall('data_set_number', data, 'q_pb_design', PC.Qin0)
    ssccall('data_set_number', data, 'tshours', 6)
    ssccall('data_set_number', data, 'specified_solar_multiple', SM)
    ssccall('data_set_number', data, 'non_solar_field_land_area_multiplier', CSP.land_mult)

    # T_startup/T_shutdown are never left at the 'Commercial' preset default
    # (325.34 C): if that default exceeds T_loop_out_des, the field can never
    # satisfy its own startup/shutdown criterion and the defocus solver fails
    # with "COMPONENT defocus failed" regardless of field size or solar multiple.
    T_startup = CSP.Tmin + 0.7 * (CSP.Tmax - CSP.Tmin)
    ssccall('data_set_number', data, 'T_startup', T_startup)
    ssccall('data_set_number', data, 'T_shutdown', T_startup)

    nSCA = 4
    aperture_SCA = 656.0
    length_SCA = 115.0

    SCA_track = 0.988
    SCA_general_optical = 1.0
    SCA_geometry = 0.952
    SCA_reflectance = 0.93
    SCA_dirt = 0.97
    SCA_optical_eff = (
        SCA_track
        * SCA_general_optical
        * SCA_geometry
        * SCA_reflectance
        * SCA_dirt
    )

    HCE_absorbtance = 0.963
    HCE_trans = 0.964
    HCE_bellows = 0.935
    HCE_dirt = 0.98
    HCE_heat_loss = 190.0
    HCE_optical_eff = (
        HCE_absorbtance * HCE_trans * HCE_bellows * HCE_dirt
    )

    loop_optical_eff = SCA_optical_eff * HCE_optical_eff

    Q_per_loop = CSP.nominal_DNI * aperture_SCA * nSCA * loop_optical_eff
    Qloss_per_loop = HCE_heat_loss * length_SCA * nSCA
    nloops = int(np.ceil(PC.Qin0 * SM * 1e6 / (Q_per_loop - Qloss_per_loop)))

    # 'track_mode' and 'nSCA' have no matching PySAM TroughPhysicalIph input attribute
    # (nSCA is derived from 'trough_loop_control' and is output-only) -- these two
    # data_set_number calls are silently dropped by _set_pysam_inputs.
    ssccall('data_set_number', data, 'track_mode', 1)
    ssccall('data_set_number', data, 'tilt', 0)
    ssccall('data_set_number', data, 'azimuth', 0)
    ssccall('data_set_number', data, 'nSCA', nSCA)
    ssccall('data_set_number', data, 'nHCEt', nSCA)
    ssccall('data_set_number', data, 'nColt', nSCA)
    ssccall('data_set_number', data, 'nHCEVar', nSCA)
    # 'nLoops' is output-only in PySAM TroughPhysicalIph; field sizing is actually
    # controlled by 'specified_solar_multiple' + 'use_solar_mult_or_aperture_area'
    # (default use_solar_mult_or_aperture_area=0 -> solar-multiple-based sizing).
    ssccall('data_set_number', data, 'nLoops', nloops)
    ssccall('data_set_number', data, 'eta_pump', 0.85)
    ssccall('data_set_number', data, 'HDR_rough', 4.57e-05)
    ssccall('data_set_number', data, 'theta_stow', 170)
    ssccall('data_set_number', data, 'theta_dep', 10)
    ssccall('data_set_number', data, 'Row_Distance', 15)
    ssccall('data_set_number', data, 'FieldConfig', 1)
    ssccall('data_set_number', data, 'is_model_heat_sink_piping', 0)
    ssccall('data_set_number', data, 'L_heat_sink_piping', 50)
    ssccall('data_set_number', data, 'm_dot_htfmin', 1)
    ssccall('data_set_number', data, 'm_dot_htfmax', 12)
    ssccall('data_set_number', data, 'Fluid', 18)
    ssccall('data_set_number', data, 'wind_stow_speed', 25)

    field_fl_props = np.array(
        [
            [20, 4.18, 999, 0.001, 9.9999999999999995e-07, 0.587, 85.3],
            [40, 4.18, 993, 0.000653, 6.58e-07, 0.618, 169.0],
            [60, 4.18, 984, 0.000467, 4.75e-07, 0.642, 252.0],
            [80, 4.19, 972, 0.000355, 3.65e-07, 0.657, 336.0],
            [100, 4.21, 959, 0.000282, 2.94e-07, 0.666, 420.0],
            [120, 4.25, 944, 0.000233, 2.46e-07, 0.67, 505.0],
            [140, 4.28, 927, 0.000197, 2.12e-07, 0.67, 590.0],
            [160, 4.34, 908, 0.000171, 1.88e-07, 0.667, 676.0],
            [180, 4.40, 887, 0.00015, 1.69e-07, 0.661, 764.0],
            [200, 4.49, 865, 0.000134, 1.55e-07, 0.651, 852.0],
            [220, 4.58, 842, 0.000118, 1.41e-07, 0.641, 941.0],
            [240, 4.67, 819, 0.000104, 1.29e-07, 0.631, 1030.0],    
            [260, 4.76, 796, 0.000092, 1.18e-07, 0.621, 1119.0],
        ], #last two rows are extrapolated from the rest of the data to allow for higher temperatures
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'field_fl_props', field_fl_props)

    ssccall('data_set_number', data, 'T_fp', 10)
    ssccall('data_set_number', data, 'Pipe_hl_coef', 0.45)
    ssccall('data_set_number', data, 'SCA_drives_elec', 125)
    ssccall('data_set_number', data, 'water_usage_per_wash', 0.7)
    ssccall('data_set_number', data, 'washing_frequency', 12)
    ssccall('data_set_number', data, 'accept_mode', 0)
    ssccall('data_set_number', data, 'accept_init', 0)
    ssccall('data_set_number', data, 'accept_loc', 1)
    ssccall('data_set_number', data, 'mc_bal_hot', 0.2)
    ssccall('data_set_number', data, 'mc_bal_cold', 0.2)
    ssccall('data_set_number', data, 'mc_bal_sca', 4.5)

    W_aperture = np.full(4, 6.0, dtype=np.float64)
    ssccall('data_set_array', data, 'W_aperture', W_aperture)

    A_aperture = np.full(4, aperture_SCA, dtype=np.float64)
    ssccall('data_set_array', data, 'A_aperture', A_aperture)

    TrackingError = np.full(4, SCA_track, dtype=np.float64)
    ssccall('data_set_array', data, 'TrackingError', TrackingError)

    GeomEffects = np.full(4, SCA_geometry, dtype=np.float64)
    ssccall('data_set_array', data, 'GeomEffects', GeomEffects)

    Rho_mirror_clean = np.full(4, SCA_reflectance, dtype=np.float64)
    ssccall('data_set_array', data, 'Rho_mirror_clean', Rho_mirror_clean)

    Dirt_mirror = np.full(4, SCA_dirt, dtype=np.float64)
    ssccall('data_set_array', data, 'Dirt_mirror', Dirt_mirror)

    Error = np.full(4, SCA_general_optical, dtype=np.float64)
    ssccall('data_set_array', data, 'Error', Error)

    Ave_Focal_Length = np.full(4, 2.15, dtype=np.float64)
    ssccall('data_set_array', data, 'Ave_Focal_Length', Ave_Focal_Length)

    L_SCA = np.full(4, length_SCA, dtype=np.float64)
    ssccall('data_set_array', data, 'L_SCA', L_SCA)

    nmod = 8
    L_aperture = np.full(4, length_SCA / nmod, dtype=np.float64)
    ssccall('data_set_array', data, 'L_aperture', L_aperture)

    ColperSCA = np.full(4, nmod, dtype=np.float64)
    ssccall('data_set_array', data, 'ColperSCA', ColperSCA)

    Distance_SCA = np.ones(4, dtype=np.float64)
    ssccall('data_set_array', data, 'Distance_SCA', Distance_SCA)

    IAM_matrix = np.array(
        [[1.0, 0.0327, -0.1351]] * 4,
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'IAM_matrix', IAM_matrix)

    HCE_FieldFrac = np.array(
        [[1.0, 0.0, 0.0, 0.0]] * 4,
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'HCE_FieldFrac', HCE_FieldFrac)

    D_2 = np.full((4, 4), 0.076, dtype=np.float64)
    ssccall('data_set_matrix', data, 'D_2', D_2)

    D_3 = np.full((4, 4), 0.08, dtype=np.float64)
    ssccall('data_set_matrix', data, 'D_3', D_3)

    D_4 = np.full((4, 4), 0.115, dtype=np.float64)
    ssccall('data_set_matrix', data, 'D_4', D_4)

    D_5 = np.full((4, 4), 0.12, dtype=np.float64)
    ssccall('data_set_matrix', data, 'D_5', D_5)

    D_p = np.zeros((4, 4), dtype=np.float64)
    ssccall('data_set_matrix', data, 'D_p', D_p)

    Flow_type = np.ones((4, 4), dtype=np.float64)
    ssccall('data_set_matrix', data, 'Flow_type', Flow_type)

    Rough = np.full((4, 4), 4.5e-05, dtype=np.float64)
    ssccall('data_set_matrix', data, 'Rough', Rough)

    alpha_env = np.array(
        [[0.02, 0.02, 0.0, 0.0]] * 4,
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'alpha_env', alpha_env)

    epsilon_3_11 = np.array(
        [
            [100.0, 0.064],
            [150.0, 0.0665],
            [200.0, 0.07],
            [250.0, 0.0745],
            [300.0, 0.08],
            [350.0, 0.0865],
            [400.0, 0.094],
            [450.0, 0.1025],
            [500.0, 0.112],
        ],
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'epsilon_3_11', epsilon_3_11)
    ssccall('data_set_matrix', data, 'epsilon_3_12', np.array([[0.65]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'epsilon_3_13', np.array([[0.65]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'epsilon_3_14', np.array([[0.0]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'epsilon_3_21', epsilon_3_11)
    ssccall('data_set_matrix', data, 'epsilon_3_22', np.array([[0.65]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'epsilon_3_23', np.array([[0.65]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'epsilon_3_24', np.array([[0.0]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'epsilon_3_31', epsilon_3_11)
    ssccall('data_set_matrix', data, 'epsilon_3_32', np.array([[0.65]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'epsilon_3_33', np.array([[0.65]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'epsilon_3_34', np.array([[0.0]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'epsilon_3_41', epsilon_3_11)
    ssccall('data_set_matrix', data, 'epsilon_3_42', np.array([[0.65]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'epsilon_3_43', np.array([[0.65]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'epsilon_3_44', np.array([[0.0]], dtype=np.float64))

    alpha_abs = np.array(
        [[HCE_absorbtance, HCE_absorbtance, 0.8, 0.0]] * 4,
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'alpha_abs', alpha_abs)

    Tau_envelope = np.array(
        [[HCE_trans, HCE_trans, 1.0, 0.0]] * 4,
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'Tau_envelope', Tau_envelope)

    EPSILON_4 = np.array(
        [[0.86, 0.86, 1.0, 0.0]] * 4,
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'EPSILON_4', EPSILON_4)

    EPSILON_5 = EPSILON_4.copy()
    ssccall('data_set_matrix', data, 'EPSILON_5', EPSILON_5)

    GlazingIntactIn = np.array(
        [[1.0, 1.0, 0.0, 1.0]] * 4,
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'GlazingIntactIn', GlazingIntactIn)

    P_a = np.array(
        [[0.0001, 750.0, 750.0, 0.0]] * 4,
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'P_a', P_a)

    AnnulusGas = np.array(
        [[27.0, 1.0, 1.0, 1.0]] * 4,
        dtype=np.float64,
    )
    AnnulusGas[2:, 3] = 27.0
    ssccall('data_set_matrix', data, 'AnnulusGas', AnnulusGas)

    AbsorberMaterial = np.ones((4, 4), dtype=np.float64)
    ssccall('data_set_matrix', data, 'AbsorberMaterial', AbsorberMaterial)

    Shadowing = np.array(
        [[HCE_bellows, HCE_bellows, HCE_bellows, 0.963]] * 4,
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'Shadowing', Shadowing)

    Dirt_HCE = np.array(
        [[HCE_dirt, HCE_dirt, 1.0, HCE_dirt]] * 4,
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'Dirt_HCE', Dirt_HCE)

    Design_loss = np.array(
        [[HCE_heat_loss, 1270.0, 1500.0, 0.0]] * 4,
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'Design_loss', Design_loss)

    ssccall('data_set_number', data, 'pb_pump_coef', 0.55)
    ssccall('data_set_number', data, 'init_hot_htf_percent', 30)
    ssccall('data_set_number', data, 'h_tank', 15)
    ssccall('data_set_number', data, 'cold_tank_max_heat', 0.5)
    ssccall('data_set_number', data, 'u_tank', 0.3)
    ssccall('data_set_number', data, 'tank_pairs', 1)
    ssccall('data_set_number', data, 'cold_tank_Thtr', 60)
    ssccall('data_set_number', data, 'h_tank_min', 0.5)
    ssccall('data_set_number', data, 'hot_tank_Thtr', 110)
    ssccall('data_set_number', data, 'hot_tank_max_heat', 1)

    weekday_schedule = np.array(
        [
            [6, 6, 6, 6, 6, 6, 5, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5],
            [6, 6, 6, 6, 6, 6, 5, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5],
            [6, 6, 6, 6, 6, 6, 5, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5],
            [6, 6, 6, 6, 6, 6, 5, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5],
            [6, 6, 6, 6, 6, 6, 5, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5],
            [3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 2, 2, 2, 3, 3, 3],
            [3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 2, 2, 2, 3, 3, 3],
            [3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 2, 2, 2, 3, 3, 3],
            [3, 3, 3, 3, 3, 3, 3, 3, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 2, 2, 2, 3, 3, 3],
            [6, 6, 6, 6, 6, 6, 5, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5],
            [6, 6, 6, 6, 6, 6, 5, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5],
            [6, 6, 6, 6, 6, 6, 5, 5, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 5, 5, 5],
        ],
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'weekday_schedule', weekday_schedule)

    weekend_schedule = np.array(
        [
            [6, 6, 6, 6, 6, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
            [6, 6, 6, 6, 6, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
            [6, 6, 6, 6, 6, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
            [6, 6, 6, 6, 6, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
            [6, 6, 6, 6, 6, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
            [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
            [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
            [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
            [3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3],
            [6, 6, 6, 6, 6, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
            [6, 6, 6, 6, 6, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
            [6, 6, 6, 6, 6, 6, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5],
        ],
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'weekend_schedule', weekend_schedule)

    ssccall('data_set_number', data, 'is_tod_pc_target_also_pc_max', 0)
    ssccall('data_set_number', data, 'is_dispatch', 0)
    ssccall('data_set_number', data, 'disp_frequency', 24)
    ssccall('data_set_number', data, 'disp_horizon', 48)
    ssccall('data_set_number', data, 'disp_max_iter', 35000)
    ssccall('data_set_number', data, 'disp_timeout', 5)
    ssccall('data_set_number', data, 'disp_mip_gap', 0.001)
    ssccall('data_set_number', data, 'disp_time_weighting', 0.99)
    ssccall('data_set_number', data, 'disp_rsu_cost_rel', 952)
    ssccall('data_set_number', data, 'disp_csu_cost_rel', 87)
    ssccall('data_set_number', data, 'disp_pen_ramping', 1)
    ssccall('data_set_number', data, 'is_wlim_series', 0)

    wlim_path = Path(__file__).resolve().parent / 'wlim_series.csv'
    wlim_series = np.loadtxt(str(wlim_path), delimiter=',')
    ssccall('data_set_array', data, 'wlim_series', wlim_series)

    f_turb_tou_periods = np.array([1.05, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float64)
    ssccall('data_set_array', data, 'f_turb_tou_periods', f_turb_tou_periods)

    ssccall('data_set_number', data, 'is_dispatch_series', 0)
    ssccall('data_set_array', data, 'dispatch_series', np.array([0.0], dtype=np.float64))
    ssccall('data_set_number', data, 'pb_fixed_par', 0.0055)
    ssccall('data_set_array', data, 'bop_array', np.array([0.0, 1.0, 0.0, 0.483, 0.0], dtype=np.float64))
    ssccall('data_set_array', data, 'aux_array', np.array([0.023, 1.0, 0.483, 0.571, 0.0], dtype=np.float64))
    ssccall('data_set_number', data, 'calc_design_pipe_vals', 1)
    ssccall('data_set_number', data, 'V_hdr_cold_max', 3)
    ssccall('data_set_number', data, 'V_hdr_cold_min', 2)
    ssccall('data_set_number', data, 'V_hdr_hot_max', 3)
    ssccall('data_set_number', data, 'V_hdr_hot_min', 2)
    ssccall('data_set_number', data, 'N_max_hdr_diams', 10)
    ssccall('data_set_number', data, 'L_rnr_pb', 25)
    ssccall('data_set_number', data, 'L_rnr_per_xpan', 70)
    ssccall('data_set_number', data, 'L_xpan_hdr', 20)
    ssccall('data_set_number', data, 'L_xpan_rnr', 20)
    ssccall('data_set_number', data, 'Min_rnr_xpans', 1)
    ssccall('data_set_number', data, 'northsouth_field_sep', 20)
    ssccall('data_set_number', data, 'N_hdr_per_xpan', 2)
    ssccall('data_set_number', data, 'offset_xpan_hdr', 1)

    K_cpnt = np.array(
        [
            [0.9, 0.0, 0.19, 0.0, 0.9, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0],
            [0.0, 0.6, 0.05, 0.0, 0.6, 0.0, 0.6, 0.0, 0.42, 0.0, 0.15],
            [0.05, 0.0, 0.42, 0.0, 0.6, 0.0, 0.6, 0.0, 0.42, 0.0, 0.15],
            [0.05, 0.0, 0.42, 0.0, 0.6, 0.0, 0.6, 0.0, 0.42, 0.0, 0.15],
            [0.05, 0.0, 0.42, 0.0, 0.6, 0.0, 0.6, 0.0, 0.42, 0.0, 0.15],
            [0.05, 0.0, 0.42, 0.0, 0.6, 0.0, 0.6, 0.0, 0.15, 0.6, 0.0],
            [0.9, 0.0, 0.19, 0.0, 0.9, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0],
        ],
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'K_cpnt', K_cpnt)

    D_cpnt = np.array(
        [
            [0.085, 0.0635, 0.085, 0.0635, 0.085, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0],
            [0.085, 0.085, 0.085, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.085],
            [0.085, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.085],
            [0.085, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.085],
            [0.085, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.085],
            [0.085, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.0635, 0.085, 0.085, 0.085],
            [0.085, 0.0635, 0.085, 0.0635, 0.085, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0],
        ],
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'D_cpnt', D_cpnt)

    L_cpnt = np.array(
        [
            [0.0, 0.0, 0.0, 0.0, 0.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0],
            [0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 0.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0],
        ],
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'L_cpnt', L_cpnt)

    Type_cpnt = np.array(
        [
            [0.0, 1.0, 0.0, 1.0, 0.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0],
            [1.0, 0.0, 0.0, 2.0, 0.0, 1.0, 0.0, 2.0, 0.0, 2.0, 0.0],
            [0.0, 2.0, 0.0, 2.0, 0.0, 1.0, 0.0, 2.0, 0.0, 2.0, 0.0],
            [0.0, 2.0, 0.0, 2.0, 0.0, 1.0, 0.0, 2.0, 0.0, 2.0, 0.0],
            [0.0, 2.0, 0.0, 2.0, 0.0, 1.0, 0.0, 2.0, 0.0, 2.0, 0.0],
            [0.0, 2.0, 0.0, 2.0, 0.0, 1.0, 0.0, 2.0, 0.0, 0.0, 1.0],
            [0.0, 1.0, 0.0, 1.0, 0.0, -1.0, -1.0, -1.0, -1.0, -1.0, -1.0],
        ],
        dtype=np.float64,
    )
    ssccall('data_set_matrix', data, 'Type_cpnt', Type_cpnt)

    ssccall('data_set_number', data, 'custom_sf_pipe_sizes', 0)
    ssccall('data_set_matrix', data, 'sf_rnr_diams', np.array([[-1.0]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'sf_rnr_wallthicks', np.array([[-1.0]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'sf_rnr_lengths', np.array([[-1.0]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'sf_hdr_diams', np.array([[-1.0]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'sf_hdr_wallthicks', np.array([[-1.0]], dtype=np.float64))
    ssccall('data_set_matrix', data, 'sf_hdr_lengths', np.array([[-1.0]], dtype=np.float64))

    ssccall('data_set_number', data, 'tanks_in_parallel', 1)
    ssccall('data_set_array', data, 'trough_loop_control', np.array([4.0, 1.0, 1.0, 4.0, 1.0, 1.0, 3.0, 1.0, 1.0, 2.0, 1.0, 1.0, 1.0], dtype=np.float64))
    ssccall('data_set_number', data, 'disp_wlim_maxspec', 9.9999999999999998e37)
    # PySAM 7.x renamed 'adjust:constant' -> 'adjust_constant' (colon replaced with
    # underscore after SAM 2022.12.21); the old key name is silently dropped by
    # _set_pysam_inputs since no matching attribute exists.
    ssccall('data_set_number', data, 'adjust_constant', 4)

    module = ssccall('module_create', 'trough_physical_process_heat')
    ok = ssccall('module_exec', module, data)
    if not _to_bool(ok):
        print('trough_physical_process_heat errors:')
        ii = 0
        while True:
            err = ssccall('module_log', module, ii)
            if not err:
                break
            print(err)
            ii += 1
        ssccall('module_free', module)
        ssccall('data_free', data)
        ssccall('unload')
        raise RuntimeError('PySAM TroughPhysical execution failed; see SAM errors above.')

    out = SimpleNamespace()
    out.field_optical_eff = ssccall('data_get_array', data, 'EqOpteff')
    out.field_thermal_power = fac * ssccall('data_get_array', data, 'q_dot_htf_sf_out')
    out.field_Tinlet = ssccall('data_get_array', data, 'T_field_cold_in')
    out.field_Toutlet = ssccall('data_get_array', data, 'T_field_hot_out')
    out.field_mdot = fac * ssccall('data_get_array', data, 'm_dot_field_delivered')
    out.field_elec_parasitics = (
        fac * ssccall('data_get_array', data, 'W_dot_sca_track')
        + fac * ssccall('data_get_array', data, 'W_dot_field_pump')
    )
    out.actual_SM = SM
    out.DNI = ssccall('data_get_array', data, 'beam')
    out.Tamb = ssccall('data_get_array', data, 'twet')

    out.mirror_area = fac * nSCA * aperture_SCA * nloops
    out.land_area = out.mirror_area * CSP.land_mult
    out.nominal_eff = loop_optical_eff
    valid_efficiency = out.field_optical_eff[out.field_optical_eff > 0]
    out.annual_eff = np.mean(valid_efficiency) if valid_efficiency.size else 0.0

    ssccall('data_free', data)
    ssccall('unload')
    return out
