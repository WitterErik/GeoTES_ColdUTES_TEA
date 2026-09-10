classdef DrillingCostUpdated
    %   DrillingCostUpdated calculates the total drilling and completion costs.
    %   This class is derived from the well costs simplified (WCS) model 
    %   used in GETEM to calculate drilling costs. WCS was updated with
    %   new parameters that represent the current state of sedimentary
    %   drilling. For shallower depths (<= 3,000 m) the costs are similar 
    %   to those between the Intermediate II and Ideal GeoVision cases.
    %   For deeper wells (> 4,500 m) the costs are inbetween the 
    %   Intermediate I and Intermediate II cases. Please refer to
    %   "Vertical Wells for GeoTES.xlsx" and "Lateral Wells for
    %   GeoTES.xlxs" for the WCS model. Costs are in 2010 dollars and are
    %   converted to current dollars using the PPI multiplier.

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
        function Drilling = DrillingCostUpdated(PWells,IWells,Depth,ProdThickness,CasingSize,SuccessRate,PPI,Profile,CompType)
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

            % Determined from updated parameters that represent the
            % current state of sedimentary rock drilling applied to the
            % Well Cost Simplified model developed by SNL (Sandia).  

            if Drilling.WellProfile == "Vertical" && Drilling.CompletionType == "Openhole" && Drilling.CasingSize == "Small"
                WellCostCalc = 0.129294 * (Drilling.WellDepth)^2 +...	
                121.90572 * Drilling.WellDepth + 619928.376659;
            end            

            if Drilling.WellProfile == "Vertical" && Drilling.CompletionType == "Openhole" && Drilling.CasingSize == "Large"
                WellCostCalc = 0.138493 * (Drilling.WellDepth)^2 +...	
                363.789891 * Drilling.WellDepth + 575820.337456;
            end            

            if Drilling.WellProfile == "Deviated" && Drilling.CompletionType == "Openhole" && Drilling.CasingSize == "Small"
                WellCostCalc = 0.132716 * (Drilling.WellDepth)^2 +...	
                148.795084 * Drilling.WellDepth + 786108.246876; 
            end            

            if Drilling.WellProfile == "Deviated" && Drilling.CompletionType == "Openhole" && Drilling.CasingSize == "Large"
                WellCostCalc = 0.141821 * (Drilling.WellDepth)^2 +...	
                394.446239 * Drilling.WellDepth + 863756.505516; 
            end            

            if Drilling.WellProfile == "Vertical" && Drilling.CompletionType == "Liner" && Drilling.CasingSize == "Small"
                WellCostCalc = 0.128944 * (Drilling.WellDepth)^2 +...	
                131.009017 * Drilling.WellDepth + 660304.471681;
            end            

            if Drilling.WellProfile == "Vertical" && Drilling.CompletionType == "Liner" && Drilling.CasingSize == "Large"
                WellCostCalc = 0.138087 * (Drilling.WellDepth)^2 +...	
                373.355967 * Drilling.WellDepth + 630723.904561;
            end

            if Drilling.WellProfile == "Deviated" && Drilling.CompletionType == "Liner" && Drilling.CasingSize == "Small"
                WellCostCalc = 0.132809 * (Drilling.WellDepth)^2 +...	
                154.165493 * Drilling.WellDepth + 836859.95667; 
            end            

            if Drilling.WellProfile == "Deviated" && Drilling.CompletionType == "Liner" && Drilling.CasingSize == "Large"
                WellCostCalc = 0.143118 * (Drilling.WellDepth)^2 +...	
                388.858041 * Drilling.WellDepth + 951705.503869; 
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