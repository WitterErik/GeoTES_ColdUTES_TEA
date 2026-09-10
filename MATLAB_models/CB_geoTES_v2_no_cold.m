%
% Version 2:
%   -   Different flow rates for production and injection wells.
%   -   Different drilling costs for production and injection wells
%   -   Include investment tax credit
%   -   print out number of wells
%   -   Include production and injection pump powers in energy output
%   -   Add dispatch to only discharge power cycle during certain hours
%   -   Operate for N years, rather than just two
%   -   Calculate capacity payments for unused stored energy

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

q=1;
for j = [2736 8208 13680]
    p=1;
    input2(q) = j ;
    for i = 1:0.05:5
        param_out(q,p,:) = run_GeoTES_TEA_nocold(i,j);
        input1(p) = i ;
        p=p+1;
    end
    q=q+1;
end

figure(71)
plot(input1,param_out(:,:,9));

function GeoTES_output = run_GeoTES_TEA_nocold(input1,input2)

save_figs = 0; % 1 to save figures, 0 to not save
write_out = 0;
if ~isfolder('Outputs')
    mkdir('./Outputs');
else
    delete('./Outputs/*')
end



% System level inputs
location = 'ERCOT West' ; % Choose from [Imperial CA], [Elk Hills CA], [ERCOT West]
year     = 2020 ; % Choose from 2020, 2021, 2022
nY = 3; % Number of years to run the simulation for

% GeoTES recovery factor
recov_fac = 0.95 ;

%% Heat engine [discharge] inputs
HE_type = 'HE'; % Type of power cycle [heat engine]
HE_design.Wout  = 10 ;% Power output, MW-e
HE_design.T0    = 25; % Design ambient temperature, C
HE_design.eff   = 0.127;%0.8*(1-sqrt(298/(170+273.15)));%0.127 ; % Turbine inlet temperature, C. Calculate Qin from this.
HE_design.TIT   = -1; % This value is unused
HE_design.Qin   = -1; % This value is unused
HE_design.fan   = input1*2.978 / 19.696 ; % Air fan parasitic, fan power per net power output from heat pump (turbine work - compressor work)*generator_eff
HE_design.Qrej   = HE_design.Wout * 134.27 / 19.701 ; % Heat rejection. For calculating heat exchanger cost. %MW-th. The terms are heat rej / net power generated (kW-th/kW-e)

HE_foff = 'data\example_off_design_v1.xlsx' ; % File location specifying off-design behaviour

HE_cost.power_block = 1000 ; % power block, $/kW-e
HE_cost.HX = 50; % $air-cooler heat exchanger, $/kWh-th
HE_cost.fan = 1000; % air fan cost, $/kW-e

% Set up high-temp power cycle class
HE = thermo_cycle_class(HE_type,HE_design,HE_foff,HE_cost,nY);

%% Heat pump [charge] inputs
HP_type = 'HP'; % Type of power cycle [heat pump]
HPmult = 1 ;
HP_design.COP   = 3.4 ; % Coefficient of Performance. Calculate Qout from this.
HP_design.Win   = HPmult*HE.Wout0 / (HE.eff0 * HP_design.COP * recov_fac) ;%33;%28 ;% 24;% Power input, MW-e
HP_design.T0    = 25; % Design ambient temperature, C
HP_design.COT   = -1; % This value is unused
HP_design.Qout  = -1; % This value is unused
HP_design.fan   = input1*2.4059 / 46.002 ; % Air fan parasitic, fan power per net power input into heat pump (Compressor work - turbine work)/motor_eff
HP_design.Qrej   = HP_design.Win * 112.16 / 46.002 ; % Heat rejection. For calculating heat exchanger cost

HP_foff = 'data\example_off_design_HP_v1.xlsx' ; % File location specifying off-design behaviour

HP_cost.power_block = 1000 ; % power block, $/kW-e
HP_cost.HX = 50; % $air-cooler heat exchanger, $/kWh-th
HP_cost.fan = 1000; % air fan cost, $/kW-e

% Set up high-temp power cycle class
HP = thermo_cycle_class(HP_type,HP_design,HP_foff,HP_cost,nY);

%% Carnot Battery
CB.Tmax = 152.53 ; % Hot storage temperature, C
CB.Tmin = 50 ;   % Cold storage temperature, C
CB.RTeff = HE.eff0 * HP.COP0 ; % Round-trip efficiency, %

%% Hot thermal storage (geoTES) inputs
gHTES_recovery = recov_fac ; % Fraction of input thermal energy that is recovered
gHTES_Tinit = 50 ; % Initial reservoir temperature, C
gHTES_flowrate.P = 100 ; % Flow rate per production well, L/s
gHTES_flowrate.I = 100 ; % Flow rate per injection well, L/s
gHTES_Qmax = 1000 ; % Maximum charging power input, MWh-th
gHTES_props.rho = 2000 ; % Rock density, kg/3
gHTES_props.cp = 710 ; % Rock heat capacity, J/kg.K
gHTES_props.void = 0.3 ; % Porosity
gHTES_props.depth = 1000 ; % Well depth, m
gHTES_props.thickness = 100 ; % Thickness, m
gHTES_props.productivity = input2;%6370 ;
gHTES_props.injectivity  = input2;%7645;
gHTES_fluid = 'water';
gHTES_mode = "push-pull"; % Three operation modes "separate", "continuous", "push-pull"

% Set up geo-TES class
gHTES = geoTES_class(gHTES_recovery,gHTES_Tinit,gHTES_flowrate,gHTES_Qmax,gHTES_props,gHTES_fluid,gHTES_mode,nY) ;


%% Financial inputs
finance.lifetime    = 30 ;      % Lifetime
finance.elec_price  = 0.025 ;      % Electricity price - dollars per kWhe. Lazard uses 0.033, ARPA-E uses 0.025. 0.06 is a value that I've used in the past.
finance.inflation   = 0.025;      % Inflation
finance.irr         = 0.10 ;      % Internal Rate of Return
finance.debt_frac   = 0.60 ;      % Project debt fraction - SAM is 0.60
finance.debt_IR     = 0.08 ;      % Debt interest rate
finance.tax_rate    = 0.2984 ;      % Tax rate
finance.deprec      = [0.20 0.32 0.20 0.14 0.14]  ; % Depreciation[0.20 0.32 0.192 0.1152 0.1152 0.0576] ;
finance.annual_cost = [1.0 0.0 0.]; % Capital cost incurred in which years [0.80 0.10 0.10] ;
finance.construc_IR = 0.0 ;         % Construction interest rate <- new assumption 25/1/17 to make CFF =1. SAM value -> % 0.08 ;
finance.OnM         = 0.015 ;      % Operations and maintenance cost as a fraction of total capital cost - see Georgiou et al 2018
finance.ITC         = 0.40 ;
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
econ.charge_price = 0.9999 * econ.median_price ; % Charge when price is less than this %18
econ.discharge_price = 1.0001 * econ.median_price ; % Discharge when price is more than this%79

if HPmult >=1
    Ndis = 12;
    Nchg = ceil(Ndis / HPmult);
    Nstr = 24 - Ndis - Nchg ;

    ophour = [ones(1,Ndis) -ones(1,Nchg) zeros(1,Nstr)]; % Discharge is 1, charge is -1
else
    Nchg = ceil(24 / (HPmult + 1));
    Ndis = 24 - Nchg ;
    ophour = [ones(1,Ndis) -ones(1,Nchg) ]; % Discharge is 1, charge is -1
end

opmode = 'hour'; % 'price' or 'hour'

%% Let's do some calculations!!!


% Specify some fluid properties from the production and injection wells and
% calculate the remaining properties

% Charging hot reservoir
gHTES.charge_production.T = gHTES.Tinit ; % Temperature of produced fluid during charge, C
gHTES.charge_production.p = 7 ; % Pressure of produced fluid during charge, bar
gHTES.charge_production = calc_fluid_props(gHTES.charge_production,'pT');

gHTES.charge_injection.T = CB.Tmax ;
gHTES.charge_injection.q = 0 ;
gHTES.charge_injection = calc_fluid_props(gHTES.charge_injection,'qT');
%if gHTES.charge_injection.p < 20
%    gHTES.charge_injection.p = 20;
%    gHTES.charge_injection = calc_fluid_props(gHTES.charge_injection,'pT');
%end

% Discharging hot reservoir
gHTES.discharge_production.T = CB.Tmax ; % Temperature of produced fluid during charge, C
gHTES.discharge_production.q = 0 ; % Pressure of produced fluid during charge, bar
gHTES.discharge_production = calc_fluid_props(gHTES.discharge_production,'qT');
%if gHTES.discharge_production.p < 20
%    gHTES.discharge_production.p = 20;
%    gHTES.discharge_production = calc_fluid_props(gHTES.discharge_production,'pT');
%end

gHTES.discharge_injection.T = gHTES.Tinit ;
gHTES.discharge_injection.p = gHTES.discharge_production.p ;
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
HE.Tamb = repmat(Tamb,nY,1);
HP.Tamb = repmat(Tamb,nY,1);
elec_prices = repmat(econ.elec_price_hourly,nY,1);
dT = 1; % Timestep = 1 hour
hour  = 2; % hour of the day

% Assume nothing happens on first time step of year
% Remaining time-steps
for i = 2:nY*8760

    gHTES.energy(i) = gHTES.energy(i-1);

    switch opmode
        case 'price'
            if elec_prices(i) <= econ.charge_price
                dispatch = -1;
            elseif elec_prices(i) > econ.discharge_price
                dispatch = 1;
            end
        case 'hour'
            dispatch = ophour(hour);
    end

    % If prices are low enough, charge the system
    if dispatch < 0

        % Charge at the design power input
        HP.Win(i) = HP.Win0 ;

        % Calculate the thermal power output under these conditions
        HP = interpolate_off_design(HP,i);

        % Add this heat to the hot storage
        gHTES.power(i) = HP.Qout(i) ;
        gHTES.energy(i) = gHTES.energy(i-1) + gHTES.power(i) * dT * gHTES.recovery ;


    % If prices are high enough, discharge the system
    elseif dispatch > 0

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

    end
    
    hour = hour + 1;
    if hour == 25
        hour = 1;
    end
end

% Calculate size of geoTES and flow rates in wells
gHTES = geoTES_size(gHTES) ;
gHTES = geoTES_well_flows(gHTES) ;


% Annual results for the CSP, power cycle, and storage
HP = PC_annual_energy(HP);
HE = PC_annual_energy(HE);
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
% Source Well Capital Cost Calculations
% ======================================

% Source wells are the lower temperature part of the hot reservoir.
% They provide the source heat to the heat pump

% Drilling cost and completions
if (strcmp(gHTES.mode,'push-pull'))
    % Number of source wells
    Nsource_well = max(gHTES.charge_prod_Nwell, gHTES.discharge_inj_Nwell);
    Hot_source_Drilling_Cost = DrillingCostUpdated(Nsource_well,0,gHTES.depth,gHTES.thickness,"Small",1,1.5,"Deviated","Liner");
elseif (strcmp(gHTES.mode,'separate'))
    Nsource_well = gHTES.charge_prod_Nwell+gHTES.charge_inj_Nwell;
    Hot_source_Drilling_Cost = DrillingCostUpdated(gHTES.charge_prod_Nwell,gHTES.charge_inj_Nwell,gHTES.depth,gHTES.thickness,"Small",1,1.5,"Deviated","Liner");
end

Hot_source_Well_Cost = Hot_source_Drilling_Cost.WellCost();
Total_Hot_source_Drilling_Cost = Hot_source_Drilling_Cost.TotalDC(Hot_source_Well_Cost);

% Production pumping duty and cost
ResTemp = gHTES.Tinit;%LTPC.Tmax ; % Really not sure what to put as the reservoir temperature
Pflowrate = gHTES.flowrate_per_well_prod * gHTES.charge_production.rho / 1000 ; % Flow rate. Units? Convert from L/s to kg/s
Hot_source_ProdPumping_Estimation = ProductionPumpingCost(ResTemp,Pflowrate,gHTES.charge_prod_Nwell,gHTES.productivity,gHTES.depth,gHTES.thickness,"Small","Lineshaft","Liner",1.553);
Step1 = Hot_source_ProdPumping_Estimation.HeadProdTop();
Step2 = Hot_source_ProdPumping_Estimation.HeadSunction(Step1.Prodtop);
Step3 = Hot_source_ProdPumping_Estimation.Sunctiondepth(Step2);
Step4 = Hot_source_ProdPumping_Estimation.CasingFriction(Step3,Step1.Prodtop);
Step5 = Hot_source_ProdPumping_Estimation.Pumppower(Step3,Step4);
Step6 = Hot_source_ProdPumping_Estimation.Pumpcost(Step5,Step3);
Hot_source_ProdPumping_Cost_Duty = Hot_source_ProdPumping_Estimation.TotalPumpDutyCost(Step5,Step6);

% Injection pumping cost
InjTemp = gHTES.Tinit ; % Which temperature to use?
Iflowrate = gHTES.flowrate_per_well_inj * gHTES.discharge_injection.rho / 1000 ; % Flow rate
PressureThermalSource = gHTES.discharge_injection.p * 14.5038; % Thermal source pressure, in psi?
Hot_source_InjPumping_Estimation = InjectionPumpingCost(ResTemp,InjTemp,Iflowrate,Pflowrate,PressureThermalSource,gHTES.discharge_inj_Nwell,gHTES.injectivity,gHTES.depth,gHTES.thickness,"Small","Liner",1.533,"Charge");
Step7 = Hot_source_InjPumping_Estimation.HeadSunction();
Step8 = Hot_source_InjPumping_Estimation.HeadInjection(Step7);
Step9 = Hot_source_InjPumping_Estimation.Pumppower(Step8);
Step10 = Hot_source_InjPumping_Estimation.Pumpcost(Step9);
Hot_source_InjPumping_Cost_Duty = Hot_source_InjPumping_Estimation.TotalPumpDutyCost(Step9,Step10);

% Flow line cost. This assumes one pad per well. Will include estimation
% for multi-well pads after discussion with PRM and Earthbridge.
LengthofFlowline = 300; % in meters per well (GETEM assumption)
PipingUnitCost = 256.98; % $ per ft (in 2022 dollars)
TotalNumberofWells = Nsource_well; % User-defined
Hot_source_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * TotalNumberofWells;

% Add fluid Processing bulk cost for oilfield from PRM

% ================================
% Source Well O&M Cost Calculations
% ================================

% This excludes labor cost which will be determined from the plant gross
% output
% Wellfield Maintenance
Hot_source_WellFieldMaintenance = 0.015 * (Total_Hot_source_Drilling_Cost + Hot_source_FlowLineCost); % 1.5% of Wellfield cost 

% Pump Maintenance
Hot_source_PumpMaintenance = Hot_source_ProdPumping_Estimation.PumpMaintenanceCost(Step3,Step6);

% Makeup Water Cost
OilSaturation = 0; % This defaults to an aquifer. For an oil reservoir, the user should input the avg. oil saturation
NumberProductionWells = Nsource_well; % The user should change this based on number of production wells
ProductionRateperWell = Pflowrate; % in kg/s. The user should change this based plant design
MakeupWaterUnitCost = 0.65; % $ per bbl or 5818.50 per arce-ft.
% (https://waterstandard.com/the-role-of-produced-water-treatment-in-shale-plays/).
% $300 per acre-ft in GETEM
SubsurfaceWaterLoss = OilSaturation + 0.001;
Hot_source_MakeupWaterSubsurface = MakeupWaterUnitCost * NumberProductionWells * ...
    (ProductionRateperWell * 18.0917 * 34.2857 * 365) * SubsurfaceWaterLoss; % in $ per year


% ======================================
% Sink Well Capital Cost Calculations
% ======================================

% Sink wells are the higher temperature part of the hot reservoir.
% They are the sink for the heat pump

% Drilling cost and completions
if (strcmp(gHTES.mode,'push-pull'))
    % Number of sink wells
    Nsink_well = max(gHTES.discharge_prod_Nwell, gHTES.charge_inj_Nwell);
    Hot_sink_Drilling_Cost = DrillingCostUpdated(Nsink_well,0,gHTES.depth,gHTES.thickness,"Small",1,1.5,"Deviated","Liner");
elseif (strcmp(gHTES.mode,'separate'))
    Nsink_well = gHTES.discharge_prod_Nwell+gHTES.discharge_inj_Nwell ;
    Hot_sink_Drilling_Cost = DrillingCostUpdated(gHTES.discharge_prod_Nwell,gHTES.discharge_inj_Nwell,gHTES.depth,gHTES.thickness,"Small",1,1.5,"Deviated","Liner");
end

Hot_sink_Well_Cost = Hot_sink_Drilling_Cost.WellCost();
Total_Hot_sink_Drilling_Cost = Hot_sink_Drilling_Cost.TotalDC(Hot_sink_Well_Cost);

% Production pumping duty and cost
ResTemp = CB.Tmax;%LTPC.Tmax ; % Really not sure what to put as the reservoir temperature
Pflowrate = gHTES.flowrate_per_well_prod * gHTES.discharge_production.rho / 1000 ; % Flow rate. Units? Convert from L/s to kg/s
Hot_sink_ProdPumping_Estimation = ProductionPumpingCost(ResTemp,Pflowrate,gHTES.discharge_prod_Nwell,gHTES.productivity,gHTES.depth,gHTES.thickness,"Small","Lineshaft","Liner",1.553);
Step1 = Hot_sink_ProdPumping_Estimation.HeadProdTop();
Step2 = Hot_sink_ProdPumping_Estimation.HeadSunction(Step1.Prodtop);
Step3 = Hot_sink_ProdPumping_Estimation.Sunctiondepth(Step2);
Step4 = Hot_sink_ProdPumping_Estimation.CasingFriction(Step3,Step1.Prodtop);
Step5 = Hot_sink_ProdPumping_Estimation.Pumppower(Step3,Step4);
Step6 = Hot_sink_ProdPumping_Estimation.Pumpcost(Step5,Step3);
Hot_sink_ProdPumping_Cost_Duty = Hot_sink_ProdPumping_Estimation.TotalPumpDutyCost(Step5,Step6);

% Injection pumping cost
InjTemp = CB.Tmax ; % Which temperature to use?
Iflowrate = gHTES.flowrate_per_well_inj * gHTES.charge_injection.rho / 1000 ; % Flow rate
PressureThermalSource = gHTES.charge_injection.p * 14.5038; % Thermal source pressure, in psi?
Hot_sink_InjPumping_Estimation = InjectionPumpingCost(ResTemp,InjTemp,Iflowrate,Pflowrate,PressureThermalSource,gHTES.charge_inj_Nwell,gHTES.injectivity,gHTES.depth,gHTES.thickness,"Small","Liner",1.533,"Charge");
Step7 = Hot_sink_InjPumping_Estimation.HeadSunction();
Step8 = Hot_sink_InjPumping_Estimation.HeadInjection(Step7);
Step9 = Hot_sink_InjPumping_Estimation.Pumppower(Step8);
Step10 = Hot_sink_InjPumping_Estimation.Pumpcost(Step9);
Hot_sink_InjPumping_Cost_Duty = Hot_sink_InjPumping_Estimation.TotalPumpDutyCost(Step9,Step10);

% Flow line cost. This assumes one pad per well. Will include estimation
% for multi-well pads after discussion with PRM and Earthbridge.
LengthofFlowline = 300; % in meters per well (GETEM assumption)
PipingUnitCost = 256.98; % $ per ft (in 2022 dollars)
TotalNumberofWells = Nsink_well; % User-defined
Hot_sink_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * TotalNumberofWells;

% Add fluid Processing bulk cost for oilfield from PRM

% ================================
% Hot Well O&M Cost Calculations
% ================================

% This excludes labor cost which will be determined from the plant gross
% output
% Wellfield Maintenance
Hot_sink_WellFieldMaintenance = 0.015 * (Total_Hot_sink_Drilling_Cost + Hot_sink_FlowLineCost); % 1.5% of Wellfield cost 

% Pump Maintenance
Hot_sink_PumpMaintenance = Hot_sink_ProdPumping_Estimation.PumpMaintenanceCost(Step3,Step6);

% Makeup Water Cost
OilSaturation = 0; % This defaults to an aquifer. For an oil reservoir, the user should input the avg. oil saturation
NumberProductionWells = Nsink_well; % The user should change this based on number of production wells
ProductionRateperWell = Pflowrate; % in kg/s. The user should change this based plant design
MakeupWaterUnitCost = 0.65; % $ per bbl or 5818.50 per arce-ft.
% (https://waterstandard.com/the-role-of-produced-water-treatment-in-shale-plays/).
% $300 per acre-ft in GETEM
SubsurfaceWaterLoss = OilSaturation + 0.001;
Hot_sink_MakeupWaterSubsurface = MakeupWaterUnitCost * NumberProductionWells * ...
    (ProductionRateperWell * 18.0917 * 34.2857 * 365) * SubsurfaceWaterLoss; % in $ per year

% =============================
% Total Subsurface Capital Cost
% =============================
SubsurfaceCapitalCost = Total_Exploration_Cost + FieldDevPlantPermitting + ...
    Total_Hot_source_Drilling_Cost + Hot_source_ProdPumping_Cost_Duty(2) + ...
    Hot_source_InjPumping_Cost_Duty(2) + Hot_source_FlowLineCost + ...
    Total_Hot_sink_Drilling_Cost + Hot_sink_ProdPumping_Cost_Duty(2) + ...
    Hot_sink_InjPumping_Cost_Duty(2) + Hot_sink_FlowLineCost;

% Property Tax and Insurance
PropertyTaxRate = 0.0075; % 0.75% rate from GETEM
AnnualTaxandInsurance = PropertyTaxRate * SubsurfaceCapitalCost;


% =============================
% Total Subsurface O&M Cost
% =========================
SubsurfaceOandMCost = Hot_source_WellFieldMaintenance + ...
    Hot_source_PumpMaintenance + Hot_source_MakeupWaterSubsurface + ...
    Hot_sink_WellFieldMaintenance + ...
    Hot_sink_PumpMaintenance + Hot_sink_MakeupWaterSubsurface + ...
    AnnualTaxandInsurance;

% Energy flows
charging_hours = size(HP.Win(HP.Win((nY-1)*8760+1:nY*8760)>0),1);
discharging_hours = size(HE.Wout(HE.Wout((nY-1)*8760+1:nY*8760)>0),1);

hot_charge_production_pump = charging_hours * Hot_source_ProdPumping_Cost_Duty(1) / 1e6 ;
hot_charge_injection_pump = charging_hours * Hot_sink_InjPumping_Cost_Duty(1) / 1e6;
charge_air_fan = charging_hours * HP.fan0 * HP.Win0 / 1e3 ;

hot_discharge_production_pump = discharging_hours * Hot_sink_ProdPumping_Cost_Duty(1) / 1e6;
hot_discharge_injection_pump = discharging_hours * Hot_source_InjPumping_Cost_Duty(1) / 1e6;
discharge_air_fan = discharging_hours * HE.fan0 * HE.Wout0 / 1e3 ;


%% Calculate LCOH
econ.subsurface_capital_cost = SubsurfaceCapitalCost ;
econ.OnM_subsurface = SubsurfaceOandMCost ;

econ.surface_capital_cost = HP.total_cost;
econ.OnM_surface = econ.OnM * econ.surface_capital_cost ;

econ.Ein = HP.Win_tot + hot_charge_injection_pump + hot_charge_production_pump + charge_air_fan + hot_discharge_injection_pump + hot_discharge_production_pump;
econ.Qout = HE.Qin_tot;

econ = calc_fcr(econ) ;
econ = calc_revenue(econ,HP.Win((nY-1)*8760+1:nY*8760),HE.Wout((nY-1)*8760+1:nY*8760));
if strcmp(opmode,'hour'); econ.charge_cost=0; end;
econ.charge_cost=0;
econ = calc_levelized_cost(econ,'H');


%% Calculate LCOS (electricity)
econ.subsurface_capital_cost = SubsurfaceCapitalCost ;
econ.OnM_subsurface = SubsurfaceOandMCost ;

econ.surface_capital_cost = HE.total_cost + HP.total_cost;
econ.OnM_surface = econ.OnM * econ.surface_capital_cost ;

econ.Ein = HP.Win_tot + hot_charge_injection_pump + hot_charge_production_pump + charge_air_fan;
econ.Eout = HE.Wout_tot - hot_discharge_injection_pump - hot_discharge_production_pump - discharge_air_fan;
CB.RTeff_real = econ.Eout / econ.Ein ;

econ = calc_fcr(econ) ;
econ = calc_revenue(econ,HP.Win((nY-1)*8760+1:nY*8760),HE.Wout((nY-1)*8760+1:nY*8760));
if strcmp(opmode,'hour'); econ.charge_cost=0; end;
econ.charge_cost=0;
econ = calc_levelized_cost(econ,'S');

% Group capital costs
Ccap = [Total_Exploration_Cost FieldDevPlantPermitting  ...
    Total_Hot_source_Drilling_Cost Hot_source_ProdPumping_Cost_Duty(2) ...
    Hot_source_InjPumping_Cost_Duty(2) Hot_source_FlowLineCost ...
    Total_Hot_sink_Drilling_Cost Hot_sink_ProdPumping_Cost_Duty(2) ...
    Hot_sink_InjPumping_Cost_Duty(2) Hot_sink_FlowLineCost ...
    HP.total_cost HE.total_cost]/1e6;
LCOS_mat = [Ccap*econ.FCR*1e6 econ.OnM_subsurface econ.OnM_surface econ.elec_cost]/econ.Eout/1e6 ;

geoTES_LCOS = (sum(Ccap(1:10))*econ.FCR*1e6 + econ.OnM_subsurface)/(econ.Eout)/1e6 ; 
geoTES_LCOS_ITC = (sum(Ccap(1:10))*econ.FCR*1e6*(1-econ.ITC) + econ.OnM_subsurface)/(econ.Eout)/1e6 ; % Note, total electricity output is scaled by quantity of heat delivered from GeoTES to Heat engine.

if write_out
%% PRINT OUT RESULTS
% Print and plot out technical results
fprintf(1,'\nPOWER OUTPUTS\n\n');
fprintf(1,"Heat pump power input                     = %6.2f MW-e\n",HP.Win0);
fprintf(1,"Heat pump heat output                     = %6.2f MW-th\n",HP.Qout0);
fprintf(1,"Heat pump heat input                      = %6.2f MW-th\n",HP.Qin0);
fprintf(1,"Average heat pump power input             = %6.2f MW-e\n\n",mean(HP.Win(HP.Win((nY-1)*8760+1:nY*8760)>0)));

fprintf(1,"Heat engine power output                  = %6.2f MW-e\n",HE.Wout0);
fprintf(1,"Heat engine heat input                    = %6.2f MW-th\n",HE.Qin0);
fprintf(1,"Heat engine heat output                   = %6.2f MW-th\n",HE.Qout0);
fprintf(1,"Average power cycle output                = %6.2f MW-e\n\n",mean(HE.Wout(HE.Wout((nY-1)*8760+1:nY*8760)>0)));

fprintf(1,"Max. thermal power into hot storage       = %6.2f MW-th\n",max(gHTES.power((nY-1)*8760+1:nY*8760)));
fprintf(1,"Max. thermal power out of hot storage     = %6.2f MW-th\n",-min(gHTES.power((nY-1)*8760+1:nY*8760)));

fprintf(1,"Hot production pump power                 = %6.2f MW-e\n",Hot_source_ProdPumping_Cost_Duty(1)/1e3);
fprintf(1,"Hot injection pump power                  = %6.2f MW-e\n",Hot_sink_InjPumping_Cost_Duty(1)/1e3);
fprintf(1,"Charge fan power                          = %6.2f MW-e\n",HP.fan0 * HP.Win0);
fprintf(1,"Discharge fan power                       = %6.2f MW-e\n",HE.fan0 * HE.Wout0);


fprintf(1,'\nANNUAL ENERGY OUTPUTS\n\n');
fprintf(1,"Number of charging hours                  = %6.2f h\n",charging_hours);
fprintf(1,"Number of discharging hours               = %6.2f h\n",discharging_hours);
fprintf(1,"Electricity input to heat pump            = %6.2f GWh-e\n",HP.Win_tot);
fprintf(1,"Electricity output of heat engine         = %6.2f GWh-e\n\n",HE.Wout_tot);

fprintf(1,"Heat delivered to hot storage             = %6.2f GWh-th\n",gHTES.energy_in_tot);
fprintf(1,"Heat extracted from hot storage           = %6.2f GWh-th\n\n",gHTES.energy_out_tot);

fprintf(1,"Charge Hot production pump consumption           = %6.2f GWh-e\n",hot_charge_production_pump);
fprintf(1,"Charge Hot injection pump consumption            = %6.2f GWh-e\n",hot_charge_injection_pump);
fprintf(1,"Charge air fan consumption                       = %6.2f GWh-e\n\n",charge_air_fan);

fprintf(1,"Discharge Hot production pump consumption        = %6.2f GWh-e\n",hot_discharge_production_pump);
fprintf(1,"Discharge Hot injection pump consumption         = %6.2f GWh-e\n",hot_discharge_injection_pump);
fprintf(1,"Disharge air fan consumption                     = %6.2f GWh-e\n\n",discharge_air_fan);

fprintf(1,"Real round-trip efficiency (inc. parasitics)     = %6.2f %%\n\n",100*CB.RTeff_real);

% Print out economic results
fprintf(1,'\nSUBSURFACE COST RESULTS\n\n');
fprintf(1,"Total Exploration Cost          = %6.2f M$\n",Total_Exploration_Cost/1e6);
fprintf(1,"Permitting cost                 = %6.2f M$\n\n",FieldDevPlantPermitting/1e6);

fprintf(1,"Number of source wells          = %6i\n",Nsource_well);
fprintf(1,"Total source Drilling Cost      = %6.2f M$\n",Total_Hot_source_Drilling_Cost/1e6);
fprintf(1,"Source production pump cost     = %6.2f M$\n",Hot_source_ProdPumping_Cost_Duty(2)/1e6);
fprintf(1,"Source injection pump cost      = %6.2f M$\n",Hot_source_InjPumping_Cost_Duty(2)/1e6);
fprintf(1,"Source flow line cost           = %6.2f M$\n\n",Hot_source_FlowLineCost/1e6);

fprintf(1,"Number of sink wells            = %6i\n",Nsink_well);
fprintf(1,"Total sink Drilling Cost        = %6.2f M$\n",Total_Hot_sink_Drilling_Cost/1e6);
fprintf(1,"Sink production pump cost       = %6.2f M$\n",Hot_sink_ProdPumping_Cost_Duty(2)/1e6);
fprintf(1,"Sink injection pump cost        = %6.2f M$\n",Hot_sink_InjPumping_Cost_Duty(2)/1e6);
fprintf(1,"Sink flow line cost             = %6.2f M$\n\n",Hot_sink_FlowLineCost/1e6);

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
fprintf(1,'LCOS (ITC)                      = %6.2f $/kWh-e\n',econ.LCOS_ITC)
fprintf(1,'LCOH                            = %6.3f $/kWh-th\n',econ.LCOH)
fprintf(1,'LCOH (ITC)                      = %6.3f $/kWh-th\n\n',econ.LCOH_ITC)
fprintf(1,'Charging electricity cost       = %6.2f M$\n',econ.charge_cost/1e6)
fprintf(1,'Discharging electricity revenue = %6.2f M$\n',econ.discharge_revenue/1e6)
fprintf(1,'Net revenue                     = %6.2f M$\n\n',econ.net_revenue/1e6)

%% Plot out some economic results
% Save figure formats
formats = {'fig','svg'};

% Capital cost
xlab = {'Exploration','Permitting',...
    'Source drilling','Source production pumps',...
    'Source injection pump','Source flow line',...
    'Sink drilling','Sink production pumps',...
    'Sink injection pump','Sink flow line',...
    'Heat pump','Heat engine'};

figure(1)
bar(Ccap);
set(gca, 'XTick', 1:12, 'XTickLabel', xlab, 'TickLabelInterpreter', 'latex')
ylabel('Capital cost, M\$');
if save_figs == 1; save_fig(1, './Outputs/capital_cost',formats); end


% Contribution to LCOE

xlab = {'Exploration','Permitting',...
    'Source drilling','Source production pumps',...
    'Source injection pump','Source flow line',...
    'Sink drilling','Sink production pumps',...
    'Sink injection pump','Sink flow line',...
    'Heat pump','Heat engine',...
    'Subsurface O\&M','Surface O\&M','Charging Electricity'};


figure(2)
bar(LCOS_mat);
set(gca, 'XTick', 1:15, 'XTickLabel', xlab, 'TickLabelInterpreter', 'latex')
ylabel('LCOS, \$/kWh-e');
if save_figs == 1; save_fig(2, './Outputs/LCOS',formats); end
%}
%% Plot technical results

figure(4)
n=(nY-1)*8760+1:nY*8760;
plot(gHTES.energy(n)/1000);
xlim([0 8760]);
pbaspect([3 1 1])
xlabel('Hour of the year');
ylabel('Energy in hot storage, GWh-th')
if save_figs == 1; save_fig(4, './Outputs/Hot_geoTES_SOC',formats); end


figure(5)
n=24*27+(nY-1)*8760+1:24*31+(nY-1)*8760+1;
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
n=24*day(datetime(2022,6,1),'dayofyear')+(nY-1)*8760+1:24*day(datetime(2022,6,4),'dayofyear')+(nY-1)*8760+1;
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
if save_figs == 1; save_fig(7, './Outputs/January_prices',formats); end



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
if save_figs == 1; save_fig(8, './Outputs/June_proces',formats); end


figure(9)
n=1:8760;
plot(econ.elec_price_hourly(n));
xlim([0 8760]);
pbaspect([3 1 1])
xlabel('Hour of the year');
ylabel('Electricity price, \$/MWh')
if save_figs == 1; save_fig(9, './Outputs/electricity_prices',formats); end

% Analyze electrcity price
price_sort = econ.elec_price_hourly(econ.elec_price_hourly(1:8760)<1000);
price_sort = sort(price_sort);
nP = 6000;
low_price = zeros(nP,1);
high_price = zeros(nP,1);
for i = 1:nP
    low_price(i) = mean(price_sort(1:i));
    high_price(i) = mean(price_sort(end-i:end));
end

figure(10)
plot(low_price);
hold on;
plot(low_price/CB.RTeff_real);
plot(high_price)
hold off
xlim([0 nP]);
xlabel('Number of hours');
ylabel('Average price for x hours, \$/MWh')
legend('Charging price', ...
    'Required discharging price','Discharging price', ...
    'Location','northwest', ...
    'Orientation','vertical',...
    'FontSize',10);
if save_figs == 1; save_fig(10, './Outputs/average_prices',formats); end

%}
end
results = [Ccap';LCOS_mat'] ;

short_results = [econ.LCOS;econ.LCOS_ITC;geoTES_LCOS;geoTES_LCOS_ITC;econ.LCOH;econ.LCOH_ITC;econ.subsurface_capital_cost/(gHTES.energy_capacity*1e6);econ.total_capital_cost;econ.OnM_total] ;

% Parasitics analysis
charge_hot_pump = Hot_source_ProdPumping_Cost_Duty(1)/1e3 + Hot_sink_InjPumping_Cost_Duty(1)/1e3 ;
charge_hot_wells = gHTES.charge_prod_Nwell + gHTES.charge_inj_Nwell ;

discharge_hot_wells = gHTES.discharge_prod_Nwell + gHTES.discharge_inj_Nwell ;
discharge_hot_pump = Hot_sink_ProdPumping_Cost_Duty(1)/1e3 + Hot_source_InjPumping_Cost_Duty(1)/1e3 ;

rte = 100*(HE.Wout0 - HE.fan0*HE.Wout0 - Hot_sink_ProdPumping_Cost_Duty(1)/1e3 - Hot_source_InjPumping_Cost_Duty(1)/1e3)/ (HP.Win0 + HP.fan0 * HP.Win0 + Hot_source_ProdPumping_Cost_Duty(1)/1e3 + Hot_sink_InjPumping_Cost_Duty(1)/1e3) ;

GeoTES_output = [input1 input2 ...
                charge_hot_pump charge_hot_wells  ...
                discharge_hot_pump discharge_hot_wells ...
                HE.fan0*HE.Wout0 HP.fan0 * HP.Win0 rte econ.LCOS econ.LCOS_ITC econ.LCOH econ.LCOH_ITC ...
                econ.total_capital_cost econ.OnM_total] ;

end
