classdef ExplorationCost
    %   ExplorationCost calculates the total cost for pre-drilling permitting,
    %   exploration drilling, non-drilling exploration activities, and acreage
    %   leasing
    %   

    properties
        SiteType
        NoOfExplorationWells
        WellfieldAcreage
        PPIMultiplier
        
    end

    methods
        function Exploration = ExplorationCost(SiteType,NoOfExpWells,Acreage,PPI)
            % Exploration creates instances for the class ExplorationCost
            % using the listed properties
            %   Detailed explanation goes here
            Exploration.SiteType = SiteType; % "Greenfield" or "Brownfield"
            Exploration.NoOfExplorationWells = NoOfExpWells;
            Exploration.WellfieldAcreage = Acreage; % in acres
            Exploration.PPIMultiplier = PPI; % Assumptions are in 2015 dollars (O&G services)
        end

        function TotalExplorationCost = ExplorationCostCalc(Exploration)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            % Pre-drilling cost
            ExplorationPermittingCost = 25000; % From discussions with PRM. GETEM uses $70,497

            % Lease cost
            LeaseUnitCost = 38; % $ per acre. Average of the $25-$50 range
            Acreage = Exploration.WellfieldAcreage;
            LeaseCost = LeaseUnitCost * Acreage;

            % Exploration Drilling Permitting
            ExpDrillingPermitting = 300000; % GETEM rounded up

            % Exploration drilling, if needed. From PRM discussions
            ExpDrillingUnitCost = 150000; % per well. Wells are not full-sized wells.
            NumberofExpWells = Exploration.NoOfExplorationWells;
            ExpDrillingCost = ExpDrillingUnitCost * NumberofExpWells;

            %Exploration activities cost from GETEM
            if Exploration.SiteType == "Greenfield"
                ExpActivtiesLumpSum = 900000;
            elseif Exploration.SiteType == "Brownfield"
                ExpActivtiesLumpSum = 600000;
            end
            TotalExplorationCost = (Exploration.PPIMultiplier * ExpActivtiesLumpSum) +...
                ExpDrillingCost + ExpDrillingPermitting + LeaseCost + ExplorationPermittingCost;
        end
    end
end