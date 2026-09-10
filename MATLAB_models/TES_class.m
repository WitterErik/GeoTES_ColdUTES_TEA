classdef TES_class
    properties
        duration
        hot_fluid
        cold_fluid
        tau
        power_out
        energy_capacity

        power
        energy

        energy_in_tot
        energy_out_tot
        eff

        fluid_mass
        tank1_volume
        tank2_volume
        Ntank1
        Ntank2
        max_tank_vol

        ins_k
        ins_rho
        ins1_volume
        ins2_volume

        fluid_cost_unit
        tank_cost_corr
        insulation_cost_unit

        fluid_cost
        tank1_cost
        tank2_cost
        insulation1_cost
        insulation2_cost
        total_cost
    end

    methods
        function obj = TES_class(duration, PC_Qin, fluid, Thot, Tcld, tau, max_tank_vol, ins, TES_cost)
            obj.duration = duration;
            obj.power_out = PC_Qin ;
            obj.hot_fluid = fluid_class(fluid) ;
            obj.cold_fluid = fluid_class(fluid) ;
            obj.hot_fluid.T = Thot ;
            obj.cold_fluid.T = Tcld ;
            obj.tau = tau ;
            obj.max_tank_vol = max_tank_vol ;

            obj.power  = zeros(2*8760,1) ;
            obj.energy = zeros(2*8760,1) ;

            obj.ins_k = ins.k ;
            obj.ins_rho = ins.rho ;

            obj.fluid_cost_unit = TES_cost.fluid ;
            obj.tank_cost_corr = TES_cost.tank ;
            obj.insulation_cost_unit = TES_cost.insulation ;

            obj.energy_capacity = obj.duration * obj.power_out ; % MWh-th
        end

        function obj = tank_sizes(obj)
            % Gather fluid data
            obj.hot_fluid = calc_fluid_props(obj.hot_fluid,'T');
            obj.cold_fluid = calc_fluid_props(obj.cold_fluid,'T');
            
            % Calculate fluid mass
            obj.fluid_mass = obj.energy_capacity * 3600e3 / (obj.hot_fluid.cp * obj.hot_fluid.T - obj.cold_fluid.cp * obj.cold_fluid.T) ;

            % Calculate fluid volume in each tank and oversize slightly
            obj.tank1_volume = 1.1 * obj.fluid_mass / obj.hot_fluid.rho ;
            obj.tank2_volume = 1.1 * obj.fluid_mass / obj.cold_fluid.rho ;

            % If tanks are larger than the max. volume then have multiple
            % equally sized tanks
            if obj.tank1_volume > obj.max_tank_vol
                obj.Ntank1 = ceil(obj.tank1_volume / obj.max_tank_vol);
                obj.tank1_volume = obj.tank1_volume / obj.Ntank1 ;
            else
                obj.Ntank1 = 1;
            end

            if obj.tank2_volume > obj.max_tank_vol
                obj.Ntank2 = ceil(obj.tank2_volume / obj.max_tank_vol);
                obj.tank2_volume = obj.tank2_volume / obj.Ntank2 ;
            else
                obj.Ntank2 = 1;
            end

            % Calculate insulation thickness for a given heat loss
            % This method follows that in the solar-PTES code
            % TANK 1: 
            phi = 1 ; % Aspect ratio
            AD = (4. * obj.tank1_volume / (pi * phi)) ^ (1./3.) ;
            AR = 0.5 * AD ;
            AL = AD * phi ;
            AA = pi * AD * (AL + AD/4.) ;
            AA = 8 * AA / 5;

            tau_s = obj.tau * 24 * 3600 ; % convert from days to seconds
            UA = obj.tank1_volume * obj.hot_fluid.rho * obj.hot_fluid.cp / (tau_s * AA) ; % Overall heat transfer coef
             
            % Insulation thickness and volume
            tins = AR * (exp(obj.ins_k / (AR * UA)) - 1) ;
            obj.ins1_volume = pi * tins * (2 + tins) * AL ; % Side wall insulation
            obj.ins1_volume = obj.ins1_volume + 2 * pi * tins * (AR + tins)^2 ; % Top and bottom insulation

            % TANK 2: 
            phi = 1 ; % Aspect ratio
            AD = (4. * obj.tank2_volume / (pi * phi)) ^ (1./3.) ;
            AR = 0.5 * AD ;
            AL = AD * phi ;
            AA = pi * AD * (AL + AD/4.) ;
            AA = 8 * AA / 5;

            tau_s = obj.tau * 24 * 3600 ; % convert from days to seconds
            UA = obj.tank2_volume * obj.cold_fluid.rho * obj.cold_fluid.cp / (tau_s * AA) ; % Overall heat transfer coef
             
            % Insulation thickness and volume
            tins = AR * (exp(obj.ins_k / (AR * UA)) - 1) ;
            obj.ins2_volume = pi * tins * (2 + tins) * AL ; % Side wall insulation
            obj.ins2_volume = obj.ins2_volume + 2 * pi * tins * (AR + tins)^2 ; % Top and bottom insulation

        end

        function obj = TES_annual_energy(obj)
            n = 8761:2*8760 ; 
            pow = obj.power(n) ;
            obj.energy_in_tot = sum(pow(pow>0)) / 1000 ;
            obj.energy_out_tot = -sum(pow(pow<0)) / 1000;
            obj.eff = obj.energy_out_tot / obj.energy_in_tot ;
        end

        function obj = calc_TES_cost(obj)

            obj.fluid_cost = obj.fluid_cost_unit * obj.fluid_mass ;
            obj.insulation1_cost = obj.insulation_cost_unit * obj.ins1_volume * obj.Ntank1 ;
            obj.insulation2_cost = obj.insulation_cost_unit * obj.ins2_volume * obj.Ntank2 ;
            switch obj.tank_cost_corr
                case 0
                    obj.tank1_cost = 3829 * obj.tank1_volume^0.557 * obj.Ntank1 ;
                    obj.tank2_cost = 3829 * obj.tank2_volume^0.557 * obj.Ntank2 ;
                otherwise
                    error('Not implemented yet')
            end

            obj.total_cost = obj.fluid_cost + obj.insulation1_cost + obj.insulation2_cost + ...
                obj.tank1_cost + obj.tank2_cost ;

        end
    end

end

