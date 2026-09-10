classdef solar_class
    properties
        location
        mirror_type
        nominal_DNI
        solar_multiple
        Tmax
        Tmin

        power
        dumped
        DNI
        nY % number of years

        land_mult
        
        mirror_cost_unit
        land_cost_unit
        HX_cost_unit

        mirror_cost
        land_cost
        HX_cost
        total_cost

        nominal_eff
        annual_eff
        mirror_aperture
        land_area

        available_solar_heat % GWh-th
        solar_thermal_generated % GWh-th
        total_dumped % GWh-th

    end

    methods
        function obj = solar_class(location, mirror_type, nominal_DNI, solar_multiple, Tmax, Tmin, land_mult, CSP_cost, nY)
            obj.location = location ;
            obj.mirror_type = mirror_type ;
            obj.nominal_DNI = nominal_DNI ;
            obj.solar_multiple = solar_multiple ;
            obj.Tmax = Tmax ;
            obj.Tmin = Tmin ;

            obj.land_mult = land_mult ;
            obj.nY = nY ;

            obj.DNI = zeros(8760,1);
            obj.power = zeros(nY*8760,1);
            obj.dumped = zeros(nY*8760,1);
            
            obj.mirror_cost_unit = CSP_cost.mirror ;
            obj.land_cost_unit = CSP_cost.land;
            obj.HX_cost_unit = CSP_cost.HX ;

        end


        function obj = CSP_annual_energy(obj)
            n = (obj.nY-1)*8760+1:obj.nY*8760;

            obj.available_solar_heat = sum(obj.DNI) * obj.mirror_aperture / 1e9 ;
            obj.solar_thermal_generated = sum(obj.power(n)) / 1000;
            obj.total_dumped = sum(obj.dumped(n)) / 1000 ;
            
        end

        % Calculate the solar field cost
        function obj = calc_CSP_cost(obj,PC)

            obj.mirror_cost = obj.mirror_cost_unit * obj.mirror_aperture ;
            obj.land_cost   = obj.land_cost_unit   * obj.land_area ;

            obj.HX_cost     = obj.HX_cost_unit * PC.Qin0 * 1000 ;

            obj.total_cost = obj.mirror_cost + obj.land_cost + obj.HX_cost ;

        end

    end


end

