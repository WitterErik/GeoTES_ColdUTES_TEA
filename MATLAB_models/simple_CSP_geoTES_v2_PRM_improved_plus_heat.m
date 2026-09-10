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
%   -   Include generator efficiency in heat engine efficiency calculation
%   -   Add in condenser parasitic load
%
% Version PRM
%   -   Inputs have been modified to reflect PRM's demonstration system
%   -   Solar field uses oil between 100-250 C


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
save_figs = 0; % 1 to save figures, 0 to not save

if ~isfolder('Outputs')
    mkdir('./Outputs');
else
    delete('./Outputs/*')
end

% System level inputs
location = 'Antelope Hills CA' ;

% Operating hours
phase1 = [1 (31+28+31)*24+1];
phase2 = [(31+28+31)*24+1 (31+28+31+30+31+30+31+31+30)*24+1];
phase3 = [(31+28+31+30+31+30+31+31+30)*24+1 (31+28+31+30+31+30+31+31+30+31+30+31)*24+1];

op_hour1 = [17:24]; % List of hours of operation
op_hour2 = [17:23]; % List of hours of operation
op_hour3 = [17:23]; % List of hours of operation

nY = 2; % Number of years to run the simulation for

% Thermal load
Qload = 200; % MW-th
Qload_hourly = zeros(8760*nY,1);

%% CSP inputs
mirror_type = 'Parabolic trough';
nominal_DNI = 950 ; % W/m2
solar_multiple = 2.5;%1.25;%1.75;%5.2;
CSP_Tmax = 250 ; % Max temperature, C
CSP_Tmin = 100 ; % Min temperature, C
CSP_land_mult = 1.1 ;

CSP_cost.mirror = 105 ; % mirror cost, $/m2
CSP_cost.land   = 20 ; % site improvements, $/m2
CSP_cost.HX     = 250 ; % Heat exchanger to high-temp TES, $/kWh-th

% Set up CSP class
CSP = solar_class(location, mirror_type, nominal_DNI, solar_multiple, CSP_Tmax, CSP_Tmin, CSP_land_mult, CSP_cost,nY);

%% Low-temperature power cycle inputs
LTPC_type = 'HE'; % Type of power cycle [heat engine]
LTPC_design.Wout  = 199 ;% Power output, MW-e
LTPC_design.T0    = 25; % Design ambient temperature, C
LTPC_design.TIT   = 250 ; % Turbine inlet temperature, C. Calculate efficiency and Qin from this.
LTPC_design.fan   = 0.1;

LTPC_foff = 'data\example_off_design.xlsx' ; % File location specifying off-design behaviour

LTPC_cost.power_block = 750 ; % power block, $/kW-e
LTPC_cost.HX = 250 ; % heat exchanger between TES and power block, $/kWh-th

% Set up high-temp power cycle class
LTPC = thermo_cycle_class(LTPC_type,LTPC_design,LTPC_foff,LTPC_cost, nY);

%% Low-temperature thermal storage (geoTES) inputs
reversible_wells = false ; % Are charge production wells used as discharge injection wells (and charge injection wells used as discharge production wells)
gTES_recovery = 0.95 ; % Fraction of input thermal energy that is recovered
gTES_Tinit = 50 ; % Initial reservoir temperature, C
gTES_flowrate.P = 40;%5.6 ; % Flow rate per production well, L/s
gTES_flowrate.I = 80;%11 ; % Flow rate per injection well, L/s
gTES_Qmax = 920.63+3*Qload;%69.39;%920.63;%692;%46 ; % Maximum charging power input, MWh-th
gTES_props.rho = 2000 ; % Rock density, kg/3
gTES_props.cp = 800 ; % Rock heat capacity, J/kg.K
gTES_props.void = 0.32 ; % Porosity
gTES_props.depth = 500 ; % Well depth, m
gTES_props.thickness = 100; % Production thickness,m
gTES_fluid = 'water';
gTES_mode = "continuous"; % Three operation modes "separate", "continuous", "push-pull"

% Set up geo-TES class
gTES = geoTES_class(gTES_recovery,gTES_Tinit,gTES_flowrate,gTES_Qmax,gTES_props,gTES_fluid,gTES_mode, nY) ;

%% Financial inputs
finance.lifetime    = 50 ;      % Lifetime
finance.elec_price  = 0.05 ;      % Electricity price - dollars per kWhe. Lazard uses 0.033, ARPA-E uses 0.025. 0.06 is a value that I've used in the past.
finance.inflation   = 0.025;      % Inflation
finance.irr         = 0.10 ;      % Internal Rate of Return
finance.debt_frac   = 0.60 ;      % Project debt fraction - SAM is 0.60
finance.debt_IR     = 0.08 ;      % Debt interest rate
finance.tax_rate    = 0.28 ;      % Tax rate
finance.deprec      = [0.20 0.32 0.20 0.14 0.14]  ; % Depreciation[0.20 0.32 0.192 0.1152 0.1152 0.0576] ;
finance.annual_cost = [1.0 0.0 0.]; % Capital cost incurred in which years [0.80 0.10 0.10] ;
finance.construc_IR = 0.0 ;         % Construction interest rate <- new assumption 25/1/17 to make CFF =1. SAM value -> % 0.08 ;
finance.OnM         = 0.015 ;      % Operations and maintenance cost as a fraction of total capital cost - see Georgiou et al 2018
finance.ITC         = 0.4 ;         % Investment tax credit

econ = economics_class(finance);

%% Let's do some calculations!!!


% Specify some fluid properties from the production and injection wells and
% calculate the remaining properties
% Charging
gTES.charge_production.T = gTES.Tinit ; % Temperature of produced fluid during charge, C
gTES.charge_production.p = 40 ; % Pressure of produced fluid during charge, bar
gTES.charge_production = calc_fluid_props(gTES.charge_production,'pT');

gTES.charge_injection.T = LTPC.Tmax ;
gTES.charge_injection.q = 0 ;
gTES.charge_injection.p = 40 ; 
gTES.charge_injection = calc_fluid_props(gTES.charge_injection,'pT');

% Discharging
gTES.discharge_production.T = LTPC.Tmax ; % Temperature of produced fluid during charge, C
gTES.discharge_production.q = 0 ; % Pressure of produced fluid during charge, bar
gTES.discharge_production = calc_fluid_props(gTES.discharge_production,'qT');

gTES.discharge_injection.T = gTES.Tinit ;
gTES.discharge_injection.p = 40 ;
gTES.discharge_injection = calc_fluid_props(gTES.discharge_injection,'pT');


% Calculate hourly energy flows in CSP system for the year
out = call_SAM(CSP,LTPC) ; % This function needs to be incorporated to CSP class
CSP.mirror_aperture = out.mirror_area ;
CSP.land_area = out.land_area ;
CSP.nominal_eff = out.nominal_eff ;
CSP.annual_eff = out.annual_eff ;
CSP.DNI = out.DNI ;

% Calculate hourly energy flows for the full system over the course of the
% year. Move this to the dispatch class at some point.
dT = 1; % Timestep = 1 hour

% First time-step of the year
CSP.power = repmat(out.field_thermal_power,nY,1) ; % Simulate nY years
for i = 1:nY*8760
    if CSP.power(i) < 0
        CSP.power(i) = 0;
    end
end
LTPC.Tamb = repmat(out.Tamb,nY,1);

LTPC.Qin(1) = CSP.power(1) ;
LTPC = interpolate_off_design(LTPC,1);
hour  = 2; % hour of the day
houry = 2; % hour of the year
% Remaining time-steps
for i = 2:nY*8760
    
    gTES.energy(i) = gTES.energy(i-1);
    % Determine phase
    if and(houry>=phase1(1),houry<phase1(2))
        operate = any(hour==op_hour1);
    elseif and(houry>=phase2(1),houry<phase2(2))
        operate = any(hour==op_hour2);
    elseif and(houry>=phase3(1),houry<phase3(2))
        operate = any(hour==op_hour3);
    end


    % Dispatch power plant if within operational hours
    if operate
        % If solar heat exceeds design power input to low-temp power cycle
        if CSP.power(i) > LTPC.Qin0 + Qload
            % Then send design heat to power cycle and calculate power output
            LTPC.Qin(i) = LTPC.Qin0 ;
            LTPC = interpolate_off_design(LTPC,i);

            % Design heat to thermal load
            Qload_hourly(i) = Qload ;

            % Send remaining heat to geo-TES if the wells have capacity
            dP = CSP.power(i) - LTPC.Qin0 - Qload ;

            if dP < gTES.Qmax
                gTES.power(i) = dP ;
            else
                gTES.power(i) = gTES.Qmax ;
                CSP.dumped(i) = dP - gTES.Qmax ;
            end
            gTES.energy(i) = gTES.energy(i-1) + gTES.power(i) * dT * gTES.recovery ;

            % If solar heat is less than design point then dispatch geoTES through
            % the LTPC
        else
            % Required heat
            dP = LTPC.Qin0 + Qload - CSP.power(i) ;
            if dP * dT < gTES.energy(i-1)
                gTES.power(i) = -dP ;
                gTES.energy(i) = gTES.energy(i-1) + gTES.power(i) ;
                LTPC.Qin(i) = LTPC.Qin0 ;
                LTPC = interpolate_off_design(LTPC,i);
                Qload_hourly(i) = Qload ; 
            else
                gTES.power(i) = -gTES.energy(i-1) / dT ;
                gTES.energy(i) = gTES.energy(i-1) + gTES.power(i) ;

                % High-temp power cycle performance
                if CSP.power(i) + gTES.power(i) > LTPC.Qin0
                    LTPC.Qin(i) = LTPC.Qin0 ;
                    LTPC = interpolate_off_design(LTPC,i);
                    Qload_hourly(i) = CSP.power(i) + gTES.power(i) - LTPC.Qin0;
                else
                    LTPC.Qin(i) = CSP.power(i) - gTES.power(i) ;
                    LTPC = interpolate_off_design(LTPC,i);
                    Qload_hourly(i) = 0 ;
                end
            end

        end
    
    % Otherwise send heat only to thermal load
    else
        if CSP.power(i) > Qload
            % Design heat to thermal load
            Qload_hourly(i) = Qload ;

            % Send remaining heat to geo-TES if the wells have capacity
            dP = CSP.power(i) - Qload ;

            if dP < gTES.Qmax
                gTES.power(i) = dP ;
            else
                gTES.power(i) = gTES.Qmax ;
                CSP.dumped(i) = dP - gTES.Qmax ;
            end
            gTES.energy(i) = gTES.energy(i-1) + gTES.power(i) * dT * gTES.recovery ;

            % If solar heat is less than design point then dispatch geoTES through
            % the LTPC
        else
            % Required heat
            dP = Qload - CSP.power(i) ;
            if dP * dT < gTES.energy(i-1)
                gTES.power(i) = -dP ;
                gTES.energy(i) = gTES.energy(i-1) + gTES.power(i) ;
                Qload_hourly(i) = Qload ; 
            else
                gTES.power(i) = -gTES.energy(i-1) / dT ;
                gTES.energy(i) = gTES.energy(i-1) + gTES.power(i) ;

                Qload_hourly(i) = CSP.power(i) - gTES.power(i) ;
            end

        end

    end

    hour = hour + 1;
    houry = houry + 1;
    if hour == 25
        hour = 1;
    end
    if houry == 8761 
        houry = 1;
    end
end

% Calculate size of geoTES and flow rates in wells
gTES = geoTES_size(gTES) ;
gTES = geoTES_well_flows(gTES) ;

% Annual results for the CSP, power cycle, and storage
CSP  = CSP_annual_energy(CSP);
LTPC = PC_annual_energy(LTPC);
gTES = geoTES_annual_energy(gTES) ;

% Calculate sub-system costs
CSP  = calc_CSP_cost(CSP,LTPC) ;
LTPC = calc_PC_cost(LTPC) ;

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
if gTES.mode == "separate"

    % Drilling cost and completions
    % Charge production cost
    Charge_Drilling_Cost_prod = DrillingCostUpdated(gTES.charge_prod_Nwell,0,gTES.depth,gTES.thickness,"Small",1,1.5,"Deviated","Liner");
    Charge_Well_Cost_prod = Charge_Drilling_Cost_prod.WellCost();
    Total_Charge_Drilling_Cost_prod = Charge_Drilling_Cost_prod.TotalDC(Charge_Well_Cost_prod);

    % Charge injection cost
    Charge_Drilling_Cost_inj = DrillingCostUpdated(0,gTES.charge_inj_Nwell,gTES.depth,gTES.thickness,"Small",1,1.5,"Deviated","Openhole");
    Charge_Well_Cost_inj = Charge_Drilling_Cost_inj.WellCost();
    Total_Charge_Drilling_Cost_inj = Charge_Drilling_Cost_inj.TotalDC(Charge_Well_Cost_inj);

    % Production pumping duty and cost
    ResTemp = gTES.Tinit ; % Is it better to use maximum formation temperature, or minimum? Celcius
    Pflowrate = gTES.flowrate_per_well_prod * gTES.charge_production.rho / 1000 ; % Flow rate. Units? Convert from L/s to kg/s
    Charge_ProdPumping_Estimation = ProductionPumpingCost(ResTemp,Pflowrate,gTES.charge_prod_Nwell,6370,gTES.depth,gTES.thickness,"Small","Lineshaft","Liner",1.553);
    Step1 = Charge_ProdPumping_Estimation.HeadProdTop();
    Step2 = Charge_ProdPumping_Estimation.HeadSunction(Step1.Prodtop);
    Step3 = Charge_ProdPumping_Estimation.Sunctiondepth(Step2);
    Step4 = Charge_ProdPumping_Estimation.CasingFriction(Step3,Step1.Prodtop);
    Step5 = Charge_ProdPumping_Estimation.Pumppower(Step3,Step4);
    Step6 = Charge_ProdPumping_Estimation.Pumpcost(Step5,Step3);
    Charge_ProdPumping_Cost_Duty = Charge_ProdPumping_Estimation.TotalPumpDutyCost(Step5,Step6);

    % Injection pumping cost
    InjTemp = LTPC.Tmax ; % Which temperature to use?
    Iflowrate = gTES.flowrate_per_well_inj * gTES.charge_injection.rho / 1000 ; % Flow rate
    PressureThermalSource = gTES.charge_injection.p * 14.5038; % Thermal source pressure, in psi?
    Charge_InjPumping_Estimation = InjectionPumpingCost(ResTemp,InjTemp,Iflowrate,Pflowrate,PressureThermalSource,gTES.charge_inj_Nwell,7645,gTES.depth,gTES.thickness,"Small","Openhole",1.533,"Charge");
    Step7 = Charge_InjPumping_Estimation.HeadSunction();
    Step8 = Charge_InjPumping_Estimation.HeadInjection(Step7);
    Step9 = Charge_InjPumping_Estimation.Pumppower(Step8);
    Step10 = Charge_InjPumping_Estimation.Pumpcost(Step9);
    Charge_InjPumping_Cost_Duty = Charge_InjPumping_Estimation.TotalPumpDutyCost(Step9,Step10);

    % Flow line cost. This assumes one pad per well.ACTION: Will include estimation
    % for multi-well pads after discussion with PRM and Earthbridge.
    LengthofFlowline = 300; % in meters per well (GETEM assumption); % Reduced to 300m as an estimate for having multiple wells on a pad. Plus PRM 7-spot has area of 213 acres which has a radius of 600 m.
    PipingUnitCost = 256.98; % $ per ft (in 2022 dollars)
    TotalNumberofWells = gTES.charge_prod_Nwell + gTES.charge_inj_Nwell; % User-defined
    Charge_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * TotalNumberofWells;

    % Add fluid Processing bulk cost for oilfield from PRM

    % ============================
    % Charge O&M Cost Calculations
    % ============================

    % This excludes labor cost which will be determined from the plant gross
    % output
    % Wellfield Maintenance
    Charge_WellFieldMaintenance = 0.015 * (Total_Charge_Drilling_Cost_prod + Total_Charge_Drilling_Cost_inj + Charge_FlowLineCost); % 1.5% of Wellfield cost

    % Pump Maintenance
    Charge_PumpMaintenance = Charge_ProdPumping_Estimation.PumpMaintenanceCost(Step3,Step6);

    % Makeup Water Cost
    OilSaturation = 0; % This defaults to an aquifer. For an oil reservoir, the user should input the avg. oil saturation
    NumberProductionWells = gTES.charge_prod_Nwell; % The user should change this based on number of production wells
    ProductionRateperWell = Pflowrate; % in kg/s. The user should change this based plant design
    MakeupWaterUnitCost = 0.65; % $ per bbl or 5818.50 per arce-ft.
    % (https://waterstandard.com/the-role-of-produced-water-treatment-in-shale-plays/).
    % $300 per acre-ft in GETEM
    SubsurfaceWaterLoss = OilSaturation + 0.001;
    Charge_MakeupWaterSubsurface = MakeupWaterUnitCost * NumberProductionWells * ...
        (ProductionRateperWell * 18.0917 * 34.2857 * 365) * SubsurfaceWaterLoss; % in $ per year


elseif gTES.mode == "continuous"

    % Drilling cost and completions
    % Charge production cost
    Total_Charge_Drilling_Cost_prod = 0.0;

    % Charge injection cost
    Total_Charge_Drilling_Cost_inj = 0.0;

    % Production pumping duty and cost
    Charge_ProdPumping_Cost_Duty = [0 0];

    % Injection pumping cost
    Charge_InjPumping_Cost_Duty = [0 0];

    % Flow line cost. This assumes one pad per well.
    Charge_FlowLineCost = 0;

    % ============================
    % Charge O&M Cost Calculations
    % ============================
    % Wellfield Maintenance
    Charge_WellFieldMaintenance = 0.0;

    % Pump Maintenance
    Charge_PumpMaintenance = 0;

    % Makeup Water Cost
    Charge_MakeupWaterSubsurface = 0.0;
        

end

% =========================================
% Discharge Well Capital Cost Calculations
% =========================================

% Drilling cost and completions
% Discharge production drilling cost
Discharge_Drilling_Cost_prod = DrillingCostUpdated(gTES.discharge_prod_Nwell,0,gTES.depth,gTES.thickness,"Small",1,1.5,"Deviated","Liner");
Discharge_Well_Cost_prod = Discharge_Drilling_Cost_prod.WellCost();
if reversible_wells == true
    Total_Discharge_Drilling_Cost_prod = 0;
else
    Total_Discharge_Drilling_Cost_prod = Discharge_Drilling_Cost_prod.TotalDC(Discharge_Well_Cost_prod);
end

% Discharge injection drilling cost
Discharge_Drilling_Cost_inj = DrillingCostUpdated(0,gTES.discharge_inj_Nwell,gTES.depth,gTES.thickness,"Small",1,1.5,"Deviated","Openhole");
Discharge_Well_Cost_inj = Discharge_Drilling_Cost_inj.WellCost();
if reversible_wells == true
    Total_Discharge_Drilling_Cost_inj = 0;
else
    Total_Discharge_Drilling_Cost_inj = Discharge_Drilling_Cost_inj.TotalDC(Discharge_Well_Cost_inj);
end


% Production pumping duty and cost
ResTemp = gTES.Tinit;%LTPC.Tmax ; % Really not sure what to put as the reservoir temperature
Pflowrate = gTES.flowrate_per_well_prod * gTES.discharge_production.rho / 1000 ; % Flow rate. Units? Convert from L/s to kg/s
Discharge_ProdPumping_Estimation = ProductionPumpingCost(ResTemp,Pflowrate,gTES.discharge_prod_Nwell,6370,gTES.depth,gTES.thickness,"Small","Lineshaft","Liner",1.553);
Step1 = Discharge_ProdPumping_Estimation.HeadProdTop();
Step2 = Discharge_ProdPumping_Estimation.HeadSunction(Step1.Prodtop);
Step3 = Discharge_ProdPumping_Estimation.Sunctiondepth(Step2);
Step4 = Discharge_ProdPumping_Estimation.CasingFriction(Step3,Step1.Prodtop);
Step5 = Discharge_ProdPumping_Estimation.Pumppower(Step3,Step4);
Step6 = Discharge_ProdPumping_Estimation.Pumpcost(Step5,Step3);
Discharge_ProdPumping_Cost_Duty = Discharge_ProdPumping_Estimation.TotalPumpDutyCost(Step5,Step6);

% Injection pumping cost
InjTemp = gTES.Tinit ; % Which temperature to use?
Iflowrate = gTES.flowrate_per_well_inj * gTES.discharge_injection.rho / 1000 ; % Flow rate
PressureThermalSource = gTES.discharge_injection.p * 14.5038; % Thermal source pressure, in psi?
Discharge_InjPumping_Estimation = InjectionPumpingCost(ResTemp,InjTemp,Iflowrate,Pflowrate,PressureThermalSource,gTES.discharge_inj_Nwell,7645,gTES.depth,gTES.thickness,"Small","Openhole",1.533,"Discharge");
Step7 = Discharge_InjPumping_Estimation.HeadSunction();
Step8 = Discharge_InjPumping_Estimation.HeadInjection(Step7);
Step9 = Discharge_InjPumping_Estimation.Pumppower(Step8);
Step10 = Discharge_InjPumping_Estimation.Pumpcost(Step9);
Discharge_InjPumping_Cost_Duty = Discharge_InjPumping_Estimation.TotalPumpDutyCost(Step9,Step10);
if reversible_wells == true
    Discharge_InjPumping_Cost_Duty = [0,0];
end

% Flow line cost. This assumes one pad per well. Will include estimation
% for multi-well pads after discussion with PRM and Earthbridge.
LengthofFlowline = 300; % in meters per well (GETEM assumption) % Reduced to 300m as an estimate for having multiple wells on a pad. Plus PRM 7-spot has area of 213 acres which has a radius of 600 m.
PipingUnitCost = 256.98; % $ per ft (in 2022 dollars)
TotalNumberofWells = gTES.discharge_prod_Nwell + gTES.discharge_inj_Nwell; % User-defined
Discharge_FlowLineCost = LengthofFlowline * 3.28084 * PipingUnitCost * TotalNumberofWells;
if reversible_wells == true
    Discharge_FlowLineCost = 0;
end

% Add fluid Processing bulk cost for oilfield from PRM

% ================================
% Discharge O&M Cost Calculations
% ================================

% This excludes labor cost which will be determined from the plant gross
% output
% Wellfield Maintenance
Discharge_WellFieldMaintenance = 0.015 * (Total_Discharge_Drilling_Cost_prod + Total_Discharge_Drilling_Cost_inj + Discharge_FlowLineCost); % 1.5% of Wellfield cost 

% Pump Maintenance
Discharge_PumpMaintenance = Discharge_ProdPumping_Estimation.PumpMaintenanceCost(Step3,Step6);

% Makeup Water Cost
OilSaturation = 0; % This defaults to an aquifer. For an oil reservoir, the user should input the avg. oil saturation
NumberProductionWells = gTES.discharge_prod_Nwell; % The user should change this based on number of production wells
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
    Total_Charge_Drilling_Cost_prod + Total_Charge_Drilling_Cost_inj + Total_Discharge_Drilling_Cost_prod + Total_Discharge_Drilling_Cost_inj + Charge_ProdPumping_Cost_Duty(2) + ...
    Charge_InjPumping_Cost_Duty(2) + Discharge_ProdPumping_Cost_Duty(2) + ...
    Discharge_InjPumping_Cost_Duty(2) + Charge_FlowLineCost + Discharge_FlowLineCost;

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

% Charging hours
charging_hours = size(gTES.power(gTES.power((nY-1)*8760+1:nY*8760)>0),1);
discharging_hours = size(gTES.power(gTES.power((nY-1)*8760+1:nY*8760)<0),1);

discharge_air_fan = discharging_hours * LTPC.fan0 * LTPC.Wout0 / 1e3 ; % Parasitic air cooler fan load

%Pumping energy requirements
if gTES.mode == "separate"

    Energy_charge_prod    = size(gTES.power(gTES.power((nY-1)*8760+1:nY*8760)>0),1) * Charge_ProdPumping_Cost_Duty(1)/1e6 ; % GWh-e
    Energy_charge_inj     = size(gTES.power(gTES.power((nY-1)*8760+1:nY*8760)>0),1) * Charge_InjPumping_Cost_Duty(1)/1e6 ;
    Energy_discharge_prod = size(gTES.power(gTES.power((nY-1)*8760+1:nY*8760)<0),1) * Discharge_ProdPumping_Cost_Duty(1)/1e6 ;
    Energy_discharge_inj  = size(gTES.power(gTES.power((nY-1)*8760+1:nY*8760)<0),1) * Discharge_InjPumping_Cost_Duty(1)/1e6 ;

elseif gTES.mode == "continuous"
    Energy_charge_prod    = size(gTES.power(gTES.power((nY-1)*8760+1:nY*8760)>0),1) * Discharge_ProdPumping_Cost_Duty(1)/1e6 ; % GWh-e
    Energy_charge_inj     = size(gTES.power(gTES.power((nY-1)*8760+1:nY*8760)>0),1) * Discharge_InjPumping_Cost_Duty(1)/1e6 ;
    Energy_discharge_prod = size(gTES.power(gTES.power((nY-1)*8760+1:nY*8760)<0),1) * Discharge_ProdPumping_Cost_Duty(1)/1e6 ;
    Energy_discharge_inj  = size(gTES.power(gTES.power((nY-1)*8760+1:nY*8760)<0),1) * Discharge_InjPumping_Cost_Duty(1)/1e6 ;
end

% Max. hours of discharge and if excess capacity, how many hours discharge
geoTES_max_hours = gTES.energy_capacity*1000/( LTPC.Wout0 / LTPC.eff0) ;
geoTES_max_elec = (LTPC.Wout0 - Discharge_ProdPumping_Cost_Duty(1)/1e3 - Discharge_InjPumping_Cost_Duty(1)/1e3 - LTPC.fan0*LTPC.Wout0) * geoTES_max_hours / 1e3;

geoTES_capacity_hours = gTES.net_energy * 1000/( LTPC.Wout0 /LTPC.eff0) ;
geoTES_capacity_elec = (LTPC.Wout0 - Discharge_ProdPumping_Cost_Duty(1)/1e3 - Discharge_InjPumping_Cost_Duty(1)/1e3 - LTPC.fan0*LTPC.Wout0) * geoTES_capacity_hours / 1e3;

% Calculate LCOH by considering the increase in cost compared to an
% electric only CSP-GeoTES system plus cost of heat exchanger
econ.surface_capital_cost = CSP.total_cost + LTPC.total_cost + 250*Qload*1000 - 923.49e6;%1.0845e9;%
econ.OnM_surface = econ.OnM * (CSP.total_cost + LTPC.total_cost + 250*Qload*1000) - 13.85e6;%1.6267e7;%

econ.subsurface_capital_cost = SubsurfaceCapitalCost - 95.42e6 ;%5.9792e8;%
econ.OnM_subsurface = SubsurfaceOandMCost - 2.80e6;%1.5267e7;%

econ.Ein = Energy_charge_prod + Energy_charge_inj + Energy_discharge_prod + Energy_discharge_inj - 62.5886;%77.5640;%
econ.Qout = sum(Qload_hourly((nY-1)*8760+1:nY*8760))/1e3 ;
econ = calc_fcr(econ) ;
econ = calc_levelized_cost(econ,'H');
           

%{
% Calculate LCOH if didn't use power cycle to produce electricity and
% instead dispacthed all energy as heat
econ.subsurface_capital_cost = SubsurfaceCapitalCost ;
econ.OnM_subsurface = SubsurfaceOandMCost ;

econ.surface_capital_cost = CSP.total_cost ;
econ.OnM_surface = econ.OnM * econ.surface_capital_cost ;

econ.Ein = Energy_charge_prod + Energy_charge_inj + Energy_discharge_prod + Energy_discharge_inj ;
econ.Qout = LTPC.Qin_tot ;
econ = calc_fcr(econ) ;
econ = calc_levelized_cost(econ,'H');
%}
% Calculate LCOE: generating electricity
econ.subsurface_capital_cost = SubsurfaceCapitalCost ;
econ.OnM_subsurface = SubsurfaceOandMCost ;
econ.surface_capital_cost = CSP.total_cost + LTPC.total_cost;
econ.OnM_surface = econ.OnM * econ.surface_capital_cost ;

econ.Ein = Energy_charge_prod + Energy_charge_inj ;
econ.Eout = LTPC.Wout_tot - (Energy_discharge_prod + Energy_discharge_inj) - discharge_air_fan;
econ = calc_fcr(econ) ;
econ = calc_levelized_cost(econ,'E');

% Group capital costs
Ccap = [Total_Exploration_Cost FieldDevPlantPermitting  ...
    Total_Charge_Drilling_Cost_inj+Total_Charge_Drilling_Cost_prod Charge_ProdPumping_Cost_Duty(2) ...
    Charge_InjPumping_Cost_Duty(2) Charge_FlowLineCost ...
    Total_Discharge_Drilling_Cost_prod+Total_Discharge_Drilling_Cost_inj Discharge_ProdPumping_Cost_Duty(2) ...
    Discharge_InjPumping_Cost_Duty(2) Discharge_FlowLineCost ...
    CSP.total_cost LTPC.total_cost]/1e6;
LCOE_mat = [Ccap*econ.FCR*1e6 econ.OnM_subsurface econ.OnM_surface]/econ.Eout/1e6 ;
geoTES_LCOE = (sum(Ccap(1:10))*econ.FCR*1e6 + econ.OnM_subsurface)/(econ.Eout * gTES.energy_out_tot / LTPC.Qin_tot)/1e6 ; % Note, total electricity output is scaled by quantity of heat delivered from GeoTES to Heat engine.
geoTES_LCOE_ITC = (sum(Ccap(1:10))*econ.FCR*1e6*(1-econ.ITC) + econ.OnM_subsurface)/(econ.Eout * gTES.energy_out_tot / LTPC.Qin_tot)/1e6 ; % Note, total electricity output is scaled by quantity of heat delivered from GeoTES to Heat engine.

% Capacity factor
net_elec = (LTPC.Wout_tot - (Energy_discharge_prod + Energy_discharge_inj) - discharge_air_fan) ;
cap_fac = 100 * 1000 * net_elec / (LTPC.Wout0 - Discharge_ProdPumping_Cost_Duty(1)/1e3 - Discharge_InjPumping_Cost_Duty(1)/1e3 - LTPC.fan0*LTPC.Wout0) / 8760 ;

%% PRINT OUT RESULTS
% Print and plot out technical results
fprintf(1,'\nPOWER OUTPUTS\n\n');
fprintf(1,"Maximum solar power generated             = %6.2f MW-th\n",max(CSP.power));
fprintf(1,"Power cycle power output                  = %6.2f MW-e\n",LTPC.Wout0);
fprintf(1,"Average power cycle output                = %6.2f MW-e\n",mean(LTPC.Wout(LTPC.Wout((nY-1)*8760+1:nY*8760)>0)));
fprintf(1,"Max. thermal power into subsurface        = %6.2f MW-th\n",max(gTES.power((nY-1)*8760+1:nY*8760)));
fprintf(1,"Max. thermal power out of subsurface      = %6.2f MW-th\n",-min(gTES.power((nY-1)*8760+1:nY*8760)));
fprintf(1,"Charge production pump power              = %6.2f MW-e\n",Charge_ProdPumping_Cost_Duty(1)/1e3);
fprintf(1,"Charge injection pump power               = %6.2f MW-e\n",Charge_InjPumping_Cost_Duty(1)/1e3);
fprintf(1,"Discharge production pump power           = %6.2f MW-e\n",Discharge_ProdPumping_Cost_Duty(1)/1e3);
fprintf(1,"Discharge injection pump power            = %6.2f MW-e\n",Discharge_InjPumping_Cost_Duty(1)/1e3);

fprintf(1,'\nANNUAL ENERGY OUTPUTS\n\n');
fprintf(1,"Available solar heat                      = %6.2f GWh-th\n",CSP.available_solar_heat);
fprintf(1,"Solar heat generated                      = %6.2f GWh-th\n",CSP.solar_thermal_generated);
fprintf(1,"Dumped solar heat                         = %6.2f GWh-th\n\n",CSP.total_dumped);

fprintf(1,"Heat delivered to low-temp. cycle         = %6.2f GWh-th\n",LTPC.Qin_tot);
fprintf(1,"Electricity generated by low-temp. cycle  = %6.2f GWh-e\n",LTPC.Wout_tot);
fprintf(1,"Discharge condenser fan parasitic         = %6.2f GWh-e\n\n",discharge_air_fan);

fprintf(1,"Heat delivered to thermal load            = %6.2f GWh-th\n",sum(Qload_hourly((nY-1)*8760+1:nY*8760))/1e3);
fprintf(1,"Thermal load capacity factor              = %6.2f %%\n\n",100*sum(Qload_hourly((nY-1)*8760+1:nY*8760))/(Qload*8760));

fprintf(1,"Heat delivered to geoTES                  = %6.2f GWh-th\n",gTES.energy_in_tot);
fprintf(1,"Heat extracted from geoTES                = %6.2f GWh-th\n",gTES.energy_out_tot);
fprintf(1,"Max. energy stored in geoTES              = %6.2f GWh-th\n",gTES.energy_capacity);
fprintf(1,"Max. hours of power delivery              = %6.2f h\n",geoTES_max_hours);
fprintf(1,"Approx. electricity from max. hours       = %6.2f GWh-e\n\n",geoTES_max_elec);

fprintf(1,"Net annual change in geoTES capacity      = %6.2f GWh-th\n",gTES.net_energy);
fprintf(1,"Equivalent hours of power delivery        = %6.2f h\n",geoTES_capacity_hours);
fprintf(1,"Approx. electricity from space capacity   = %6.2f GWh-e\n\n",geoTES_capacity_elec);

fprintf(1,"Charge production pump consumption        = %6.2f GWh-e\n",size(gTES.power(gTES.power((nY-1)*8760+1:nY*8760)>0),1) * Charge_ProdPumping_Cost_Duty(1)/1e6);
fprintf(1,"Charge injection pump consumption         = %6.2f GWh-e\n",size(gTES.power(gTES.power((nY-1)*8760+1:nY*8760)>0),1) * Charge_InjPumping_Cost_Duty(1)/1e6);
fprintf(1,"Discharge production pump consumption     = %6.2f GWh-e\n",size(gTES.power(gTES.power((nY-1)*8760+1:nY*8760)<0),1) * Discharge_ProdPumping_Cost_Duty(1)/1e6);
fprintf(1,"Discharge injection pump consumption      = %6.2f GWh-e\n\n",size(gTES.power(gTES.power((nY-1)*8760+1:nY*8760)<0),1) * Discharge_InjPumping_Cost_Duty(1)/1e6);

fprintf(1,"Net electricity generated                 = %6.2f GWh-e\n",net_elec);
fprintf(1,"Capacity factor                           = %6.2f %%\n\n",cap_fac);

fprintf(1,"Number of charging production wells       = %6.2f\n",gTES.charge_prod_Nwell);
fprintf(1,"Number of charging injection wells        = %6.2f\n",gTES.charge_inj_Nwell);
fprintf(1,"Number of discharging production wells    = %6.2f\n",gTES.discharge_prod_Nwell);
fprintf(1,"Number of discharging injection wells     = %6.2f\n\n",gTES.discharge_inj_Nwell);

% Print out economic results
fprintf(1,'\nSUBSURFACE COST RESULTS\n\n');
fprintf(1,"Total Exploration Cost          = %6.2f M$\n",Total_Exploration_Cost/1e6);
fprintf(1,"Permitting cost                 = %6.2f M$\n\n",FieldDevPlantPermitting/1e6);
fprintf(1,"Total Charge Drilling Cost      = %6.2f M$\n",(Total_Charge_Drilling_Cost_prod+Total_Charge_Drilling_Cost_inj)/1e6);
fprintf(1,"Charge production pump cost     = %6.2f M$\n",Charge_ProdPumping_Cost_Duty(2)/1e6);
fprintf(1,"Charge injection pump cost      = %6.2f M$\n",Charge_InjPumping_Cost_Duty(2)/1e6);
fprintf(1,"Charge flow line cost           = %6.2f M$\n\n",Charge_FlowLineCost/1e6);

fprintf(1,"Total Discharge Drilling Cost   = %6.2f M$\n",(Total_Discharge_Drilling_Cost_prod+Total_Discharge_Drilling_Cost_inj)/1e6);
fprintf(1,"Discharge production pump cost  = %6.2f M$\n",Discharge_ProdPumping_Cost_Duty(2)/1e6);
fprintf(1,"Discharge injection pump cost   = %6.2f M$\n",Discharge_InjPumping_Cost_Duty(2)/1e6);
fprintf(1,"Discharge flow line cost        = %6.2f M$\n\n",Discharge_FlowLineCost/1e6);

fprintf(1,"Subsurface Capital Cost         = %6.2f M$\n",SubsurfaceCapitalCost/1e6);
fprintf(1,"Subsurface O&M Cost             = %6.2f M$\n",SubsurfaceOandMCost/1e6);
fprintf(1,"Capital cost of storage         = %6.2f $/kWh-th\n",econ.subsurface_capital_cost/(gTES.energy_capacity*1e6));

fprintf(1,'\nSURFACE COST RESULTS\n\n');
fprintf(1,'Solar field cost                = %6.2f M$\n',CSP.total_cost/1e6)
fprintf(1,'Low-temp. power cycle cost      = %6.2f M$\n\n',LTPC.total_cost/1e6)

fprintf(1,'Surface capital cost            = %6.2f M$\n',econ.surface_capital_cost/1e6)
fprintf(1,'Surface O&M cost                = %6.2f M$\n\n',econ.OnM_surface/1e6)

fprintf(1,'\nTOTAL COST RESULTS\n\n');
fprintf(1,'Total capital cost              = %6.2f M$\n',econ.total_capital_cost/1e6)
fprintf(1,'LCOE                            = %6.3f $/kWh-e\n',econ.LCOE)
fprintf(1,'LCOH                            = %6.3f $/kWh-th\n',econ.LCOH)
fprintf(1,'GeoTES contribution to LCOE     = %6.3f $/kWh-e\n\n',geoTES_LCOE)
fprintf(1,'Cost results including an investment tax credit of %4.2f%%\n',100*econ.ITC)
fprintf(1,'Total capital cost (ITC)        = %6.2f M$\n',econ.total_capital_cost_ITC/1e6)
fprintf(1,'LCOE (ITC)                      = %6.3f $/kWh-e\n',econ.LCOE_ITC)
fprintf(1,'LCOH (ITC)                      = %6.3f $/kWh-th\n',econ.LCOH_ITC)
fprintf(1,'GeoTES contribution to LCOE (ITC) = %6.3f $/kWh-e\n\n',geoTES_LCOE_ITC)


%% Plot out some economic results
% Save figure formats
formats = {'fig','svg'};

% Capital cost
xlab = {'Exploration','Permitting','Charge drilling','Charge production pumps',...
    'Charge injection pump','Charge flow line',...
    'Discharge drilling','Discharge production pumps',...
    'Discharge injection pump','Discharge flow line',...
    'CSP','Low-temp power cycle'};

figure(1)
bar(Ccap);
set(gca, 'XTick', 1:12, 'XTickLabel', xlab, 'TickLabelInterpreter', 'latex')
ylabel('Capital cost, M\$');
if save_figs == 1; save_fig(1, './Outputs/capital_cost',formats); end


% Contribution to LCOE
% Storage contribution to LCOE and LCOH
xlab = {'Exploration','Permitting','Charge drilling','Charge production pumps',...
    'Charge injection pump','Charge flow line',...
    'Discharge drilling','Discharge production pumps',...
    'Discharge injection pump','Discharge flow line',...
    'CSP','Low-temp power cycle',...
    'Subsurface O\&M','Surface O\&M'};


figure(2)
bar(LCOE_mat);
set(gca, 'XTick', 1:14, 'XTickLabel', xlab, 'TickLabelInterpreter', 'latex')
ylabel('LCOE, \$/kWh-e');
if save_figs == 1; save_fig(2, './Outputs/LCOE',formats); end

%% Plot technical results
figure(3)
n=(nY-1)*8760+1:nY*8760;
plot(gTES.energy(n)/1000);
xlim([0 8760]);
pbaspect([3 1 1])
xlabel('Hour of the year');
ylabel('Energy in geoTES, GWh-th')
if save_figs == 1; save_fig(3, './Outputs/geoTES_SOC',formats); end

figure(4)
n=24*27+(nY-1)*8760+1:24*31+(nY-1)*8760+1;
plot(CSP.power(n)); hold on
plot(gTES.power(n));
plot(LTPC.Qin(n)); 
plot(Qload_hourly(n)); hold off;
pbaspect([3 1 1])
title('January 27')
xlabel('Hour');
ylabel('Heat, MWh-th');
legend('Solar heat', ...
    'Heat to geoTES','Heat to LT power cycle','Heat to thermal load', ...
    'Location','southoutside', ...
    'Orientation','vertical',...
    'FontSize',10);
if save_figs == 1; save_fig(4, './Outputs/January_power_flows',formats); end


figure(5)
n=24*day(datetime(2022,8,1),'dayofyear')+(nY-1)*8760+1:24*day(datetime(2022,8,4),'dayofyear')+(nY-1)*8760+1;
plot(CSP.power(n)); hold on
plot(gTES.power(n));
plot(LTPC.Qin(n)); 
plot(Qload_hourly(n)); hold off;
pbaspect([3 1 1])
title('August 4')
xlabel('Hour');
ylabel('Heat, MWh-th');
legend('Solar heat',...
    'Heat to geoTES','Heat to LT power cycle','Heat to thermal load', ...
    'Location','southoutside', ...
    'Orientation','vertical',...
    'FontSize',10);
if save_figs == 1; save_fig(5, './Outputs/August_power_flows',formats); end

figure(6)
n=24*day(datetime(2022,2,7),'dayofyear')+(nY-1)*8760+1:24*day(datetime(2022,2,11),'dayofyear')+(nY-1)*8760+1;
plot(CSP.power(n)); hold on
plot(gTES.power(n));
plot(LTPC.Qin(n)); 
plot(Qload_hourly(n)); hold off;
pbaspect([3 1 1])
title('February 7')
xlabel('Hour');
ylabel('Heat, MWh-th');
legend('Solar heat',...
    'Heat to geoTES','Heat to LT power cycle','Heat to thermal load', ...
    'Location','southoutside', ...
    'Orientation','vertical',...
    'FontSize',10);
if save_figs == 1; save_fig(6, './Outputs/Feb_power_flows',formats); end






% Um
Net_wout = LTPC.Wout_tot- (Energy_charge_prod + Energy_charge_inj + Energy_discharge_prod + Energy_discharge_inj) ;
cap_hours = (gTES.energy_in_tot*gTES.recovery - gTES.energy_out_tot)*LTPC.eff0*1000/LTPC.Wout0; % Hours that full power can be delivered by capacity storage
Ecap = (gTES.energy_in_tot*gTES.recovery - gTES.energy_out_tot)*LTPC.eff0*1e6; % Electricity capacity for emergencies, kWh-e
d = 0.05 ; % Discount rate
G = (1-(1+d)^-econ.lifetime)/(1-(1+d)^-1);

pel_5 = 0.05 ; % price of electricity, $/kWh-e
Rel_5 = pel_5 * Net_wout * 1e6 ; % Revenue from selling electricity at price pel

cv_5 = (econ.total_capital_cost/G - Rel_5 + econ.OnM_total) / Ecap ;
cap_payment_5 = (econ.total_capital_cost/G - Rel_5 + econ.OnM_total) / (LTPC.Wout0 * 1000) ;


pel_10 = 0.10 ; % price of electricity, $/kWh-e
Rel_10 = pel_10 * Net_wout * 1e6 ; % Revenue from selling electricity at price pel

cv_10 = (econ.total_capital_cost/G - Rel_10 + econ.OnM_total) / Ecap ;
cap_payment_10 = (econ.total_capital_cost/G - Rel_10 + econ.OnM_total) / (LTPC.Wout0 * 1000) ;

% Results matrix
results = [CSP.solar_multiple;CSP.available_solar_heat;...
    CSP.solar_thermal_generated;LTPC.Qin_tot;LTPC.Wout_tot;...
    LTPC.Wout_tot- (Energy_charge_prod + Energy_charge_inj + Energy_discharge_prod + Energy_discharge_inj);...
    gTES.energy_in_tot;gTES.energy_out_tot;gTES.energy_capacity;gTES.energy_capacity*1000/(LTPC.Wout0/LTPC.eff0);...,
    econ.subsurface_capital_cost/(gTES.energy_capacity*1e6);gTES.charge_prod_Nwell;...
    gTES.charge_inj_Nwell;gTES.discharge_prod_Nwell;gTES.discharge_inj_Nwell;...
    econ.total_capital_cost/1e6;econ.LCOE;econ.LCOH;econ.LCOE_ITC;...
    econ.LCOH_ITC;geoTES_LCOE;geoTES_LCOE_ITC;cap_payment_5;cap_payment_10;cap_hours;Ccap';LCOE_mat'];

short_results = [econ.LCOE;econ.LCOE_ITC;econ.LCOH;econ.LCOH_ITC;geoTES_LCOE;geoTES_LCOE_ITC;econ.subsurface_capital_cost/(gTES.energy_capacity*1e6);econ.total_capital_cost;econ.OnM_total;net_elec;cap_fac;100*CSP.total_dumped/CSP.solar_thermal_generated;gTES.charge_inj_Nwell+gTES.charge_prod_Nwell+gTES.discharge_inj_Nwell+gTES.discharge_prod_Nwell] ;

