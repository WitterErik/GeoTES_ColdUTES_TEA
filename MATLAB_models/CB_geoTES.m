%
clear all

% Determine Operating System
c = computer();

% Add paths
switch computer
    case 'GLNXA64' %Linux
        addpath('./Subsurface/','./utility/','./SAM/','./data/')
    case 'PCWIN64' %Windows
        addpath('.\Subsurface\','.\utility\','.\SAM\','.\data\')
end

set_graphics
save_figs = 1; % 1 to save figures, 0 to not save
if ~isfolder('Outputs')
    mkdir('./Outputs');
else
    delete('./Outputs/*')
end


% System level inputs
location = 'Imperial CA' ; % Choose from [Imperial CA], [Elk Hills CA], [ERCOT West]
year     = 2020 ; % Choose from 2020, 2021, 2022

%% Heat engine [discharge] inputs
HE_type = 'HE'; % Type of power cycle [heat engine]
HE_design.Wout  = 100 ;% Power output, MW-e
HE_design.T0    = 15; % Design ambient temperature, C
HE_design.eff   = 0.11 ; % Turbine inlet temperature, C. Calculate Qin from this.
HE_design.TIT   = -1; % This value is unused
HE_design.Qin   = -1; % This value is unused

HE_foff = 'data\example_off_design_v1.xlsx' ; % File location specifying off-design behaviour

HE_cost.power_block = 1000 ; % power block, $/kW-e
HE_cost.HX = 0; % Unused

% Set up high-temp power cycle class
HE = thermo_cycle_class(HE_type,HE_design,HE_foff,HE_cost);

%% Heat pump [charge] inputs
HP_type = 'HP'; % Type of power cycle [heat pump]
HP_design.Win   = 250 ;% Power output, MW-e
HP_design.T0    = 15; % Design ambient temperature, C
HP_design.COP   = 3.7 ; % Coefficient of Performance. Calculate Qout from this.
HP_design.COT   = -1; % This value is unused
HP_design.Qout  = -1; % This value is unused

HP_foff = 'data\example_off_design_HP_v1.xlsx' ; % File location specifying off-design behaviour

HP_cost.power_block = 1000 ; % power block, $/kW-e
HP_cost.HX = 0; % Unused

% Set up high-temp power cycle class
HP = thermo_cycle_class(HP_type,HP_design,HP_foff,HP_cost);

%% Carnot Battery
CB.Tmax = 150 ; % Hot storage temperature, C
CB.Tmin = 5 ;   % Cold storage temperature, C
CB.RTeff = HE.eff0 * HP.COP0 ; % Round-trip efficiency, %

%% Cold thermal storage (geoTES) inputs
gCTES_recovery = 0.95 ; % Fraction of input thermal energy that is recovered
gCTES_Tinit = 50 ; % Initial reservoir temperature, C
gCTES_flowrate = 60 ; % Flow rate per well, L/s
gCTES_Qmax = 10000 ; % Maximum charging power input, MWh-th
gCTES_props.rho = 2000 ; % Rock density, kg/3
gCTES_props.cp = 800 ; % Rock heat capacity, J/kg.K
gCTES_props.void = 0.25 ; % Porosity

gCTES_fluid = 'water';

% Set up geo-TES class
gCTES = geoTES_class(gCTES_recovery,gCTES_Tinit,gCTES_flowrate,gCTES_Qmax,gCTES_props,gCTES_fluid) ;

%% Hot thermal storage (geoTES) inputs
gHTES_recovery = 0.95 ; % Fraction of input thermal energy that is recovered
gHTES_Tinit = 50 ; % Initial reservoir temperature, C
gHTES_flowrate = 60 ; % Flow rate per well, L/s
gHTES_Qmax = 1000 ; % Maximum charging power input, MWh-th
gHTES_props.rho = 2000 ; % Rock density, kg/3
gHTES_props.cp = 800 ; % Rock heat capacity, J/kg.K
gHTES_props.void = 0.25 ; % Porosity

gHTES_fluid = 'water';

% Set up geo-TES class
gHTES = geoTES_class(gHTES_recovery,gHTES_Tinit,gHTES_flowrate,gHTES_Qmax,gHTES_props,gHTES_fluid) ;


%% Financial inputs
finance.lifetime    = 30 ;      % Lifetime
finance.elec_price  = 0.025 ;      % Electricity price - dollars per kWhe. Lazard uses 0.033, ARPA-E uses 0.025. 0.06 is a value that I've used in the past.
finance.inflation   = 0.025;      % Inflation
finance.irr         = 0.10 ;      % Internal Rate of Return
finance.debt_frac   = 0.60 ;      % Project debt fraction - SAM is 0.60
finance.debt_IR     = 0.08 ;      % Debt interest rate
finance.tax_rate    = 0.40 ;      % Tax rate
finance.deprec      = [0.20 0.32 0.20 0.14 0.14]  ; % Depreciation[0.20 0.32 0.192 0.1152 0.1152 0.0576] ;
finance.annual_cost = [1.0 0.0 0.]; % Capital cost incurred in which years [0.80 0.10 0.10] ;
finance.construc_IR = 0.0 ;         % Construction interest rate <- new assumption 25/1/17 to make CFF =1. SAM value -> % 0.08 ;
finance.OnM         = 0.05 ;      % Operations and maintenance cost as a fraction of total capital cost - see Georgiou et al 2018

econ = economics_class(finance);

% Electricity prices
switch location
    case 'Imperial CA'
        load("./data/caliPrices.mat");
        econ.elec_price_hourly = cali.margCost ;
    case 'Elk Hills CA'
        switch year
            case 2020
                error('Elk Hills 2020 price data not available')
            case 2021
                econ.elec_price_hourly = readmatrix('./data/2021_CAIOS_EK_DA.csv','Range','B2:B8761');
            case 2022
                econ.elec_price_hourly = readmatrix('./data/2022_CAIOS_EK_DA.csv','Range','B2:B8761');
        end
    case 'ERCOT West'
        switch year
            case 2020
                econ.elec_price_hourly = readmatrix('./data/2020_PECO__DA.csv','Range','B2:B8761');
            case 2021
                econ.elec_price_hourly = readmatrix('./data/2021_PECO__DA.csv','Range','B2:B8761');
            case 2022
                error('ERCOT West 2022 price data not available')
        end
end
econ.median_price = median(econ.elec_price_hourly);
econ.charge_price = 0.9999 * econ.median_price ; % Charge when price is less than this
econ.discharge_price = 1.001 * econ.median_price ; % Discharge when price is more than this

%% Let's do some calculations!!!


% Specify some fluid properties from the production and injection wells and
% calculate the remaining properties
% Charging cold reservoir
gCTES.charge_production.T = gCTES.Tinit ; % Temperature of produced fluid during charge, C
gCTES.charge_production.p = 10 ; % Pressure of produced fluid during charge, bar
gCTES.charge_production = calc_fluid_props(gCTES.charge_production,'pT');

gCTES.charge_injection.T = CB.Tmin ;
gCTES.charge_injection.q = 0 ;
gCTES.charge_injection = calc_fluid_props(gCTES.charge_injection,'qT');

% Charging hot reservoir
gHTES.charge_production.T = gHTES.Tinit ; % Temperature of produced fluid during charge, C
gHTES.charge_production.p = 10 ; % Pressure of produced fluid during charge, bar
gHTES.charge_production = calc_fluid_props(gHTES.charge_production,'pT');

gHTES.charge_injection.T = CB.Tmax ;
gHTES.charge_injection.q = 0 ;
gHTES.charge_injection = calc_fluid_props(gHTES.charge_injection,'qT');

% Discharging cold reservoir
gCTES.discharge_production.T = CB.Tmin ; % Temperature of produced fluid during charge, C
gCTES.discharge_production.q = 0 ; % Pressure of produced fluid during charge, bar
gCTES.discharge_production = calc_fluid_props(gCTES.discharge_production,'qT');

gCTES.discharge_injection.T = gCTES.Tinit ;
gCTES.discharge_injection.p = 10 ;
gCTES.discharge_injection = calc_fluid_props(gCTES.discharge_injection,'pT');

% Discharging hot reservoir
gHTES.discharge_production.T = CB.Tmax ; % Temperature of produced fluid during charge, C
gHTES.discharge_production.q = 0 ; % Pressure of produced fluid during charge, bar
gHTES.discharge_production = calc_fluid_props(gHTES.discharge_production,'qT');

gHTES.discharge_injection.T = gHTES.Tinit ;
gHTES.discharge_injection.p = 10 ;
gHTES.discharge_injection = calc_fluid_props(gHTES.discharge_injection,'pT');

% Read in location data and extract hourly ambient temperatures
switch location
    case 'Imperial CA'
        location_path = 'data\imperial_ca_32.835205_-115.572398_psmv3_60_tmy.csv' ;
        range = "J4:J8763" ;
    case 'Elk Hills CA'
        location_path = 'data\Elk_Hills_tmy-2021.csv' ;
        range = "L4:L8763" ;
    case 'ERCOT West'
        location_path = 'data\ERCOT_West_tmy-2021.csv' ;
        range = "L4:L8763" ;
    otherwise
        error('Data file for suggested location not found.')
end

Tamb = readmatrix(location_path,"Range",range);

% Simulate two years
HE.Tamb = [Tamb;Tamb];
HP.Tamb = [Tamb;Tamb];
elec_prices = [econ.elec_price_hourly;econ.elec_price_hourly];
dT = 1; % Timestep = 1 hour

% Assume nothing happens on first time step of year
% Remaining time-steps
for i = 2:2*8760

    gCTES.energy(i) = gCTES.energy(i-1);
    gHTES.energy(i) = gHTES.energy(i-1);

    % If prices are low enough, charge the system
    if elec_prices(i) <= econ.charge_price

        % Charge at the design power input
        HP.Win(i) = HP.Win0 ;

        % Calculate the thermal power output under these conditions
        HP = interpolate_off_design(HP,i);

        % Add this heat to the hot storage
        gHTES.power(i) = HP.Qout(i) ;
        gHTES.energy(i) = gHTES.energy(i-1) + gHTES.power(i) * dT * gHTES.recovery ;

        % Assume the cold storage is charged at a proportional rate to
        % the hot storage
        gCTES.power(i) = -HP.Qin0 * (gHTES.power(i) / HP.Qout0) ;
        gCTES.energy(i) = gCTES.energy(i-1) + gCTES.power(i) * dT * gCTES.recovery;



    % If prices are high enough, discharge the system
    elseif elec_prices(i) > econ.discharge_price

        % Check there is enough energy in hot storage
        Qh = HE.Qin0 ;

        if Qh*dT < gHTES.energy(i-1)
            gHTES.power(i) = -Qh ;
        else
            gHTES.power(i) = -gHTES.energy(i-1) / dT;
        end
        gHTES.energy(i) = gHTES.energy(i-1) + gHTES.power(i) * dT ;

        % Hot energy is thermal input to heat engine
        HE.Qin(i) = -gHTES.power(i) ;
        HE = interpolate_off_design(HE,i);

        % Assume the cold storage is discharged at a proportional rate to
        % the hot storage
        gCTES.power(i) = -HE.Qout0 * (gHTES.power(i) / HE.Qin0) ;
        gCTES.energy(i) = gCTES.energy(i-1) + gCTES.power(i) * dT ;

    end

end

% Calculate size of geoTES and flow rates in wells
gCTES = geoTES_size(gCTES) ;
gCTES = geoTES_well_flows(gCTES) ;

gHTES = geoTES_size(gHTES) ;
gHTES = geoTES_well_flows(gHTES) ;


% Annual results for the CSP, power cycle, and storage
HP = PC_annual_energy(HP);
HE = PC_annual_energy(HE);
gCTES = geoTES_annual_energy(gCTES) ;
gHTES = geoTES_annual_energy(gHTES) ;

% Calculate sub-system costs
HP = calc_PC_cost(HP) ;
HE = calc_PC_cost(HE) ;

%% Subsurface cost calculations
% This has been developed by Dayo
% The contents of WorkingScript have been copied here but key variables
% from above (such as number of wells and flow rates) are copied in.
% Working script for GeoTES subsurface costs. The includes capital costs for
% exploration, permitting, drilling & completionss, pumping, surface flow
% lines. It also calculates the subsurface O&M cost, excluding labor cost.

% The input arguments in the defined classes are placeholders. Users should
% define their own arguments based on the project needs.

% Exploration Cost
Exploration_Cost = ExplorationCost("Greenfield",3,20000,1.2); % What is a sensible number of exploration wells? Try the number of charge production wells for now
Total_Exploration_Cost = Exploration_Cost.ExplorationCostCalc();

% Development and Plant Permitting
PPImultiplier = 1.175; % 2012 dollar year (for legal services)
FieldDevPlantPermitting = 1000000 * PPImultiplier; % from GETEM 2012 cost

% ======================================
% Charge Well Capital Cost Calculations
% ======================================

% Drilling cost and completions
Charge_Drilling_Cost = DrillingCost(gCTES.charge_prod_Nwell,gCTES.charge_inj_Nwell,500,200,"Large",1,1.5,"Vertical","Openhole");
Charge_Well_Cost = Charge_Drilling_Cost.WellCost();
Total_Charge_Drilling_Cost = Charge_Drilling_Cost.TotalDC(Charge_Well_Cost);

% Production pumping duty and cost
ResTemp = gCTES.Tinit ; % Is it better to use maximum formation temperature, or minimum? Celcius
Pflowrate = gCTES.flowrate_per_well * gCTES.charge_production.rho / 1000 ; % Flow rate. Units? Convert from L/s to kg/s
Charge_ProdPumping_Estimation = ProductionPumpingCost(ResTemp,Pflowrate,gCTES.charge_prod_Nwell,6370,500,200,"Large","Lineshaft","Openhole",1.553);
Step1 = Charge_ProdPumping_Estimation.HeadProdTop();
Step2 = Charge_ProdPumping_Estimation.HeadSunction(Step1.Prodtop);
Step3 = Charge_ProdPumping_Estimation.Sunctiondepth(Step2);
Step4 = Charge_ProdPumping_Estimation.CasingFriction(Step3,Step1.Prodtop);
Step5 = Charge_ProdPumping_Estimation.Pumppower(Step3,Step4);
Step6 = Charge_ProdPumping_Estimation.Pumpcost(Step5,Step3);
Charge_ProdPumping_Cost_Duty = Charge_ProdPumping_Estimation.TotalPumpDutyCost(Step5,Step6);

% Injection pumping cost
InjTemp = CB.Tmin ; % Which temperature to use?
Iflowrate = gCTES.flowrate_per_well * gCTES.charge_injection.rho / 1000 ; % Flow rate
PressureThermalSource = gCTES.charge_injection.p * 14.5038; % Thermal source pressure, in psi?
Charge_InjPumping_Estimation = InjectionPumpingCost(ResTemp,InjTemp,Iflowrate,Pflowrate,PressureThermalSource,gCTES.charge_inj_Nwell,7645,500,200,"Large","Openhole",1.533,"Discharge");
Step7 = Charge_InjPumping_Estimation.HeadSunction();
Step8 = Charge_InjPumping_Estimation.HeadInjection(Step7);
Step9 = Charge_InjPumping_Estimation.Pumppower(Step8);
Step10 = Charge_InjPumping_Estimation.Pumpcost(Step9);
Charge_InjPumping_Cost_Duty = Charge_InjPumping_Estimation.TotalPumpDutyCost(Step9,Step10);

% Flow line cost. This assumes one pad per well. Will include estimation
% for multi-well pads after discussion with PRM and Earthbridge.
LengthofFlowline = 750; % in meters per well (GETEM assumption)
PipingUnitCost = 256.98; % $ per ft (in 2022 dollars)
TotalNumberofWells = gCTES.charge_prod_Nwell + gCTES.charge_inj_Nwell; % User-defined
Charge_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * TotalNumberofWells;

% Add fluid Processing bulk cost for oilfield from PRM

% ============================
% Charge O&M Cost Calculations
% ============================

% This excludes labor cost which will be determined from the plant gross
% output
% Wellfield Maintenance
Charge_WellFieldMaintenance = 0.015 * (Total_Charge_Drilling_Cost + Charge_FlowLineCost); % 1.5% of Wellfield cost 

% Pump Maintenance
Charge_PumpMaintenance = Charge_ProdPumping_Estimation.PumpMaintenanceCost(Step3,Step6);

% Makeup Water Cost
OilSaturation = 0; % This defaults to an aquifer. For an oil reservoir, the user should input the avg. oil saturation
NumberProductionWells = gCTES.charge_prod_Nwell; % The user should change this based on number of production wells
ProductionRateperWell = Pflowrate; % in kg/s. The user should change this based plant design
MakeupWaterUnitCost = 0.65; % $ per bbl or 5818.50 per arce-ft.
% (https://waterstandard.com/the-role-of-produced-water-treatment-in-shale-plays/).
% $300 per acre-ft in GETEM
SubsurfaceWaterLoss = OilSaturation + 0.001;
Charge_MakeupWaterSubsurface = MakeupWaterUnitCost * NumberProductionWells * ...
    (ProductionRateperWell * 18.0917 * 34.2857 * 365) * SubsurfaceWaterLoss; % in $ per year


% =========================================
% Discharge Well Capital Cost Calculations
% =========================================
%{
% Drilling cost and completions
Discharge_Drilling_Cost = DrillingCost(gCTES.discharge_prod_Nwell,gCTES.discharge_inj_Nwell,1000,500,"Large",1,2.2,"Vertical","Openhole");
Discharge_Well_Cost = Discharge_Drilling_Cost.WellCost();
Total_Discharge_Drilling_Cost = Discharge_Drilling_Cost.TotalDC(Discharge_Well_Cost);

% Production pumping duty and cost
ResTemp = gCTES.Tinit;%LTPC.Tmax ; % Really not sure what to put as the reservoir temperature
Pflowrate = gCTES.flowrate_per_well * gCTES.discharge_production.rho / 1000 ; % Flow rate. Units? Convert from L/s to kg/s
Discharge_ProdPumping_Estimation = ProductionPumpingCost(ResTemp,Pflowrate,gCTES.discharge_prod_Nwell,2500,1000,500,"Large","Lineshaft","Openhole",1.553);
Step1 = Discharge_ProdPumping_Estimation.HeadProdTop();
Step2 = Discharge_ProdPumping_Estimation.HeadSunction(Step1.Prodtop);
Step3 = Discharge_ProdPumping_Estimation.Sunctiondepth(Step2);
Step4 = Discharge_ProdPumping_Estimation.CasingFriction(Step3,Step1.Prodtop);
Step5 = Discharge_ProdPumping_Estimation.Pumppower(Step3,Step4);
Step6 = Discharge_ProdPumping_Estimation.Pumpcost(Step5,Step3);
Discharge_ProdPumping_Cost_Duty = Discharge_ProdPumping_Estimation.TotalPumpDutyCost(Step5,Step6);

% Injection pumping cost
InjTemp = gCTES.Tinit ; % Which temperature to use?
Iflowrate = gCTES.flowrate_per_well * gCTES.discharge_injection.rho / 1000 ; % Flow rate
PressureThermalSource = gCTES.discharge_injection.p * 14.5038; % Thermal source pressure, in psi?
Discharge_InjPumping_Estimation = InjectionPumpingCost(ResTemp,InjTemp,Iflowrate,Pflowrate,PressureThermalSource,gCTES.discharge_inj_Nwell,3000,2500,500,"Large","Openhole",1.533,"Discharge");
Step7 = Discharge_InjPumping_Estimation.HeadSunction();
Step8 = Discharge_InjPumping_Estimation.HeadInjection(Step7);
Step9 = Discharge_InjPumping_Estimation.Pumppower(Step8);
Step10 = Discharge_InjPumping_Estimation.Pumpcost(Step9);
Discharge_InjPumping_Cost_Duty = Discharge_InjPumping_Estimation.TotalPumpDutyCost(Step9,Step10);

% Flow line cost. This assumes one pad per well. Will include estimation
% for multi-well pads after discussion with PRM and Earthbridge.
LengthofFlowline = 750; % in meters per well (GETEM assumption)
PipingUnitCost = 256.98; % $ per ft (in 2022 dollars)
TotalNumberofWells = gCTES.discharge_prod_Nwell + gCTES.discharge_inj_Nwell; % User-defined
Discharge_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * TotalNumberofWells;

% Add fluid Processing bulk cost for oilfield from PRM

% ================================
% Discharge O&M Cost Calculations
% ================================

% This excludes labor cost which will be determined from the plant gross
% output
% Wellfield Maintenance
Discharge_WellFieldMaintenance = 0.015 * (Total_Discharge_Drilling_Cost + Discharge_FlowLineCost); % 1.5% of Wellfield cost 

% Pump Maintenance
Discharge_PumpMaintenance = Discharge_ProdPumping_Estimation.PumpMaintenanceCost(Step3,Step6);

% Makeup Water Cost
OilSaturation = 0; % This defaults to an aquifer. For an oil reservoir, the user should input the avg. oil saturation
NumberProductionWells = gCTES.discharge_prod_Nwell; % The user should change this based on number of production wells
ProductionRateperWell = Pflowrate; % in kg/s. The user should change this based plant design
MakeupWaterUnitCost = 0.65; % $ per bbl or 5818.50 per arce-ft.
% (https://waterstandard.com/the-role-of-produced-water-treatment-in-shale-plays/).
% $300 per acre-ft in GETEM
SubsurfaceWaterLoss = OilSaturation + 0.05;
Discharge_MakeupWaterSubsurface = MakeupWaterUnitCost * NumberProductionWells * ...
    (ProductionRateperWell * 18.0917 * 34.2857 * 365) * SubsurfaceWaterLoss; % in $ per year

%}
% Drilling cost and completions
Discharge_Drilling_Cost = DrillingCost(gHTES.charge_prod_Nwell,gHTES.charge_inj_Nwell,500,200,"Large",1,1.5,"Vertical","Openhole");
Discharge_Well_Cost = Discharge_Drilling_Cost.WellCost();
Total_Discharge_Drilling_Cost = Discharge_Drilling_Cost.TotalDC(Discharge_Well_Cost);

% Production pumping duty and cost
ResTemp = gHTES.Tinit;%LTPC.Tmax ; % Really not sure what to put as the reservoir temperature
Pflowrate = gHTES.flowrate_per_well * gHTES.charge_production.rho / 1000 ; % Flow rate. Units? Convert from L/s to kg/s
Discharge_ProdPumping_Estimation = ProductionPumpingCost(ResTemp,Pflowrate,gHTES.charge_prod_Nwell,6370,500,200,"Large","Lineshaft","Openhole",1.553);
Step1 = Discharge_ProdPumping_Estimation.HeadProdTop();
Step2 = Discharge_ProdPumping_Estimation.HeadSunction(Step1.Prodtop);
Step3 = Discharge_ProdPumping_Estimation.Sunctiondepth(Step2);
Step4 = Discharge_ProdPumping_Estimation.CasingFriction(Step3,Step1.Prodtop);
Step5 = Discharge_ProdPumping_Estimation.Pumppower(Step3,Step4);
Step6 = Discharge_ProdPumping_Estimation.Pumpcost(Step5,Step3);
Discharge_ProdPumping_Cost_Duty = Discharge_ProdPumping_Estimation.TotalPumpDutyCost(Step5,Step6);

% Injection pumping cost
InjTemp = gHTES.Tinit ; % Which temperature to use?
Iflowrate = gHTES.flowrate_per_well * gHTES.charge_injection.rho / 1000 ; % Flow rate
PressureThermalSource = gHTES.charge_injection.p * 14.5038; % Thermal source pressure, in psi?
Discharge_InjPumping_Estimation = InjectionPumpingCost(ResTemp,InjTemp,Iflowrate,Pflowrate,PressureThermalSource,gHTES.charge_inj_Nwell,7645,500,200,"Large","Openhole",1.533,"Discharge");
Step7 = Discharge_InjPumping_Estimation.HeadSunction();
Step8 = Discharge_InjPumping_Estimation.HeadInjection(Step7);
Step9 = Discharge_InjPumping_Estimation.Pumppower(Step8);
Step10 = Discharge_InjPumping_Estimation.Pumpcost(Step9);
Discharge_InjPumping_Cost_Duty = Discharge_InjPumping_Estimation.TotalPumpDutyCost(Step9,Step10);

% Flow line cost. This assumes one pad per well. Will include estimation
% for multi-well pads after discussion with PRM and Earthbridge.
LengthofFlowline = 750; % in meters per well (GETEM assumption)
PipingUnitCost = 256.98; % $ per ft (in 2022 dollars)
TotalNumberofWells = gHTES.charge_prod_Nwell + gHTES.charge_inj_Nwell; % User-defined
Discharge_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * TotalNumberofWells;

% Add fluid Processing bulk cost for oilfield from PRM

% ================================
% Discharge O&M Cost Calculations
% ================================

% This excludes labor cost which will be determined from the plant gross
% output
% Wellfield Maintenance
Discharge_WellFieldMaintenance = 0.015 * (Total_Discharge_Drilling_Cost + Discharge_FlowLineCost); % 1.5% of Wellfield cost 

% Pump Maintenance
Discharge_PumpMaintenance = Discharge_ProdPumping_Estimation.PumpMaintenanceCost(Step3,Step6);

% Makeup Water Cost
OilSaturation = 0; % This defaults to an aquifer. For an oil reservoir, the user should input the avg. oil saturation
NumberProductionWells = gHTES.charge_prod_Nwell; % The user should change this based on number of production wells
ProductionRateperWell = Pflowrate; % in kg/s. The user should change this based plant design
MakeupWaterUnitCost = 0.65; % $ per bbl or 5818.50 per arce-ft.
% (https://waterstandard.com/the-role-of-produced-water-treatment-in-shale-plays/).
% $300 per acre-ft in GETEM
SubsurfaceWaterLoss = OilSaturation + 0.001;
Discharge_MakeupWaterSubsurface = MakeupWaterUnitCost * NumberProductionWells * ...
    (ProductionRateperWell * 18.0917 * 34.2857 * 365) * SubsurfaceWaterLoss; % in $ per year

% =============================
% Total Subsurface Capital Cost
% =============================
SubsurfaceCapitalCost = Total_Exploration_Cost + FieldDevPlantPermitting + ...
    Total_Charge_Drilling_Cost + Charge_ProdPumping_Cost_Duty(2) + ...
    Charge_InjPumping_Cost_Duty(2) + Discharge_ProdPumping_Cost_Duty(2) + ...
    Discharge_InjPumping_Cost_Duty(2) + Charge_FlowLineCost;

% Property Tax and Insurance
PropertyTaxRate = 0.0075; % 0.75% rate from GETEM
AnnualTaxandInsurance = PropertyTaxRate * SubsurfaceCapitalCost;


% =============================
% Total Subsurface O&M Cost
% =========================
SubsurfaceOandMCost = Charge_WellFieldMaintenance + Charge_PumpMaintenance + ...
    Charge_MakeupWaterSubsurface + Discharge_WellFieldMaintenance + ...
    Discharge_PumpMaintenance + Discharge_MakeupWaterSubsurface + ...
    AnnualTaxandInsurance;


%% Calculate finance
econ.subsurface_capital_cost = SubsurfaceCapitalCost ;
econ.OnM_subsurface = SubsurfaceOandMCost ;

econ.surface_capital_cost = HE.total_cost + HP.total_cost;
econ.OnM_surface = econ.OnM * econ.surface_capital_cost ;

econ.Ein = HP.Win_tot ;
econ.Eout = HE.Wout_tot ;
econ = calc_fcr(econ) ;
econ = calc_levelized_cost(econ,'S');
econ = calc_revenue(econ,HP.Win(8761:2*8760),HE.Wout(8761:2*8760));

%% PRINT OUT RESULTS
% Print and plot out technical results
fprintf(1,'\nPOWER OUTPUTS\n\n');
fprintf(1,"Heat pump power input                     = %6.2f MW-e\n",HP.Win0);
fprintf(1,"Heat pump heat output                     = %6.2f MW-th\n",HP.Qout0);
fprintf(1,"Heat pump heat input                      = %6.2f MW-th\n",HP.Qin0);
fprintf(1,"Average heat pump power input             = %6.2f MW-e\n\n",mean(HP.Win(HP.Win(8761:2*8760)>0)));

fprintf(1,"Heat engine power output                  = %6.2f MW-e\n",HE.Wout0);
fprintf(1,"Heat engine heat input                    = %6.2f MW-th\n",HE.Qin0);
fprintf(1,"Heat engine heat output                   = %6.2f MW-th\n",HE.Qout0);
fprintf(1,"Average power cycle output                = %6.2f MW-e\n\n",mean(HE.Wout(HE.Wout(8761:2*8760)>0)));

fprintf(1,"Max. thermal power into hot storage       = %6.2f MW-th\n",max(gHTES.power(8761:2*8760)));
fprintf(1,"Max. thermal power out of hot storage     = %6.2f MW-th\n",-min(gHTES.power(8761:2*8760)));
fprintf(1,"Max. thermal power into cold storage      = %6.2f MW-th\n",max(gCTES.power(8761:2*8760)));
fprintf(1,"Max. thermal power out of cold storage    = %6.2f MW-th\n",-min(gCTES.power(8761:2*8760)));

fprintf(1,"Charge production pump power              = %6.2f MW-e\n",Charge_ProdPumping_Cost_Duty(1)/1e3);
fprintf(1,"Charge injection pump power               = %6.2f MW-e\n",Charge_InjPumping_Cost_Duty(1)/1e3);
fprintf(1,"Discharge production pump power           = %6.2f MW-e\n",Discharge_ProdPumping_Cost_Duty(1)/1e3);
fprintf(1,"Discharge injection pump power            = %6.2f MW-e\n",Discharge_InjPumping_Cost_Duty(1)/1e3);


fprintf(1,'\nANNUAL ENERGY OUTPUTS\n\n');
fprintf(1,"Electricity input to heat pump            = %6.2f GWh-e\n",HP.Win_tot);
fprintf(1,"Electricity output of heat engine         = %6.2f GWh-e\n\n",HE.Wout_tot);

fprintf(1,"Heat delivered to hot storage             = %6.2f GWh-th\n",gHTES.energy_in_tot);
fprintf(1,"Heat extracted from hot storage           = %6.2f GWh-th\n\n",gHTES.energy_out_tot);

fprintf(1,"Heat delivered to cold storage            = %6.2f GWh-th\n",gCTES.energy_in_tot);
fprintf(1,"Heat extracted from cold storage          = %6.2f GWh-th\n\n",gCTES.energy_out_tot);

fprintf(1,"Charge production pump consumption        = %6.2f GWh-e\n",size(gCTES.power(gCTES.power(8761:2*8760)>0),1) * Charge_ProdPumping_Cost_Duty(1)/1e6);
fprintf(1,"Charge injection pump consumption         = %6.2f GWh-e\n",size(gCTES.power(gCTES.power(8761:2*8760)>0),1) * Charge_InjPumping_Cost_Duty(1)/1e6);
fprintf(1,"Discharge production pump consumption     = %6.2f GWh-e\n",size(gCTES.power(gCTES.power(8761:2*8760)<0),1) * Discharge_ProdPumping_Cost_Duty(1)/1e6);
fprintf(1,"Discharge injection pump consumption      = %6.2f GWh-e\n\n",size(gCTES.power(gCTES.power(8761:2*8760)<0),1) * Discharge_InjPumping_Cost_Duty(1)/1e6);

% Print out economic results
fprintf(1,'\nSUBSURFACE COST RESULTS\n\n');
fprintf(1,"Total Exploration Cost          = %6.2f M$\n",Total_Exploration_Cost/1e6);
fprintf(1,"Permitting cost                 = %6.2f M$\n\n",FieldDevPlantPermitting/1e6);
fprintf(1,"Total Charge Drilling Cost      = %6.2f M$\n",Total_Charge_Drilling_Cost/1e6);
fprintf(1,"Charge production pump cost     = %6.2f M$\n",Charge_ProdPumping_Cost_Duty(2)/1e6);
fprintf(1,"Charge injection pump cost      = %6.2f M$\n",Charge_InjPumping_Cost_Duty(2)/1e6);
fprintf(1,"Charge flow line cost           = %6.2f M$\n\n",Charge_FlowLineCost/1e6);

fprintf(1,"Total Discharge Drilling Cost   = %6.2f M$\n",Total_Discharge_Drilling_Cost/1e6);
fprintf(1,"Discharge production pump cost  = %6.2f M$\n",Discharge_ProdPumping_Cost_Duty(2)/1e6);
fprintf(1,"Discharge injection pump cost   = %6.2f M$\n",Discharge_InjPumping_Cost_Duty(2)/1e6);
fprintf(1,"Discharge flow line cost        = %6.2f M$\n\n",Discharge_FlowLineCost/1e6);

fprintf(1,"Subsurface Capital Cost         = %6.2f M$\n",SubsurfaceCapitalCost/1e6);
fprintf(1,"Subsurface O&M Cost             = %6.2f M$\n",SubsurfaceOandMCost/1e6);

fprintf(1,'\nSURFACE COST RESULTS\n\n');
fprintf(1,'Heat pump cost                  = %6.2f M$\n',HP.total_cost/1e6)
fprintf(1,'Heat engine cost                = %6.2f M$\n\n',HE.total_cost/1e6)

fprintf(1,'Surface capital cost            = %6.2f M$\n',econ.surface_capital_cost/1e6)
fprintf(1,'Surface O&M cost                = %6.2f M$\n\n',econ.OnM_surface/1e6)

fprintf(1,'\nTOTAL COST RESULTS\n\n');
fprintf(1,'Total capital cost              = %6.2f M$\n',econ.total_capital_cost/1e6)
fprintf(1,'LCOS                            = %6.2f $/kWh-e\n',econ.LCOS)
fprintf(1,'LCOH                            = %6.2f $/kWh-th\n\n',econ.LCOH)
fprintf(1,'Charging electricity cost       = %6.2f M$\n',econ.charge_cost/1e6)
fprintf(1,'Discharging electricity revenue = %6.2f M$\n',econ.discharge_revenue/1e6)
fprintf(1,'Net revenue                     = %6.2f M$\n\n',econ.net_revenue/1e6)

%% Plot out some economic results
% Save figure formats
formats = {'epsc','fig','svg'};

% Capital cost
Ccap = [Total_Exploration_Cost FieldDevPlantPermitting  ...
    Total_Charge_Drilling_Cost Charge_ProdPumping_Cost_Duty(2) ...
    Charge_InjPumping_Cost_Duty(2) Charge_FlowLineCost ...
    Total_Discharge_Drilling_Cost Discharge_ProdPumping_Cost_Duty(2) ...
    Discharge_InjPumping_Cost_Duty(2) Discharge_FlowLineCost ...
    HP.total_cost HE.total_cost]/1e6;
xlab = {'Exploration','Permitting','Charge drilling','Charge production pumps',...
    'Charge injection pump','Charge flow line',...
    'Discharge drilling','Discharge production pumps',...
    'Discharge injection pump','Discharge flow line',...
    'Heat pump','Heat engine'};

figure(1)
bar(Ccap);
set(gca, 'XTick', 1:12, 'XTickLabel', xlab, 'TickLabelInterpreter', 'latex')
ylabel('Capital cost, M\$');
if save_figs == 1; save_fig(1, './Outputs/capital_cost',formats); end


% Contribution to LCOE
LCOS_mat = [Ccap*econ.FCR*1e6 econ.OnM_subsurface econ.OnM_surface]/econ.Eout/1e6 ;
xlab = {'Exploration','Permitting','Charge drilling','Charge production pumps',...
    'Charge injection pump','Charge flow line',...
    'Discharge drilling','Discharge production pumps',...
    'Discharge injection pump','Discharge flow line',...
    'Heat pump','Heat engine',...
    'Subsurface O\&M','Surface O\&M'};


figure(2)
bar(LCOS_mat);
set(gca, 'XTick', 1:14, 'XTickLabel', xlab, 'TickLabelInterpreter', 'latex')
ylabel('LCOS, \$/kWh-e');
if save_figs == 1; save_fig(2, './Outputs/LCOS',formats); end
%}
%% Plot technical results
figure(3)
n=8761:2*8760;
plot(gCTES.energy(n)/1000);
xlim([0 8760]);
pbaspect([3 1 1])
xlabel('Hour of the year');
ylabel('Energy in cold storage, GWh-th')
if save_figs == 1; save_fig(3, './Outputs/Cold_geoTES_SOC',formats); end

figure(4)
n=8761:2*8760;
plot(gHTES.energy(n)/1000);
xlim([0 8760]);
pbaspect([3 1 1])
xlabel('Hour of the year');
ylabel('Energy in hot storage, GWh-th')
if save_figs == 1; save_fig(4, './Outputs/Hot_geoTES_SOC',formats); end


figure(5)
n=24*27+8761:24*31+8761;
plot(HP.Win(n)); hold on
plot(HE.Wout(n)); 
plot(gHTES.power(n)); hold off
pbaspect([3 1 1])
title('January 27')
xlabel('Hour');
ylabel('Energy, MWh');
legend('Heat pump power input', ...
    'Heat engine power output','Heat to hot geoTES', ...
    'Location','southoutside', ...
    'Orientation','vertical',...
    'FontSize',10);
if save_figs == 1; save_fig(5, './Outputs/January_energy',formats); end



figure(6)
n=24*day(datetime(2022,6,1),'dayofyear')+8761:24*day(datetime(2022,6,4),'dayofyear')+8761;
plot(HP.Win(n)); hold on
plot(HE.Wout(n)); 
plot(gHTES.power(n)); hold off
pbaspect([3 1 1])
title('June 4')
xlabel('Hour');
ylabel('Energy, MWh');
legend('Heat pump power input', ...
    'Heat engine power output','Heat to hot geoTES', ...
    'Location','southoutside', ...
    'Orientation','vertical',...
    'FontSize',10);
if save_figs == 1; save_fig(6, './Outputs/June_energy',formats); end

figure(7)
n=24*27:24*31;
plot(econ.charge_cost_hourly(n)); hold on
plot(econ.discharge_revenue_hourly(n)); hold off
pbaspect([3 1 1])
title('January 27')
xlabel('Hour');
ylabel('Price, \$');
legend('Charge cost', 'Discharge revenue',...
    'Location','southoutside', ...
    'Orientation','vertical',...
    'FontSize',10);
if save_figs == 1; save_fig(5, './Outputs/January_prices',formats); end



figure(8)
n=24*day(datetime(2022,6,1),'dayofyear'):24*day(datetime(2022,6,4),'dayofyear');
plot(econ.charge_cost_hourly(n)); hold on
plot(econ.discharge_revenue_hourly(n)); hold off
pbaspect([3 1 1])
title('June 4')
xlabel('Hour');
ylabel('Price, \$');
legend('Charge cost', 'Discharge revenue',...
    'Location','southoutside', ...
    'Orientation','vertical',...
    'FontSize',10);
if save_figs == 1; save_fig(6, './Outputs/June_proces',formats); end


figure(9)
n=1:8760;
plot(econ.elec_price_hourly(n));
xlim([0 8760]);
pbaspect([3 1 1])
xlabel('Hour of the year');
ylabel('Electricity price, \$/MWh')
if save_figs == 1; save_fig(4, './Outputs/electricity_prices',formats); end
%}
