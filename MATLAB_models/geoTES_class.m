classdef geoTES_class
    properties
        mode % separate, continuous, or flowing
        recovery
        Tinit
        flowrate_per_well_prod % L/s
        flowrate_per_well_inj  % L/s
        Qmax
        depth
        thickness % m
        productivity
        injectivity

        nY

        rho
        cp
        void

        charge_production 
        charge_injection 
        discharge_production 
        discharge_injection 

        charge_prod_Nwell
        charge_inj_Nwell

        discharge_prod_Nwell
        discharge_inj_Nwell

        power
        energy
        net_energy

        energy_in_tot
        energy_out_tot
        eff

        energy_capacity % GWh-th
        mass
        volume
        side_length

    end

    methods
        function obj = geoTES_class(recovery,Tinit,flowrate,Qmax,props,fluid,mode,nY)
            obj.recovery = recovery ;
            obj.Tinit = Tinit ;
            obj.nY = nY ;
            if isstruct(flowrate)
                obj.flowrate_per_well_inj  = flowrate.I;
                obj.flowrate_per_well_prod = flowrate.P;
            else
                obj.flowrate_per_well_inj  = flowrate ;
                obj.flowrate_per_well_prod = flowrate ;
            end
            obj.Qmax = Qmax ;

            obj.rho = props.rho ;
            obj.cp = props.cp;
            obj.void = props.void;
            obj.depth = props.depth ;
            obj.thickness = props.thickness ;
            obj.productivity = props.productivity ;
            obj.injectivity = props.injectivity ;

            obj.mode = mode ;

            obj.charge_production = fluid_class(fluid) ;
            obj.charge_injection = fluid_class(fluid) ;
            obj.discharge_production = fluid_class(fluid) ;
            obj.discharge_injection = fluid_class(fluid) ;

            obj.power  = zeros(nY*8760,1) ;
            obj.energy = zeros(nY*8760,1) ;
        end

        % Calculate the physical size of the RTES
        function obj = geoTES_size(obj)
            if obj.charge_injection.T > obj.charge_production.T
                obj.energy_capacity = max(obj.energy((obj.nY-1)*8760+1:obj.nY*8760))/1000;
            else
                obj.energy_capacity = -min(obj.energy((obj.nY-1)*8760+1:obj.nY*8760))/1000;
            end
            en_cap_J = obj.energy_capacity * 3600e9 ;
            obj.mass = en_cap_J / (obj.cp * abs(obj.charge_injection.T - obj.charge_production.T)); % kg
            obj.volume = obj.mass / obj.rho / (1-obj.void) ;
            obj.side_length = obj.volume ^ (1/3);

            obj.net_energy = (obj.energy(obj.nY*8760) - obj.energy((obj.nY-1)*8760+1))/1000; % Net change in energy content of reservoir over one year, GWh-th
        end

        % Calculate flow rates and number of wells
        function obj = geoTES_well_flows(obj)
            if obj.charge_injection.T > obj.charge_production.T
                max_charge_power = max(obj.power((obj.nY-1)*8760+1:obj.nY*8760)) ;
                max_discharge_power = -min(obj.power((obj.nY-1)*8760+1:obj.nY*8760)) ;
            else
                max_charge_power = -min(obj.power((obj.nY-1)*8760+1:obj.nY*8760)) ;
                max_discharge_power = max(obj.power((obj.nY-1)*8760+1:obj.nY*8760)) ;
            end

            if max_charge_power == 0
                obj.charge_production.mdot = 0;
                obj.charge_injection.mdot = 0;
                obj.charge_production.vdot = 0;
                obj.charge_injection.vdot = 0;
            else
                obj.charge_production.mdot = max_charge_power * 1000 / abs(obj.charge_injection.h-obj.charge_production.h);
                obj.charge_injection.mdot = obj.charge_production.mdot ;
                obj.charge_injection = calc_mdot_vdot(obj.charge_injection,'vdot');
                obj.charge_production = calc_mdot_vdot(obj.charge_production,'vdot');
            end

            if max_discharge_power == 0
                obj.discharge_production.mdot = 0 ;
                obj.discharge_injection.mdot = 0;
                obj.discharge_production.vdot = 0 ;
                obj.discharge_injection.vdot = 0;
            else
                obj.discharge_production.mdot = max_discharge_power * 1000 / abs(obj.discharge_injection.h-obj.discharge_production.h);
                obj.discharge_injection.mdot = obj.discharge_production.mdot ;
                obj.discharge_injection = calc_mdot_vdot(obj.discharge_injection,'vdot');
                obj.discharge_production = calc_mdot_vdot(obj.discharge_production,'vdot');
            end

           
            % Calculate the number of wells
            obj.charge_prod_Nwell = ceil(obj.charge_production.vdot * 1000 / obj.flowrate_per_well_prod);
            obj.charge_inj_Nwell = ceil(obj.charge_injection.vdot * 1000 / obj.flowrate_per_well_inj);

            obj.discharge_prod_Nwell = ceil(obj.discharge_production.vdot * 1000 / obj.flowrate_per_well_prod);
            obj.discharge_inj_Nwell = ceil(obj.discharge_injection.vdot * 1000 / obj.flowrate_per_well_inj);


        end

        function obj = geoTES_annual_energy(obj)

            n = (obj.nY-1)*8760+1:obj.nY*8760 ; 
            pow = obj.power(n) ;
            obj.energy_in_tot = sum(pow(pow>0)) / 1000 ;
            obj.energy_out_tot = -sum(pow(pow<0)) / 1000;
            obj.eff = obj.energy_out_tot / obj.energy_in_tot ;
        end
    end

end
