                % ============================ %
                % GeoTES Subsurface Cost Model %
                % ============================ %

% Working script for GeoTES subsurface costs. The includes capital costs for
% exploration, permitting, drilling & completionss, pumping, surface flow
% lines. It also calculates the subsurface O&M cost, excluding labor cost.

% The input arguments in the defined classes are placeholders. Users should
% define their own arguments based on the project needs.


% =========================
% Capital Cost Calculations
% =========================

% Exploration Cost
Exploration_Cost = ExplorationCost("Greenfield",3,20000,1.2);
Total_Exploration_Cost = Exploration_Cost.ExplorationCostCalc();
disp("Total Exploration Cost = $" + Total_Exploration_Cost);

% Development and Plant Permitting
PPImultiplier = 1.175; % 2012 dollar year (for legal services)
FieldDevPlantPermitting = 1000000 * PPImultiplier; % from GETEM 2012 cost

% Drilling cost and completions
Drilling_Cost = DrillingCost(4,5,2500,500,"Large",1,2.2,"Vertical","Openhole");
Well_Cost = Drilling_Cost.WellCost();
Total_Drilling_Cost = Drilling_Cost.TotalDC(Well_Cost);
disp("Total Drilling Cost = $" + Total_Drilling_Cost);

% Production pumping duty and cost
ProdPumping_Estimation = ProductionPumpingCost(50,110,4,2500,2500,500,"Large","Lineshaft","Openhole",1.553);
Step1 = ProdPumping_Estimation.HeadProdTop();
Step2 = ProdPumping_Estimation.HeadSunction(Step1.Prodtop);
Step3 = ProdPumping_Estimation.Sunctiondepth(Step2);
Step4 = ProdPumping_Estimation.CasingFriction(Step3,Step1.Prodtop);
Step5 = ProdPumping_Estimation.Pumppower(Step3,Step4);
Step6 = ProdPumping_Estimation.Pumpcost(Step5,Step3);
ProdPumping_Cost_Duty = ProdPumping_Estimation.TotalPumpDutyCost(Step5,Step6);

% Injection pumping cost
InjPumping_Estimation = InjectionPumpingCost(50,160,146.67,110,187.25,2.5,3000,2500,500,"Large","Openhole",1.533,"Discharge");
Step7 = InjPumping_Estimation.HeadSunction();
Step8 = InjPumping_Estimation.HeadInjection(Step7);
Step9 = InjPumping_Estimation.Pumppower(Step8);
Step10 = InjPumping_Estimation.Pumpcost(Step9);
InjPumping_Cost_Duty = InjPumping_Estimation.TotalPumpDutyCost(Step9,Step10);

% Flow line cost. This assumes one pad per well. Will include estimation
% for multi-well pads after discussion with PRM and Earthbridge.
LengthofFlowline = 750; % in meters per well (GETEM assumption)
PipingUnitCost = 256.98; % $ per ft (in 2022 dollars)
TotalNumberofWells = 11; % User-defined
FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * TotalNumberofWells;

% Add fluid Processing bulk cost for oilfield from PRM


% Total Subsurface Capital Cost
% =============================
SubsurfaceCapitalCost = Total_Exploration_Cost + FieldDevPlantPermitting + ...
    Total_Drilling_Cost + Step6 + Step10 + FlowLineCost;
disp("Subsurface Capital Cost = $" + SubsurfaceCapitalCost);



% =====================
% O&M Cost Calculations
% =====================

% This excludes labor cost which will be determined from the plant gross
% output

% Wellfield Maintenance
WellFieldMaintenance = 0.015 * (Total_Drilling_Cost + FlowLineCost); % 1.5% of Wellfield cost 

% Pump Maintenance
PumpMaintenance = ProdPumping_Estimation.PumpMaintenanceCost(Step3,Step6);

% Makeup Water Cost
OilSaturation = 0; % This defaults to an aquifer. For an oil reservoir, the user should input the avg. oil saturation
NumberProductionWells = 4; % The user should change this based on number of production wells
ProductionRateperWell = 110; % in kg/s. The user should change this based plant design
MakeupWaterUnitCost = 0.65; % $ per bbl or 5818.50 per arce-ft.
% (https://waterstandard.com/the-role-of-produced-water-treatment-in-shale-plays/).
% $300 per acre-ft in GETEM
SubsurfaceWaterLoss = OilSaturation + 0.05;
MakeupWaterSubsurface = MakeupWaterUnitCost * NumberProductionWells * ...
    (ProductionRateperWell * 18.0917 * 34.2857 * 365) * SubsurfaceWaterLoss; % in $ per year

% Property Tax and Insurance
PropertyTaxRate = 0.0075; % 0.75% rate from GETEM
AnnualTaxandInsurance = PropertyTaxRate * SubsurfaceCapitalCost;


% Total Subsurface O&M Cost
% =========================
SubsurfaceOandMCost = WellFieldMaintenance + PumpMaintenance + MakeupWaterSubsurface + AnnualTaxandInsurance;
disp("Subsurface O&M Cost = $" + SubsurfaceOandMCost);
