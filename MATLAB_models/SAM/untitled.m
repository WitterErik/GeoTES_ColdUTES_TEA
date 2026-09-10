function untitled
	function [result] = ssccall(action, arg0, arg1, arg2 )
    [pathstr, fn, fext] = fileparts(mfilename('fullpath'));
        ssclibpath = './';
        ssclib = 'ssc';
    if ~libisloaded(ssclib)
        oldFolder = cd(pathstr);
        loadlibrary(strcat(ssclibpath,ssclib),strcat(ssclibpath,'sscapi.h'));
        cd(oldFolder);
    end
    if strcmp(action,'load')
        if ~libisloaded(ssclib)
            oldFolder = cd(pathstr);
            loadlibrary(strcat(ssclibpath,ssclib),strcat(ssclibpath,'../sscapi.h'));
            cd(oldFolder);
        end
    elseif strcmp(action,'unload')
        if libisloaded(ssclib)
            unloadlibrary(ssclib)    
        end
    elseif strcmp(action,'version')
        result = calllib(ssclib,'ssc_version');
    elseif strcmp(action,'build_info')
        result = calllib(ssclib, 'ssc_build_info');
    elseif strcmp(action,'data_create')
        result = calllib(ssclib, 'ssc_data_create');
        if ( isnullpointer(result) )
            result = 0;
        end
    elseif strcmp(action,'data_free')
        result = calllib(ssclib, 'ssc_data_free', arg0);
    elseif strcmp(action,'data_unassign')
        result = calllib(ssclib, 'ssc_data_unassign', arg0, arg1);
    elseif strcmp(action,'data_query')
        result = calllib(ssclib, 'ssc_data_query', arg0, arg1 );
    elseif strcmp(action,'data_first')
        result = calllib(ssclib, 'ssc_data_first', arg0 );
    elseif strcmp(action,'data_next')
        result = calllib(ssclib, 'ssc_data_next', arg0 );
    elseif strcmp(action,'data_set_string')
        result = calllib(ssclib, 'ssc_data_set_string', arg0, arg1, arg2 );
    elseif strcmp(action,'data_set_number')
        result = calllib(ssclib, 'ssc_data_set_number', arg0, arg1, arg2 );
    elseif strcmp(action,'data_set_array')
        len = length(arg2);
        arr = libpointer( 'doublePtr', arg2 );
        result = calllib(ssclib,'ssc_data_set_array',arg0,arg1,arr,len);
    elseif strcmp(action,'data_set_matrix')
        [nr nc] = size(arg2);
        mat = zeros(nr*nc, 1);
        ii = 1;
        for r=1:nr,
            for c=1:nc,
                mat(ii) = arg2(r,c);
                ii=ii+1;
            end
        end
        arr = libpointer( 'doublePtr', mat );
        result = calllib(ssclib,'ssc_data_set_matrix',arg0,arg1,arr,nr,nc);
    elseif strcmp(action,'data_set_table')
        result = calllib(ssclib,'ssc_data_set_table',arg0,arg1,arg2);
    elseif strcmp(action,'data_get_string')
        result = calllib(ssclib,'ssc_data_get_string',arg0,arg1);
    elseif strcmp(action,'data_get_number')
         p = libpointer('doublePtr',0);
         calllib(ssclib,'ssc_data_get_number', arg0,arg1,p);
         result = get(p,'Value');
    elseif strcmp(action,'data_get_array')
        p_count = libpointer('int32Ptr',0);   
        [xobj] = calllib(ssclib,'ssc_data_get_array',arg0,arg1,p_count);
        setdatatype(xobj,'int64Ptr',p_count.Value,1);
        len = p_count.Value;
        result = zeros( len, 1 );
        for i=1:len,
            pidx = xobj+(i-1);
            setdatatype(pidx,'doublePtr',1,1);
            result(i) = pidx.Value;
        end
    elseif strcmp(action,'data_get_matrix')
        p_rows = libpointer('int32Ptr',0);
        p_cols = libpointer('int32Ptr',0);
        [xobj] = calllib(ssclib,'ssc_data_get_matrix',arg0,arg1,p_rows,p_cols);
        setdatatype(xobj,'int64Ptr',p_rows.Value*p_cols.Value,1);
        nrows = p_rows.Value;
        ncols = p_cols.Value;
        if ( nrows*ncols > 0 )
            result = zeros( nrows, ncols );
            ii=1;
            for r=1:nrows,
                for c=1:ncols,
                    pidx = xobj+(ii-1);
                    setdatatype(pidx,'doublePtr',1,1);
                    result(r,c) = pidx.Value;
                    ii=ii+1;
                end
            end
        end
    elseif strcmp(action,'data_get_table')
        result = calllib(ssclib,'ssc_data_get_table',arg0,arg1);
    elseif strcmp(action,'module_entry')
        result = calllib(ssclib,'ssc_module_entry',arg0);
        if isnullpointer( result ),
            result = 0;
        end
    elseif strcmp(action,'entry_name')
        result = calllib(ssclib,'ssc_entry_name',arg0);
    elseif strcmp(action,'entry_description')
        result = calllib(ssclib,'ssc_entry_description',arg0);
    elseif strcmp(action,'entry_version')
        result = calllib(ssclib,'ssc_entry_version',arg0);
    elseif strcmp(action,'module_var_info')
        result = calllib(ssclib,'ssc_module_var_info',arg0,arg1);
        if isnullpointer( result ),
            result = 0;
        end
    elseif strcmp(action,'info_var_type')
        ty = calllib(ssclib,'ssc_info_var_type',arg0);
        if (ty == 1)
            result = 'input';
        elseif ( ty==2 )
            result = 'output';
        else
            result = 'inout';
        end
    elseif strcmp(action,'info_data_type')
        dt = calllib(ssclib,'ssc_info_data_type',arg0);
        if (dt == 1)
            result = 'string';
        elseif (dt == 2)
            result = 'number';
        elseif (dt == 3)
            result = 'array';
        elseif (dt == 4)
            result = 'matrix';
        elseif (dt == 5)
            result = 'table';
        else
            result = 'invalid';
        end
    elseif strcmp(action,'info_name')
        result = calllib(ssclib,'ssc_info_name',arg0);
    elseif strcmp(action,'info_label')
        result = calllib(ssclib,'ssc_info_label',arg0);
    elseif strcmp(action,'info_units')
        result = calllib(ssclib,'ssc_info_units',arg0);
    elseif strcmp(action,'info_meta')
        result = calllib(ssclib,'ssc_info_meta',arg0);
    elseif strcmp(action,'info_group')
        result = calllib(ssclib,'ssc_info_group',arg0);
    elseif strcmp(action,'info_required')
        result = calllib(ssclib,'ssc_info_required',arg0);
    elseif strcmp(action,'info_constraints')
        result = calllib(ssclib,'ssc_info_constraints',arg0);
    elseif strcmp(action,'info_uihint')
        result = calllib(ssclib,'ssc_info_uihint',arg0);
    elseif strcmp(action,'exec_simple')
        result = calllib(ssclib,'ssc_module_exec_simple',arg0,arg1);
    elseif strcmp(action,'exec_simple_nothread')
        result = calllib(ssclib,'ssc_module_exec_simple_nothread',arg0,arg1);
    elseif strcmp(action,'module_create')
        result = calllib(ssclib,'ssc_module_create',arg0);
        if ( isnullpointer(result) )
            result = 0;
        end
    elseif strcmp(action,'module_free')
        result = calllib(ssclib,'ssc_module_free',arg0);
    elseif strcmp(action,'module_exec_set_print')
        calllib(ssclib,'ssc_module_exec_set_print',arg0);
        result = 0;
    elseif strcmp(action,'module_exec')
        result = calllib(ssclib,'ssc_module_exec',arg0,arg1);
    elseif strcmp(action,'module_log')
        p_type = libpointer('int32Ptr',1);
        p_time = libpointer('singlePtr',1);
        result = calllib(ssclib,'ssc_module_log', arg0, arg1, p_type, p_time);
    elseif strcmp(action,'module_log_detailed')
        p_type = libpointer('int32Ptr',1);
        p_time = libpointer('singlePtr',1);
        text = calllib(ssclib,'ssc_module_log', arg0, arg1, p_type, p_time);
        typetext = 'notice';
        if (p_type.Value == 2)
            typetext = 'warning';
        elseif (p_type.Value == 3)
            typetext = 'error';
        end
        if ( strcmp(text,'') )
            result = 0;
        else
            result = {text , typetext , p_time.Value};
        end
    else
        disp( sprintf('ssccall: invalid action %s', action) );        
        result = 0;
    end
	end
	function bb = isnullpointer(p)
    bb = false;
    try
        setdatatype(p, 'voidPtr', 1, 1);
        deref = get(p);
    catch
        e = lasterror();
        if strcmp(e.identifier, 'MATLAB:libpointer:ValueNotDefined')
            bb = true;
        end
    end
	end
	clear
	ssccall('load');
	disp('Current folder = C:/Users/jmcti/OneDrive/Documents/GeoHybrids_2022/RTES/GeoTES_TEA/SAM');
	disp(sprintf('SSC Version = %d', ssccall('version')));
	disp(sprintf('SSC Build Information = %s', ssccall('build_info')));
	ssccall('module_exec_set_print',0);
	data = ssccall('data_create');
	ssccall('data_set_string', data, 'file_name', 'C:/Users/jmcti/SAM Downloaded Weather Files/35.56981869312573_-119.88060366322233_35.3428_-118.73_psm3-tmy_60_tmy.csv');
	ssccall('data_set_number', data, 'track_mode', 1);
	ssccall('data_set_number', data, 'tilt', 0);
	ssccall('data_set_number', data, 'azimuth', 0);
	ssccall('data_set_number', data, 'I_bn_des', 950);
	ssccall('data_set_number', data, 'T_loop_in_des', 100);
	ssccall('data_set_number', data, 'T_loop_out', 250);
	ssccall('data_set_number', data, 'q_pb_design', 50);
	ssccall('data_set_number', data, 'tshours', 6);
	ssccall('data_set_number', data, 'nSCA', 4);
	ssccall('data_set_number', data, 'nHCEt', 4);
	ssccall('data_set_number', data, 'nColt', 4);
	ssccall('data_set_number', data, 'nHCEVar', 4);
	ssccall('data_set_number', data, 'nLoops', 58);
	ssccall('data_set_number', data, 'eta_pump', 0.84999999999999998);
	ssccall('data_set_number', data, 'HDR_rough', 4.57e-05);
	ssccall('data_set_number', data, 'theta_stow', 170);
	ssccall('data_set_number', data, 'theta_dep', 10);
	ssccall('data_set_number', data, 'Row_Distance', 15);
	ssccall('data_set_number', data, 'FieldConfig', 1);
	ssccall('data_set_number', data, 'is_model_heat_sink_piping', 0);
	ssccall('data_set_number', data, 'L_heat_sink_piping', 50);
	ssccall('data_set_number', data, 'm_dot_htfmin', 1);
	ssccall('data_set_number', data, 'm_dot_htfmax', 12);
	ssccall('data_set_number', data, 'Fluid', 21);
	ssccall('data_set_number', data, 'wind_stow_speed', 25);
	field_fl_props =[ 20   4.1799999999999997   999   0.001   9.9999999999999995e-07   0.58699999999999997   85.299999999999997 ; 40   4.1799999999999997   993   0.00065300000000000004   6.5799999999999999e-07   0.61799999999999999   169 ; 60   4.1799999999999997   984   0.00046700000000000002   4.75e-07   0.64200000000000002   252 ; 80   4.1900000000000004   972   0.00035500000000000001   3.65e-07   0.65700000000000003   336 ; 100   4.21   959   0.00028200000000000002   2.9400000000000001e-07   0.66600000000000004   420 ; 120   4.25   944   0.000233   2.4600000000000001e-07   0.67000000000000004   505 ; 140   4.2800000000000002   927   0.00019699999999999999   2.1199999999999999e-07   0.67000000000000004   590 ; 160   4.3399999999999999   908   0.00017100000000000001   1.8799999999999999e-07   0.66700000000000004   676 ; 180   4.4000000000000004   887   0.00014999999999999999   1.6899999999999999e-07   0.66100000000000003   764 ; 200   4.4900000000000002   865   0.000134   1.55e-07   0.65100000000000002   852 ; 220   4.5800000000000001   842   0.000118   1.4100000000000001e-07   0.64100000000000001   941 ];
	ssccall( 'data_set_matrix', data, 'field_fl_props', field_fl_props );
	ssccall('data_set_number', data, 'T_fp', 10);
	ssccall('data_set_number', data, 'Pipe_hl_coef', 0.45000000000000001);
	ssccall('data_set_number', data, 'SCA_drives_elec', 125);
	ssccall('data_set_number', data, 'water_usage_per_wash', 0.69999999999999996);
	ssccall('data_set_number', data, 'washing_frequency', 12);
	ssccall('data_set_number', data, 'accept_mode', 0);
	ssccall('data_set_number', data, 'accept_init', 0);
	ssccall('data_set_number', data, 'accept_loc', 1);
	ssccall('data_set_number', data, 'mc_bal_hot', 0.20000000000000001);
	ssccall('data_set_number', data, 'mc_bal_cold', 0.20000000000000001);
	ssccall('data_set_number', data, 'mc_bal_sca', 4.5);
	W_aperture =[ 6; 6; 6; 6 ];
	ssccall( 'data_set_array', data, 'W_aperture', W_aperture );
	A_aperture =[ 656; 656; 656; 656 ];
	ssccall( 'data_set_array', data, 'A_aperture', A_aperture );
	TrackingError =[ 0.98799999999999999; 0.98799999999999999; 0.98799999999999999; 0.98799999999999999 ];
	ssccall( 'data_set_array', data, 'TrackingError', TrackingError );
	GeomEffects =[ 0.95199999999999996; 0.95199999999999996; 0.95199999999999996; 0.95199999999999996 ];
	ssccall( 'data_set_array', data, 'GeomEffects', GeomEffects );
	Rho_mirror_clean =[ 0.93000000000000005; 0.93000000000000005; 0.93000000000000005; 0.93000000000000005 ];
	ssccall( 'data_set_array', data, 'Rho_mirror_clean', Rho_mirror_clean );
	Dirt_mirror =[ 0.96999999999999997; 0.96999999999999997; 0.96999999999999997; 0.96999999999999997 ];
	ssccall( 'data_set_array', data, 'Dirt_mirror', Dirt_mirror );
	Error =[ 1; 1; 1; 1 ];
	ssccall( 'data_set_array', data, 'Error', Error );
	Ave_Focal_Length =[ 2.1499999999999999; 2.1499999999999999; 2.1499999999999999; 2.1499999999999999 ];
	ssccall( 'data_set_array', data, 'Ave_Focal_Length', Ave_Focal_Length );
	L_SCA =[ 115; 115; 115; 115 ];
	ssccall( 'data_set_array', data, 'L_SCA', L_SCA );
	L_aperture =[ 14.375; 14.375; 14.375; 14.375 ];
	ssccall( 'data_set_array', data, 'L_aperture', L_aperture );
	ColperSCA =[ 8; 8; 8; 8 ];
	ssccall( 'data_set_array', data, 'ColperSCA', ColperSCA );
	Distance_SCA =[ 1; 1; 1; 1 ];
	ssccall( 'data_set_array', data, 'Distance_SCA', Distance_SCA );
	IAM_matrix =[ 1   0.0327   -0.1351 ; 1   0.0327   -0.1351 ; 1   0.0327   -0.1351 ; 1   0.0327   -0.1351 ];
	ssccall( 'data_set_matrix', data, 'IAM_matrix', IAM_matrix );
	HCE_FieldFrac =[ 1   0   0   0 ; 1   0   0   0 ; 1   0   0   0 ; 1   0   0   0 ];
	ssccall( 'data_set_matrix', data, 'HCE_FieldFrac', HCE_FieldFrac );
	D_2 =[ 0.075999999999999998   0.075999999999999998   0.075999999999999998   0.075999999999999998 ; 0.075999999999999998   0.075999999999999998   0.075999999999999998   0.075999999999999998 ; 0.075999999999999998   0.075999999999999998   0.075999999999999998   0.075999999999999998 ; 0.075999999999999998   0.075999999999999998   0.075999999999999998   0.075999999999999998 ];
	ssccall( 'data_set_matrix', data, 'D_2', D_2 );
	D_3 =[ 0.080000000000000002   0.080000000000000002   0.080000000000000002   0.080000000000000002 ; 0.080000000000000002   0.080000000000000002   0.080000000000000002   0.080000000000000002 ; 0.080000000000000002   0.080000000000000002   0.080000000000000002   0.080000000000000002 ; 0.080000000000000002   0.080000000000000002   0.080000000000000002   0.080000000000000002 ];
	ssccall( 'data_set_matrix', data, 'D_3', D_3 );
	D_4 =[ 0.115   0.115   0.115   0.115 ; 0.115   0.115   0.115   0.115 ; 0.115   0.115   0.115   0.115 ; 0.115   0.115   0.115   0.115 ];
	ssccall( 'data_set_matrix', data, 'D_4', D_4 );
	D_5 =[ 0.12   0.12   0.12   0.12 ; 0.12   0.12   0.12   0.12 ; 0.12   0.12   0.12   0.12 ; 0.12   0.12   0.12   0.12 ];
	ssccall( 'data_set_matrix', data, 'D_5', D_5 );
	D_p =[ 0   0   0   0 ; 0   0   0   0 ; 0   0   0   0 ; 0   0   0   0 ];
	ssccall( 'data_set_matrix', data, 'D_p', D_p );
	Flow_type =[ 1   1   1   1 ; 1   1   1   1 ; 1   1   1   1 ; 1   1   1   1 ];
	ssccall( 'data_set_matrix', data, 'Flow_type', Flow_type );
	Rough =[ 4.5000000000000003e-05   4.5000000000000003e-05   4.5000000000000003e-05   4.5000000000000003e-05 ; 4.5000000000000003e-05   4.5000000000000003e-05   4.5000000000000003e-05   4.5000000000000003e-05 ; 4.5000000000000003e-05   4.5000000000000003e-05   4.5000000000000003e-05   4.5000000000000003e-05 ; 4.5000000000000003e-05   4.5000000000000003e-05   4.5000000000000003e-05   4.5000000000000003e-05 ];
	ssccall( 'data_set_matrix', data, 'Rough', Rough );
	alpha_env =[ 0.02   0.02   0   0 ; 0.02   0.02   0   0 ; 0.02   0.02   0   0 ; 0.02   0.02   0   0 ];
	ssccall( 'data_set_matrix', data, 'alpha_env', alpha_env );
	epsilon_3_11 =[ 100   0.064000000000000001 ; 150   0.066500000000000004 ; 200   0.070000000000000007 ; 250   0.074499999999999997 ; 300   0.080000000000000002 ; 350   0.086499999999999994 ; 400   0.094 ; 450   0.10249999999999999 ; 500   0.112 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_11', epsilon_3_11 );
	epsilon_3_12 =[ 0.65000000000000002 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_12', epsilon_3_12 );
	epsilon_3_13 =[ 0.65000000000000002 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_13', epsilon_3_13 );
	epsilon_3_14 =[ 0 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_14', epsilon_3_14 );
	epsilon_3_21 =[ 100   0.064000000000000001 ; 150   0.066500000000000004 ; 200   0.070000000000000007 ; 250   0.074499999999999997 ; 300   0.080000000000000002 ; 350   0.086499999999999994 ; 400   0.094 ; 450   0.10249999999999999 ; 500   0.112 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_21', epsilon_3_21 );
	epsilon_3_22 =[ 0.65000000000000002 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_22', epsilon_3_22 );
	epsilon_3_23 =[ 0.65000000000000002 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_23', epsilon_3_23 );
	epsilon_3_24 =[ 0 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_24', epsilon_3_24 );
	epsilon_3_31 =[ 100   0.064000000000000001 ; 150   0.066500000000000004 ; 200   0.070000000000000007 ; 250   0.074499999999999997 ; 300   0.080000000000000002 ; 350   0.086499999999999994 ; 400   0.094 ; 450   0.10249999999999999 ; 500   0.112 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_31', epsilon_3_31 );
	epsilon_3_32 =[ 0.65000000000000002 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_32', epsilon_3_32 );
	epsilon_3_33 =[ 0.65000000000000002 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_33', epsilon_3_33 );
	epsilon_3_34 =[ 0 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_34', epsilon_3_34 );
	epsilon_3_41 =[ 100   0.064000000000000001 ; 150   0.066500000000000004 ; 200   0.070000000000000007 ; 250   0.074499999999999997 ; 300   0.080000000000000002 ; 350   0.086499999999999994 ; 400   0.094 ; 450   0.10249999999999999 ; 500   0.112 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_41', epsilon_3_41 );
	epsilon_3_42 =[ 0.65000000000000002 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_42', epsilon_3_42 );
	epsilon_3_43 =[ 0.65000000000000002 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_43', epsilon_3_43 );
	epsilon_3_44 =[ 0 ];
	ssccall( 'data_set_matrix', data, 'epsilon_3_44', epsilon_3_44 );
	alpha_abs =[ 0.96299999999999997   0.96299999999999997   0.80000000000000004   0 ; 0.96299999999999997   0.96299999999999997   0.80000000000000004   0 ; 0.96299999999999997   0.96299999999999997   0.80000000000000004   0 ; 0.96299999999999997   0.96299999999999997   0.80000000000000004   0 ];
	ssccall( 'data_set_matrix', data, 'alpha_abs', alpha_abs );
	Tau_envelope =[ 0.96399999999999997   0.96399999999999997   1   0 ; 0.96399999999999997   0.96399999999999997   1   0 ; 0.96399999999999997   0.96399999999999997   1   0 ; 0.96399999999999997   0.96399999999999997   1   0 ];
	ssccall( 'data_set_matrix', data, 'Tau_envelope', Tau_envelope );
	EPSILON_4 =[ 0.85999999999999999   0.85999999999999999   1   0 ; 0.85999999999999999   0.85999999999999999   1   0 ; 0.85999999999999999   0.85999999999999999   1   0 ; 0.85999999999999999   0.85999999999999999   1   0 ];
	ssccall( 'data_set_matrix', data, 'EPSILON_4', EPSILON_4 );
	EPSILON_5 =[ 0.85999999999999999   0.85999999999999999   1   0 ; 0.85999999999999999   0.85999999999999999   1   0 ; 0.85999999999999999   0.85999999999999999   1   0 ; 0.85999999999999999   0.85999999999999999   1   0 ];
	ssccall( 'data_set_matrix', data, 'EPSILON_5', EPSILON_5 );
	GlazingIntactIn =[ 1   1   0   1 ; 1   1   0   1 ; 1   1   0   1 ; 1   1   0   1 ];
	ssccall( 'data_set_matrix', data, 'GlazingIntactIn', GlazingIntactIn );
	P_a =[ 0.0001   750   750   0 ; 0.0001   750   750   0 ; 0.0001   750   750   0 ; 0.0001   750   750   0 ];
	ssccall( 'data_set_matrix', data, 'P_a', P_a );
	AnnulusGas =[ 27   1   1   1 ; 27   1   1   1 ; 27   1   1   27 ; 27   1   1   27 ];
	ssccall( 'data_set_matrix', data, 'AnnulusGas', AnnulusGas );
	AbsorberMaterial =[ 1   1   1   1 ; 1   1   1   1 ; 1   1   1   1 ; 1   1   1   1 ];
	ssccall( 'data_set_matrix', data, 'AbsorberMaterial', AbsorberMaterial );
	Shadowing =[ 0.93500000000000005   0.93500000000000005   0.93500000000000005   0.96299999999999997 ; 0.93500000000000005   0.93500000000000005   0.93500000000000005   0.96299999999999997 ; 0.93500000000000005   0.93500000000000005   0.93500000000000005   0.96299999999999997 ; 0.93500000000000005   0.93500000000000005   0.93500000000000005   0.96299999999999997 ];
	ssccall( 'data_set_matrix', data, 'Shadowing', Shadowing );
	Dirt_HCE =[ 0.97999999999999998   0.97999999999999998   1   0.97999999999999998 ; 0.97999999999999998   0.97999999999999998   1   0.97999999999999998 ; 0.97999999999999998   0.97999999999999998   1   0.97999999999999998 ; 0.97999999999999998   0.97999999999999998   1   0.97999999999999998 ];
	ssccall( 'data_set_matrix', data, 'Dirt_HCE', Dirt_HCE );
	Design_loss =[ 190   1270   1500   0 ; 190   1270   1500   0 ; 190   1270   1500   0 ; 190   1270   1500   0 ];
	ssccall( 'data_set_matrix', data, 'Design_loss', Design_loss );
	ssccall('data_set_number', data, 'pb_pump_coef', 0.55000000000000004);
	ssccall('data_set_number', data, 'init_hot_htf_percent', 30);
	ssccall('data_set_number', data, 'h_tank', 15);
	ssccall('data_set_number', data, 'cold_tank_max_heat', 0.5);
	ssccall('data_set_number', data, 'u_tank', 0.29999999999999999);
	ssccall('data_set_number', data, 'tank_pairs', 1);
	ssccall('data_set_number', data, 'cold_tank_Thtr', 60);
	ssccall('data_set_number', data, 'h_tank_min', 0.5);
	ssccall('data_set_number', data, 'hot_tank_Thtr', 110);
	ssccall('data_set_number', data, 'hot_tank_max_heat', 1);
	weekday_schedule =[ 6   6   6   6   6   6   5   5   4   4   4   4   4   4   4   4   4   4   4   4   4   5   5   5 ; 6   6   6   6   6   6   5   5   4   4   4   4   4   4   4   4   4   4   4   4   4   5   5   5 ; 6   6   6   6   6   6   5   5   4   4   4   4   4   4   4   4   4   4   4   4   4   5   5   5 ; 6   6   6   6   6   6   5   5   4   4   4   4   4   4   4   4   4   4   4   4   4   5   5   5 ; 6   6   6   6   6   6   5   5   4   4   4   4   4   4   4   4   4   4   4   4   4   5   5   5 ; 3   3   3   3   3   3   3   3   2   2   2   2   1   1   1   1   1   1   2   2   2   3   3   3 ; 3   3   3   3   3   3   3   3   2   2   2   2   1   1   1   1   1   1   2   2   2   3   3   3 ; 3   3   3   3   3   3   3   3   2   2   2   2   1   1   1   1   1   1   2   2   2   3   3   3 ; 3   3   3   3   3   3   3   3   2   2   2   2   1   1   1   1   1   1   2   2   2   3   3   3 ; 6   6   6   6   6   6   5   5   4   4   4   4   4   4   4   4   4   4   4   4   4   5   5   5 ; 6   6   6   6   6   6   5   5   4   4   4   4   4   4   4   4   4   4   4   4   4   5   5   5 ; 6   6   6   6   6   6   5   5   4   4   4   4   4   4   4   4   4   4   4   4   4   5   5   5 ];
	ssccall( 'data_set_matrix', data, 'weekday_schedule', weekday_schedule );
	weekend_schedule =[ 6   6   6   6   6   6   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5 ; 6   6   6   6   6   6   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5 ; 6   6   6   6   6   6   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5 ; 6   6   6   6   6   6   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5 ; 6   6   6   6   6   6   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5 ; 3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3 ; 3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3 ; 3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3 ; 3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3   3 ; 6   6   6   6   6   6   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5 ; 6   6   6   6   6   6   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5 ; 6   6   6   6   6   6   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5   5 ];
	ssccall( 'data_set_matrix', data, 'weekend_schedule', weekend_schedule );
	ssccall('data_set_number', data, 'is_tod_pc_target_also_pc_max', 0);
	ssccall('data_set_number', data, 'is_dispatch', 0);
	ssccall('data_set_number', data, 'disp_frequency', 24);
	ssccall('data_set_number', data, 'disp_horizon', 48);
	ssccall('data_set_number', data, 'disp_max_iter', 35000);
	ssccall('data_set_number', data, 'disp_timeout', 5);
	ssccall('data_set_number', data, 'disp_mip_gap', 0.001);
	ssccall('data_set_number', data, 'disp_time_weighting', 0.98999999999999999);
	ssccall('data_set_number', data, 'disp_rsu_cost_rel', 952);
	ssccall('data_set_number', data, 'disp_csu_cost_rel', 87);
	ssccall('data_set_number', data, 'disp_pen_ramping', 1);
	ssccall('data_set_number', data, 'is_wlim_series', 0);
	wlim_series = csvread( 'C:/Users/jmcti/OneDrive/Documents/GeoHybrids_2022/RTES/GeoTES_TEA/SAM/wlim_series.csv');
	ssccall( 'data_set_array', data, 'wlim_series', wlim_series );
	f_turb_tou_periods =[ 1.05; 1; 1; 1; 1; 1; 1; 1; 1 ];
	ssccall( 'data_set_array', data, 'f_turb_tou_periods', f_turb_tou_periods );
	ssccall('data_set_number', data, 'is_dispatch_series', 0);
	dispatch_series =[ 0 ];
	ssccall( 'data_set_array', data, 'dispatch_series', dispatch_series );
	ssccall('data_set_number', data, 'pb_fixed_par', 0.0054999999999999997);
	bop_array =[ 0; 1; 0; 0.48299999999999998; 0 ];
	ssccall( 'data_set_array', data, 'bop_array', bop_array );
	aux_array =[ 0.023; 1; 0.48299999999999998; 0.57099999999999995; 0 ];
	ssccall( 'data_set_array', data, 'aux_array', aux_array );
	ssccall('data_set_number', data, 'calc_design_pipe_vals', 1);
	ssccall('data_set_number', data, 'V_hdr_cold_max', 3);
	ssccall('data_set_number', data, 'V_hdr_cold_min', 2);
	ssccall('data_set_number', data, 'V_hdr_hot_max', 3);
	ssccall('data_set_number', data, 'V_hdr_hot_min', 2);
	ssccall('data_set_number', data, 'N_max_hdr_diams', 10);
	ssccall('data_set_number', data, 'L_rnr_pb', 25);
	ssccall('data_set_number', data, 'L_rnr_per_xpan', 70);
	ssccall('data_set_number', data, 'L_xpan_hdr', 20);
	ssccall('data_set_number', data, 'L_xpan_rnr', 20);
	ssccall('data_set_number', data, 'Min_rnr_xpans', 1);
	ssccall('data_set_number', data, 'northsouth_field_sep', 20);
	ssccall('data_set_number', data, 'N_hdr_per_xpan', 2);
	ssccall('data_set_number', data, 'offset_xpan_hdr', 1);
	K_cpnt =[ 0.90000000000000002   0   0.19   0   0.90000000000000002   -1   -1   -1   -1   -1   -1 ; 0   0.59999999999999998   0.050000000000000003   0   0.59999999999999998   0   0.59999999999999998   0   0.41999999999999998   0   0.14999999999999999 ; 0.050000000000000003   0   0.41999999999999998   0   0.59999999999999998   0   0.59999999999999998   0   0.41999999999999998   0   0.14999999999999999 ; 0.050000000000000003   0   0.41999999999999998   0   0.59999999999999998   0   0.59999999999999998   0   0.41999999999999998   0   0.14999999999999999 ; 0.050000000000000003   0   0.41999999999999998   0   0.59999999999999998   0   0.59999999999999998   0   0.41999999999999998   0   0.14999999999999999 ; 0.050000000000000003   0   0.41999999999999998   0   0.59999999999999998   0   0.59999999999999998   0   0.14999999999999999   0.59999999999999998   0 ; 0.90000000000000002   0   0.19   0   0.90000000000000002   -1   -1   -1   -1   -1   -1 ];
	ssccall( 'data_set_matrix', data, 'K_cpnt', K_cpnt );
	D_cpnt =[ 0.085000000000000006   0.063500000000000001   0.085000000000000006   0.063500000000000001   0.085000000000000006   -1   -1   -1   -1   -1   -1 ; 0.085000000000000006   0.085000000000000006   0.085000000000000006   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.085000000000000006 ; 0.085000000000000006   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.085000000000000006 ; 0.085000000000000006   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.085000000000000006 ; 0.085000000000000006   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.085000000000000006 ; 0.085000000000000006   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.063500000000000001   0.085000000000000006   0.085000000000000006   0.085000000000000006 ; 0.085000000000000006   0.063500000000000001   0.085000000000000006   0.063500000000000001   0.085000000000000006   -1   -1   -1   -1   -1   -1 ];
	ssccall( 'data_set_matrix', data, 'D_cpnt', D_cpnt );
	L_cpnt =[ 0   0   0   0   0   -1   -1   -1   -1   -1   -1 ; 0   0   0   1   0   0   0   1   0   1   0 ; 0   1   0   1   0   0   0   1   0   1   0 ; 0   1   0   1   0   0   0   1   0   1   0 ; 0   1   0   1   0   0   0   1   0   1   0 ; 0   1   0   1   0   0   0   1   0   0   0 ; 0   0   0   0   0   -1   -1   -1   -1   -1   -1 ];
	ssccall( 'data_set_matrix', data, 'L_cpnt', L_cpnt );
	Type_cpnt =[ 0   1   0   1   0   -1   -1   -1   -1   -1   -1 ; 1   0   0   2   0   1   0   2   0   2   0 ; 0   2   0   2   0   1   0   2   0   2   0 ; 0   2   0   2   0   1   0   2   0   2   0 ; 0   2   0   2   0   1   0   2   0   2   0 ; 0   2   0   2   0   1   0   2   0   0   1 ; 0   1   0   1   0   -1   -1   -1   -1   -1   -1 ];
	ssccall( 'data_set_matrix', data, 'Type_cpnt', Type_cpnt );
	ssccall('data_set_number', data, 'custom_sf_pipe_sizes', 0);
	sf_rnr_diams =[ -1 ];
	ssccall( 'data_set_matrix', data, 'sf_rnr_diams', sf_rnr_diams );
	sf_rnr_wallthicks =[ -1 ];
	ssccall( 'data_set_matrix', data, 'sf_rnr_wallthicks', sf_rnr_wallthicks );
	sf_rnr_lengths =[ -1 ];
	ssccall( 'data_set_matrix', data, 'sf_rnr_lengths', sf_rnr_lengths );
	sf_hdr_diams =[ -1 ];
	ssccall( 'data_set_matrix', data, 'sf_hdr_diams', sf_hdr_diams );
	sf_hdr_wallthicks =[ -1 ];
	ssccall( 'data_set_matrix', data, 'sf_hdr_wallthicks', sf_hdr_wallthicks );
	sf_hdr_lengths =[ -1 ];
	ssccall( 'data_set_matrix', data, 'sf_hdr_lengths', sf_hdr_lengths );
	ssccall('data_set_number', data, 'tanks_in_parallel', 1);
	ssccall('data_set_number', data, 'specified_solar_multiple', 2);
	ssccall('data_set_number', data, 'non_solar_field_land_area_multiplier', 1.1000000000000001);
	trough_loop_control =[ 4; 1; 1; 4; 1; 1; 3; 1; 1; 2; 1; 1; 1 ];
	ssccall( 'data_set_array', data, 'trough_loop_control', trough_loop_control );
	ssccall('data_set_number', data, 'disp_wlim_maxspec', 9.9999999999999998e+37);
	ssccall('data_set_number', data, 'adjust:constant', 4);
	module = ssccall('module_create', 'trough_physical_process_heat'); 
	ok = ssccall('module_exec', module, data);
	if ~ok,
		disp('trough_physical_process_heat errors:'); 
		ii=0;
		while 1,
			err = ssccall('module_log', module, ii);
			if strcmp(err,''),
			      break;
			end
			disp( err );
			ii=ii+1;
		end
		return 
	end
	ssccall('module_free', module);
	annual_energy = ssccall('data_get_number', data, 'annual_energy' );
	disp(sprintf('%s = %g', 'Annual energy (year 1)', annual_energy));
	annual_gross_energy = ssccall('data_get_number', data, 'annual_gross_energy' );
	disp(sprintf('%s = %g', 'Annual gross energy (year 1)', annual_gross_energy));
	annual_thermal_consumption = ssccall('data_get_number', data, 'annual_thermal_consumption' );
	disp(sprintf('%s = %g', 'Annual thermal freeze protection (year 1)', annual_thermal_consumption));
	capacity_factor = ssccall('data_get_number', data, 'capacity_factor' );
	disp(sprintf('%s = %g', 'Capacity factor', capacity_factor));
	annual_electricity_consumption = ssccall('data_get_number', data, 'annual_electricity_consumption' );
	disp(sprintf('%s = %g', 'Annual electricity load (year 1)', annual_electricity_consumption));
	ssccall('data_free', data);
	ssccall('unload');
end