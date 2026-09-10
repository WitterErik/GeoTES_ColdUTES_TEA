classdef economics_class
    properties
        lifetime
        elec_price
        inflation
        irr
        debt_frac
        debt_IR
        tax_rate
        deprec
        annual_cost
        construc_IR
        OnM
        ITC

        RROE
        RINT
        WACC
        CRF
        PVDEP
        PFF
        CFF

        elec_price_hourly
        median_price
        charge_price
        discharge_price

        charge_cost_hourly
        discharge_revenue_hourly
        charge_cost
        discharge_revenue
        net_revenue

        Ein % Annual Electricity input, GWh
        Eout % Annual Electricity output, GWh
        Qout % Annual heat output, GWh; for calculating LCOH
        surface_capital_cost
        subsurface_capital_cost
        total_capital_cost
        total_capital_cost_ITC
        OnM_surface
        OnM_subsurface
        OnM_total
        elec_cost
        FCR
        LCOS
        LCOE
        LCOH
        LCOS_ITC
        LCOE_ITC
        LCOH_ITC
    end

    methods
        function obj = economics_class(inputs)
            obj.lifetime    = inputs.lifetime ;      % Lifetime
            obj.elec_price  = inputs.elec_price ;      % Electricity price - dollars per kWhe. Lazard uses 0.033, ARPA-E uses 0.025. 0.06 is a value that I've used in the past.
            obj.inflation   = inputs.inflation ;      % Inflation
            obj.irr         = inputs.irr ;      % Internal Rate of Return
            obj.debt_frac   = inputs.debt_frac ;      % Project debt fraction - SAM is 0.60
            obj.debt_IR     = inputs.debt_IR ;      % Debt interest rate
            obj.tax_rate    = inputs.tax_rate ;      % Tax rate
            obj.deprec      = inputs.deprec ; % Depreciation[0.20 0.32 0.192 0.1152 0.1152 0.0576] ;
            obj.annual_cost = inputs.annual_cost; % Capital cost incurred in which years [0.80 0.10 0.10] ;
            obj.construc_IR = inputs.construc_IR ;         % Construction interest rate <- new assumption 25/1/17 to make CFF =1. SAM value -> % 0.08 ;
            obj.OnM         = inputs.OnM ;      % Operations and maintenance cost as a fraction of total capital cost - see Georgiou et al 2018
            obj.ITC         = inputs.ITC;       % Investment tax credit
        end

        % Calculate the fixed charge rate and other economic factors
        % Calculations based on the model in SAM
        function obj = calc_fcr(obj)
            obj.RROE = (1 + obj.irr) / (1 + obj.inflation) - 1.0 ;
            obj.RINT = (1 + obj.debt_IR) / (1 + obj.inflation) - 1.0 ;
            obj.WACC = ((1 + obj.inflation) * (1 + obj.RROE) - 1) * (1 - obj.debt_frac) + 1 ;
            obj.WACC = obj.WACC + obj.debt_frac * ((1 + obj.RINT) * (1 + obj.inflation) - 1) * (1 - obj.tax_rate) ;
            obj.WACC = obj.WACC / (1 + obj.inflation) - 1.0 ;

            obj.CRF  = obj.WACC / (1.0 - (1.0 / (1 + obj.WACC)^obj.lifetime) ) ;

            obj.PVDEP = 0.0 ;
            for i = 1:numel(obj.deprec)
                obj.PVDEP = obj.PVDEP + obj.deprec(i) / (((1 + obj.WACC) * (1 + obj.inflation))^i );
            end

            obj.PFF   = (1 - obj.tax_rate * obj.PVDEP) / (1.0 - obj.tax_rate) ;

            obj.CFF   = 0.0 ;
            for i = 1:numel(obj.annual_cost)
                obj.CFF = obj.CFF + (((1 + obj.construc_IR)^(i-0.5) - 1) * (1 - obj.tax_rate) + 1) * obj.annual_cost(i) ;
            end

            obj.FCR   = obj.CRF * obj.PFF * obj.CFF ;
        end


        % Calculate the levelised cost of energy
        function obj = calc_levelized_cost(obj,mode)

            obj.total_capital_cost = (obj.surface_capital_cost + obj.subsurface_capital_cost) ;
            obj.total_capital_cost_ITC = (1-obj.ITC) * obj.total_capital_cost;
            obj.OnM_total = obj.OnM_surface + obj.OnM_subsurface ;
            
            % If revenue previously calculated, use that for electricity cost
            if obj.charge_cost > 0
                obj.elec_cost = obj.charge_cost ;
            % Otherwise estimate from assumed electricity price
            else
                obj.elec_cost = obj.elec_price * obj.Ein * 1e6;
            end

            % Eout is total electricity generated per year, MWh-e
            switch mode
                case 'E'
                    obj.LCOE = (obj.total_capital_cost * obj.FCR + obj.OnM_total + obj.elec_cost) / (obj.Eout * 1e6) ;
                    obj.LCOE_ITC = (obj.total_capital_cost * obj.FCR * (1-obj.ITC) + obj.OnM_total + obj.elec_cost) / (obj.Eout * 1e6) ;
                case 'S'
                    obj.LCOS = (obj.total_capital_cost * obj.FCR + obj.OnM_total + obj.elec_cost) / (obj.Eout * 1e6) ;
                    obj.LCOS_ITC = (obj.total_capital_cost * obj.FCR * (1-obj.ITC) + obj.OnM_total + obj.elec_cost) / (obj.Eout * 1e6) ;
                case 'H'
                    obj.LCOH = (obj.total_capital_cost * obj.FCR + obj.OnM_total + obj.elec_cost) / (obj.Qout * 1e6) ;
                    obj.LCOH_ITC = (obj.total_capital_cost * obj.FCR * (1-obj.ITC) + obj.OnM_total + obj.elec_cost) / (obj.Qout * 1e6) ;
            end

            

        end

        function obj = calc_revenue(obj,Win,Wout)
            % Spending on electricity
            obj.charge_cost_hourly = obj.elec_price_hourly .* Win ;
            obj.discharge_revenue_hourly = obj.elec_price_hourly .* Wout ;

            obj.charge_cost = sum(obj.charge_cost_hourly);
            obj.discharge_revenue = sum(obj.discharge_revenue_hourly);
            obj.net_revenue = obj.discharge_revenue - obj.charge_cost ;
        end

    end

end