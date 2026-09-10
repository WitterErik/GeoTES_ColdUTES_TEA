classdef thermo_cycle_class
    properties
        type % 'HE' (heat engine) or 'HP' (heat pump)
        
        % Design values have a 0
        Win0
        Wout0
        Qin0
        Qout0
        Qrej0 % can manually specify heat rejection
        eff0
        COP0
        Tamb0
        fan0 % Parasitic fan loss divided by work output of power cycle

        nY

        % Hourly values are matrices
        Win
        Wout
        Qin
        Qout
        eff
        COP
        Tamb

        Tmax
        Tmin
        mdot

        % Off-design data
        fname
        T0_off
        Qin_off
        Wout_off
        Win_off
        Qout_off

        % Annual totals
        Qin_tot
        Wout_tot
        Win_tot
        Qout_tot
        capacity_factor

        power_block_cost_unit
        HX_cost_unit
        fan_cost_unit

        power_block_cost
        HX_cost
        fan_cost
        total_cost

    end

    methods
        function obj = thermo_cycle_class(PC_type,PC_design,PC_foff,PC_cost,nY)
            obj.type = PC_type ;
            obj.nY = nY; 
            
            switch obj.type
                case 'HE'
                    obj.Wout0 = PC_design.Wout ;
                    obj.Tamb0 = PC_design.T0;
                    obj.Qrej0 = PC_design.Qrej;
                    if PC_design.TIT > 0
                        obj.Tmax  = PC_design.TIT ;
                        obj.eff0  = (1-sqrt((obj.Tamb0+273.15)/(obj.Tmax+273.15))) * 0.98 * 0.9; % Multiply by 0.98 to represent generator efficiency.Multiply by 0.9 to capture other losses.
                        obj.Qin0  = obj.Wout0 / obj.eff0 ;
                    elseif PC_design.Qin > 0
                        obj.Qin0 = PC_design.Qin ;
                        obj.eff0 = obj.Wout0 / obj.Qin0 ;
                    elseif PC_design.eff > 0
                        obj.eff0 = PC_design.eff ;
                        obj.Qin0 = obj.Wout0 / obj.eff0 ;
                    end
                    obj.Qout0 = obj.Qin0 - obj.Wout0 ;
                    obj.fan0 = PC_design.fan ;

                case 'HP'
                    obj.Win0 = PC_design.Win ;
                    obj.Tamb0 = PC_design.T0;
                    obj.Qrej0 = PC_design.Qrej;
                    if PC_design.COT > 0
                        obj.Tmax  = PC_design.COT ;
                        obj.COP0  = 1/(1-((obj.Tamb0+273.15)/(obj.Tmax+273.15))) ;
                        obj.Qout0 = obj.Win0 * obj.COP0 ;
                    elseif PC_design.Qout > 0
                        obj.Qout0 = PC_design.Qout ;
                        obj.COP0  = obj.Qout0 / obj.Win0 ;
                    elseif PC_design.COP > 0
                        obj.COP0  = PC_design.COP ;
                        obj.Qout0 = obj.Win0 * obj.COP0 ;
                    end
                    obj.Qin0 = obj.Qout0 - obj.Win0 ;
                    obj.fan0 = PC_design.fan ;

            end

            % Hourly values for a year
            obj.Win = zeros(nY*8760,1);
            obj.Wout = zeros(nY*8760,1);
            obj.Qin = zeros(nY*8760,1);
            obj.Qout = zeros(nY*8760,1);
            obj.eff = zeros(nY*8760,1);
            obj.COP = zeros(nY*8760,1);
            obj.Tamb  = zeros(nY*8760,1);   

            % Read in off-design data
            obj.fname = PC_foff ;
            off_data  = readmatrix(obj.fname);
            nrow = size(off_data,1);
            ncol = size(off_data,2);

            obj.T0_off = off_data(1,2:ncol) + zeros(nrow-1,ncol-1); % Create meshgrid arrangement (suitable for interp2)
            switch obj.type
                case 'HE'
                        obj.Qin_off = off_data(2:nrow,1) + zeros(nrow-1,ncol-1); % Create meshgrid arrangement (suitable for interp2)
                        obj.Wout_off = off_data(2:nrow,2:ncol);
                case 'HP'
                        obj.Win_off = off_data(2:nrow,1) + zeros(nrow-1,ncol-1); % Create meshgrid arrangement (suitable for interp2)
                        obj.Qout_off = off_data(2:nrow,2:ncol);
            end

            obj.power_block_cost_unit = PC_cost.power_block;
            obj.HX_cost_unit = PC_cost.HX ;
            obj.fan_cost_unit = PC_cost.fan ;
        end

        %{
        function obj = setup_thermo_cycle(obj)
            switch obj.type
                case  'HE'
                    obj.Qin0 = obj.Wout0 / obj.eff0 ;
                    obj.Qout0 = obj.Qin0 - obj.Wout0 ;
                case 'HP'

            end
        end
        %}

        function obj = PC_annual_energy(obj)

            n = (obj.nY-1)*8760+1 : obj.nY*8760;

            switch obj.type
                case 'HE'
                    obj.Qin_tot = sum(obj.Qin(n)) / 1000 ;
                    obj.Wout_tot = sum(obj.Wout(n)) / 1000 ;
                    obj.capacity_factor = obj.Wout_tot * 1000 / (obj.Wout0*24*365) ;
                case 'HP'
                    obj.Win_tot = sum(obj.Win(n)) / 1000 ;
                    obj.Qout_tot = sum(obj.Qout(n)) / 1000 ;
                    obj.capacity_factor = obj.Qout_tot * 1000 / (obj.Qout0*24*365) ;
                    %error('Not implemented yet')
            end
        end


        function obj = interpolate_off_design(obj,i)
            % Normalize the required values by the design values
            x_req = obj.Tamb(i) / obj.Tamb0;
            switch obj.type
                case 'HE'
                    y_req = obj.Qin(i) / obj.Qin0 ;
                    if y_req <= 0
                        obj.Wout(i) = 0;
                    else
                        obj.Wout(i) = obj.Wout0 * interp2(obj.T0_off,obj.Qin_off,obj.Wout_off,x_req,y_req,'spline');
                    end
                case 'HP'
                    y_req = obj.Win(i) / obj.Win0 ;
                    if y_req <= 0
                        obj.Qout(i) = 0 ;
                    else
                        obj.Qout(i) = obj.Qout0 * interp2(obj.T0_off,obj.Win_off,obj.Qout_off,x_req,y_req,'spline');
                    end
                    %error('Not implemented yet');
            end

        end

        function obj = calc_PC_cost(obj)

            switch obj.type
                case 'HE'
                    obj.power_block_cost = obj.power_block_cost_unit * obj.Wout0 * 1000 ;
                    obj.HX_cost = obj.HX_cost_unit * obj.Qrej0 * 1000;
                    obj.fan_cost = obj.fan_cost_unit * obj.fan0 * obj.Wout0 * 1000;
                    obj.total_cost = obj.power_block_cost + obj.HX_cost + obj.fan_cost ;
                case 'HP'
                    obj.power_block_cost = obj.power_block_cost_unit * obj.Win0 * 1000 ;
                    obj.HX_cost = obj.HX_cost_unit * obj.Qrej0 * 1000;
                    obj.fan_cost = obj.fan_cost_unit * obj.fan0 * obj.Win0 * 1000 ;
                    obj.total_cost = obj.power_block_cost + obj.HX_cost + obj.fan_cost;
            end
        end

    end

end
