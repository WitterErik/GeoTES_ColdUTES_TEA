classdef DrillingCost
    %   DrillingCost calculates the total drilling and completion costs.
    %   This class is derived from the well costs simplified (WCS) model 
    %   used in GETEM to calculate driling costs. The "Intermediate I"
    %   cost cuve is used because it adequately describes the current costs
    %   to drill new wells in sedimentary basins.

    properties
        NoOfProductionWells
        NoOfInjectionWells
        WellDepth
        ProductionThickness
        CasingSize
        SuccessRate
        PPImultiplier
        WellProfile
        CompletionType
        TotalDrillingCost
        
    end

    methods
        function Drilling = DrillingCost(PWells,IWells,Depth,ProdThickness,CasingSize,SuccessRate,PPI,Profile,CompType)
            %   Drilling calculates the drilling costs for all wells
            Drilling.NoOfProductionWells = PWells;
            Drilling.NoOfInjectionWells = IWells;
            Drilling.WellDepth = Depth;
            Drilling.ProductionThickness = ProdThickness;
            Drilling.CasingSize = CasingSize;
            Drilling.SuccessRate = SuccessRate;
            Drilling.PPImultiplier = PPI; % Conversion from a 2010 dollar year to current year
            Drilling.WellProfile = Profile; % "Vertical" or "Deviated"
            Drilling.CompletionType = CompType; % "Openhole" or "Liner" completion
            Drilling.TotalDrillingCost = [];
        end

        function WellCostCalc = WellCost(Drilling)

            % GETEM Intermediate I drilling cost curves for GeoVision Report  

            if Drilling.WellProfile == "Vertical" && Drilling.CompletionType == "Openhole" && Drilling.CasingSize == "Small"
                WellCostCalc = 0.13709983 * (Drilling.WellDepth)^2 +...	
                129.610328 * Drilling.WellDepth + 1205587.571;
            end

            if Drilling.WellProfile == "Vertical" && Drilling.CompletionType == "Openhole" && Drilling.CasingSize == "Large"
                WellCostCalc = 0.189267288 * (Drilling.WellDepth)^2 +...	
                293.4517365 * Drilling.WellDepth + 1326526.313;
            end

            if Drilling.WellProfile == "Deviated" && Drilling.CompletionType == "Openhole" && Drilling.CasingSize == "Small"
                WellCostCalc = 0.153396734 * (Drilling.WellDepth)^2 +...	
                120.3169953 * Drilling.WellDepth + 1431801.544 - (105 * Drilling.ProductionThickness + 12300);
            end

            if Drilling.WellProfile == "Deviated" && Drilling.CompletionType == "Openhole" && Drilling.CasingSize == "Large"
                WellCostCalc = 0.199504332 * (Drilling.WellDepth)^2 +...	
                296.1301091 * Drilling.WellDepth + 1697867.709 - (189 * Drilling.ProductionThickness + 12300);
            end

            if Drilling.WellProfile == "Vertical" && Drilling.CompletionType == "Liner" && Drilling.CasingSize == "Small"
                WellCostCalc = 0.13709983 * (Drilling.WellDepth)^2 +...	
                129.610328 * Drilling.WellDepth + 1205587.571 + (105 * Drilling.ProductionThickness + 12300);
            end

            if Drilling.WellProfile == "Vertical" && Drilling.CompletionType == "Liner" && Drilling.CasingSize == "Large"
                WellCostCalc = 0.189267288 * (Drilling.WellDepth)^2 +...	
                293.4517365 * Drilling.WellDepth + 1326526.313 + (189 * Drilling.ProductionThickness + 12300);
            end

            if Drilling.WellProfile == "Deviated" && Drilling.CompletionType == "Liner" && Drilling.CasingSize == "Small"
                WellCostCalc = 0.153396734 * (Drilling.WellDepth)^2 +...	
                120.3169953 * Drilling.WellDepth + 1431801.544;
            end

            if Drilling.WellProfile == "Deviated" && Drilling.CompletionType == "Liner" && Drilling.CasingSize == "Large"
                WellCostCalc = 0.199504332 * (Drilling.WellDepth)^2 +...	
                296.1301091 * Drilling.WellDepth + 1697867.709;
            end


% 
%     % Check if casing size and completion type are valid inputs
%     if ~(strcmp(Drilling.CasingSize, 'Small') || strcmp(Drilling.CasingSize, 'Large'))
%         error('Invalid casing size. Must be "Small" or "Large".');
%     end
%     if ~(strcmp(Drilling.CompletionType, 'Openhole') || strcmp(Drilling.CompletionType, 'Liner'))
%         error('Invalid completion type. Must be "Openhole" or "Liner".');
%     end
% 
%     % Calculate well cost based on completion type and casing size
%     if strcmp(Drilling.CompletionType, 'Openhole') && strcmp(Drilling.CasingSize, 'Small')
%         WellCostCalc = 0.13709983 * (Drilling.WellDepth)^2 + 129.610328 * Drilling.WellDepth + 1205587.571;
%     elseif strcmp(Drilling.CompletionType, 'Openhole') && strcmp(Drilling.CasingSize, 'Large')
%         WellCostCalc = 0.189267288 * (Drilling.WellDepth)^2 + 293.4517365 * Drilling.WellDepth + 1326526.313;
%     elseif strcmp(Drilling.CompletionType, 'Liner') && strcmp(Drilling.CasingSize, 'Small')
%         WellCostCalc = 0.153396734 * (Drilling.WellDepth)^2 + 120.3169953 * Drilling.WellDepth + 1431801.544;
%     else
%         WellCostCalc = 0.199504332 * (Drilling.WellDepth)^2 + 296.1301091 * Drilling.WellDepth + 1697867.709;
%     end

        end

        % Total Drilling Cost for all wells
        function TotalDrillCost = TotalDC(Drilling, WellCostCalc)
            Drilling.TotalDrillingCost = WellCostCalc * (Drilling.NoOfProductionWells + ...
            Drilling.NoOfInjectionWells) * Drilling.SuccessRate * Drilling.PPImultiplier;
            IndirectCost = 0.05 * Drilling.TotalDrillingCost; % From GETEM. Includes well testing, engineering, and management.
            TotalDrillCost = Drilling.TotalDrillingCost + IndirectCost;
        end

    end
end