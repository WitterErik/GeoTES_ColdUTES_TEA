classdef ProductionPumpingCost
    % Pumping Cost calculator for GeoTES
    %   Estimates the pumping cost based on the indvidual well flow rate
    %   Three types of pumps can be assessed:
    %   (1) ESP: Electric Submersible Pump
    %   (2) Lineshaft Vertical Turbine Pump
    %   ESP cost is based on xxx dollar year
    %   Lineshaft pump cost is based on a 2002 dollar year
    %   The user will need to convert to current dollar year using PPI
    %   multiplier

    properties
        ReservoirTemperature
        WellFlowRate
        WellProductivity
        WellDepth
        WellType    % "Small" or "Large" Diameter
        WellTempLoss
        Completion
        ProductionThickness
        PumpCasingSize
        PumpType    % "ESP" or "Lineshaft"
        NumberProductionWells
        PPImultiplier
        TotalPumpingDuty
        TotalPumpingCost
        


    end

    methods
        function ProdPumping = ProductionPumpingCost(ResTemp,FlowRate,NoProdWells,Productivity,Depth,Thickness,WellType,PumpType,CompletionType,PPI)
            %   Defines the input arguments for the production pumping
            %   calculations
            %   Detailed explanation goes here
            ProdPumping.ReservoirTemperature = ResTemp; % Celsius
            ProdPumping.WellFlowRate = FlowRate;
            ProdPumping.NumberProductionWells = NoProdWells;
            ProdPumping.WellDepth = Depth;
            ProdPumping.ProductionThickness = Thickness;
            ProdPumping.WellType = WellType;
            ProdPumping.PumpType = PumpType;
            ProdPumping.TotalPumpingDuty = [];
            ProdPumping.TotalPumpingCost = [];
            ProdPumping.WellProductivity = Productivity;
            ProdPumping.Completion = CompletionType;
            ProdPumping.WellTempLoss = 0.0005; % C/m
            ProdPumping.PPImultiplier = PPI;
        end
        

        % Depth of water column from sunction depth to top of production zone       
        function PumpHeadProdTop = HeadProdTop(ProdPumping)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            if ProdPumping.WellType == "Small" && ProdPumping.Completion == "Openhole"
                WellDiameter = 8.5; % inches
            elseif ProdPumping.WellType == "Small" && ProdPumping.Completion == "Liner"
                WellDiameter = 7; % inches
            elseif ProdPumping.WellType == "Large" && ProdPumping.Completion == "Openhole"
                WellDiameter = 12.25; % inches
            else 
                WellDiameter = 9.625; % inches
            end

            ProdThicknessft = ProdPumping.ProductionThickness * 3.28084;
            ResTemperatureF = ProdPumping.ReservoirTemperature * 1.8 + 32;
            WellTempLossFft = ProdPumping.WellTempLoss * 1.8/3.28083;
            Tsurf = 52.88; % surface temp in degree Farenheit
%             Psatsurf = (-2.55175E-12*Tsurf^5) + 2.41218E-08*Tsurf^4 + (-9.19096E-06*Tsurf^3) + (0.001969537*Tsurf^2) + (-0.197885257*Tsurf) + 8.089410675;
                        
            if ProdPumping.Completion == "Openhole"
                SurfaceRoughness = 0.02; % in ft
            else
                SurfaceRoughness = 0.001; % in ft
            end

            rhosurf =  (-0.00000000017845*Tsurf^4 + 0.00000020215*Tsurf^3 - 0.00012456*Tsurf^2 + 0.0072343*Tsurf + 62.329) * 16.01846; %density at surface conditions
            % density at any temperature (in F) below surface in lb/ft^3
            Psurf = 1.01325; % atmospheric pressure in bar
            tauT = (ProdPumping.ReservoirTemperature-((Tsurf-32)/1.8))/ProdPumping.WellDepth; % Earth temperature gradient in C/m User can specify
            Cp = 0.000000000464; % Pressure Gradient in 1/bar
            CT = (9E-4)/(30.796 * ProdPumping.ReservoirTemperature^-0.552); % Temperature gradient coefficient 1/degree celcius
            Phydrostatic = Psurf + 1/Cp*((exp(rhosurf*9.807*Cp*(ProdPumping.WellDepth-(0.5*CT*tauT*ProdPumping.WellDepth^2))/100000))-1); % in bar
            Phydropsi = 14.50377 * Phydrostatic; % Hydrostatic pressure in psi
            Drawdown = ProdPumping.WellFlowRate * 7936.64 / ProdPumping.WellProductivity; % Pressure drawdown in psi
            Pbottomhole = Phydropsi - Drawdown; % Bottomhole pressure in psi
            
            TavgF = ResTemperatureF-0.5*WellTempLossFft*ProdThicknessft; % Average temperature within a well interval in F
            Psatwater = (-2.55175E-12*TavgF^5) + 2.41218E-08*TavgF^4 + (-9.19096E-06*TavgF^3) + (0.001969537*TavgF^2) + (-0.197885257*TavgF) + 8.089410675;
            rho = 1/((1.40682E-18*TavgF^6)+(-2.69957E-15*TavgF^5)+(2.17758E-12*TavgF^4)+(-9.15282E-10*TavgF^3)+(2.2418E-7*TavgF^2)+(-2.3968E-5*TavgF)+0.017070952);
            PressureRatio = (Pbottomhole-0.5*rho*ProdThicknessft/144)/Psatwater; % Pressure (or average pressure within an interval) / Psat
            rhocorrected = rho*(1+(7.15037E-19*TavgF^5.91303)*(PressureRatio-1)); % Pressure-corrected density
            viscosity = 407.22 * TavgF^(-1.194) / 3600;  % in lb/ft-s
            viscositycorrected = viscosity*(1+(4.02401E-18*TavgF^5.736882)*(PressureRatio-1)); % Pressure-corrected density;
            Velocity = ((ProdPumping.WellFlowRate*7936.64/rhocorrected)/3600) / (pi() * (WellDiameter/12)^2 / 4); % ft/sec
            ReynoldsNum = rho * Velocity * (WellDiameter/12)/viscositycorrected;
            Aconst = -2*log10((SurfaceRoughness/(WellDiameter/12))/3.7+12/ReynoldsNum);
            Bconst = -2*log10((SurfaceRoughness/(WellDiameter/12))/3.7+(2.51*Aconst)/ReynoldsNum);
            Cconst = -2*log10((SurfaceRoughness/(WellDiameter/12))/3.7+(2.51*Bconst)/ReynoldsNum);
            FrictionFactor = (Aconst-(Bconst-Aconst)^2/(Cconst-2*Bconst+Aconst))^-2; % Serghide's friction factor
%             FrictionFactor = ((Cconst-2*Bconst+Aconst)/(Aconst*Cconst-Bconst^2))^2;
            DeltaPFriction = (rho * ProdThicknessft * ((FrictionFactor*1/(WellDiameter/12)) * (Velocity^2)/(2*32.174))) / 144;
            Pprodtop = Pbottomhole-DeltaPFriction-(rhocorrected*ProdThicknessft/144);
            PumpHeadProdTop.Prodtop = Pprodtop; % in psi
        end

        % Pump Head from well head to sunction depth
        function PumpHeadSunction = HeadSunction(ProdPumping,PumpHeadProdTop)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            if ProdPumping.WellType == "Small"
                CasingIntDiameter = 9.625 - (2 * 0.4375); % inches
            else 
                CasingIntDiameter = 13.625 - (2 * 0.5625); % inches
            end
            WellDepthft = ProdPumping.WellDepth * 3.28084;
            ProdThicknessft = ProdPumping.ProductionThickness * 3.28084;
            ColumnDepth = WellDepthft - ProdThicknessft;
            ResTemperatureF = ProdPumping.ReservoirTemperature * 1.8 + 32;
            WellTempLossFft = ProdPumping.WellTempLoss * 1.8/3.28083;
            Pexcess = 50; % Excess pressure to ensure that NCG says in solution, in psi
%             Tsurf = 52.88; % surface temp in degree Farenheit
            Twellhead = ResTemperatureF-WellTempLossFft*WellDepthft;
            Psatwellhead = (-2.55175E-12*Twellhead^5) + 2.41218E-08*Twellhead^4 + (-9.19096E-06*Twellhead^3) + (0.001969537*Twellhead^2) + (-0.197885257*Twellhead) + 8.089410675;         
            SurfaceRoughness = 0.00015; % in ft (K55 casing)

            TavgF = ResTemperatureF-0.5*WellTempLossFft*ColumnDepth; % Average temperature within a well interval in F
            rho = 1/((1.40682E-18*TavgF^6)+(-2.69957E-15*TavgF^5)+(2.17758E-12*TavgF^4)+(-9.15282E-10*TavgF^3)+(2.2418E-7*TavgF^2)+(-2.3968E-5*TavgF)+0.017070952);
            Psatwater = (-2.55175E-12*TavgF^5) + 2.41218E-08*TavgF^4 + (-9.19096E-06*TavgF^3) + (0.001969537*TavgF^2) + (-0.197885257*TavgF) + 8.089410675;
            PressureRatio = (0.5 * (PumpHeadProdTop + Psatwater))/Psatwater; % Pressure (or average pressure within an interval) / Psat
            rhocorrected = rho*(1+(7.15037E-19*TavgF^5.91303)*(PressureRatio-1)); % Pressure-corrected density
            viscosity = 407.22 * TavgF^(-1.194) / 3600;  % in lb/ft-s
            viscositycorrected = viscosity*(1+(4.02401E-18*TavgF^5.736882)*(PressureRatio-1)); % Pressure-corrected density;
            Velocity = ((ProdPumping.WellFlowRate*7936.64/rhocorrected)/3600) / (pi() * (CasingIntDiameter/12)^2 / 4); % ft/sec
            ReynoldsNum = rhocorrected * Velocity * (CasingIntDiameter/12)/viscositycorrected;
            Aconst = -2*log10((SurfaceRoughness/(CasingIntDiameter/12))/3.7+12/ReynoldsNum);
            Bconst = -2*log10((SurfaceRoughness/(CasingIntDiameter/12))/3.7+(2.51*Aconst)/ReynoldsNum);
            Cconst = -2*log10((SurfaceRoughness/(CasingIntDiameter/12))/3.7+(2.51*Bconst)/ReynoldsNum);
            FrictionFactor = (Aconst-(Bconst-Aconst)^2/(Cconst-2*Bconst+Aconst))^-2; % Serghide's friction factor
            
            Pavailable = (PumpHeadProdTop - Pexcess - Psatwellhead) * 144; % in pounds per square ft
            Headfrictionloss = ((FrictionFactor*1/(CasingIntDiameter/12)) * (Velocity^2)/(2*32.174)); %in ft/ft
            Headavailable = (Pavailable/rhocorrected)/(1+Headfrictionloss); % in ft            
            PumpHeadSunction = Headavailable; % in ft
        end

        
        % Depth of the pump sunction inlet
        function SunctionDepth = Sunctiondepth(ProdPumping,PumpHeadSunction)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            ProdThicknessft = ProdPumping.ProductionThickness * 3.28084;
            Pumpsettingdepth = (ProdPumping.WellDepth*3.28084)-ProdThicknessft-PumpHeadSunction; % in ft
            SunctionDepth = Pumpsettingdepth;
        end

        % Friction Head within pump casing
        function CasingFrictionHead = CasingFriction(ProdPumping,SunctionDepth,PumpHeadProdTop)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            if ProdPumping.WellType == "Small"
                PumpCasingDiameter = 7 - 0.944; % inches
            else 
                PumpCasingDiameter = 9.625 - 0.944; % inches
            end
            WellDepthft = ProdPumping.WellDepth * 3.28084;
            ProdThicknessft = ProdPumping.ProductionThickness * 3.28084;
            ColumnDepth = WellDepthft - ProdThicknessft;
            ResTemperatureF = ProdPumping.ReservoirTemperature * 1.8 + 32;
            WellTempLossFft = ProdPumping.WellTempLoss * 1.8/3.28083;
            SurfaceRoughness = 0.00015; % in ft (K55 casing)
            TavgF = ResTemperatureF-0.5*WellTempLossFft*ColumnDepth; % Average temperature within a well interval in F
            rho = 1/((1.40682E-18*TavgF^6)+(-2.69957E-15*TavgF^5)+(2.17758E-12*TavgF^4)+(-9.15282E-10*TavgF^3)+(2.2418E-7*TavgF^2)+(-2.3968E-5*TavgF)+0.017070952);
            Psatwater = (-2.55175E-12*TavgF^5) + 2.41218E-08*TavgF^4 + (-9.19096E-06*TavgF^3) + (0.001969537*TavgF^2) + (-0.197885257*TavgF) + 8.089410675;
            PressureRatio = (0.5 * (PumpHeadProdTop + Psatwater))/Psatwater; % Pressure (or average pressure within an interval) / Psat
            rhocorrected = rho*(1+(7.15037E-19*TavgF^5.91303)*(PressureRatio-1)); % Pressure-corrected density
            viscosity = 407.22 * TavgF^(-1.194) / 3600;  % in lb/ft-s
            viscositycorrected = viscosity*(1+(4.02401E-18*TavgF^5.736882)*(PressureRatio-1)); % Pressure-corrected density;
            Velocity = ((ProdPumping.WellFlowRate*7936.64/rhocorrected)/3600) / (pi() * (PumpCasingDiameter/12)^2 / 4); % ft/sec
            ReynoldsNum = rhocorrected * Velocity * (PumpCasingDiameter/12)/viscositycorrected;
            Aconst = -2*log10((SurfaceRoughness/(PumpCasingDiameter/12))/3.7+12/ReynoldsNum);
            Bconst = -2*log10((SurfaceRoughness/(PumpCasingDiameter/12))/3.7+(2.51*Aconst)/ReynoldsNum);
            Cconst = -2*log10((SurfaceRoughness/(PumpCasingDiameter/12))/3.7+(2.51*Bconst)/ReynoldsNum);
            FrictionFactor = (Aconst-(Bconst-Aconst)^2/(Cconst-2*Bconst+Aconst))^-2; % Serghide's friction factor
            FrictionHead = SunctionDepth * ((FrictionFactor*1/(PumpCasingDiameter/12)) * (Velocity^2)/(2*32.174)); % in ft          
            CasingFrictionHead = FrictionHead;
        end
        
        % Power required for production pumping per well
        function PumpingPower = Pumppower(ProdPumping,SunctionDepth,CasingFrictionHead)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            PumpLift = SunctionDepth + CasingFrictionHead;
            Pumppowerideal = ((ProdPumping.WellFlowRate*7936.64/60)*PumpLift)/33000; % in horsepower

            if ProdPumping.PumpType == "ESP"
                PumpEfficiency = 0.68;
            elseif ProdPumping.PumpType == "Lineshaft"
                PumpEfficiency = 0.68;
            else
                PumpEfficiency = 0.675;
            end

            Pumppowerreal = (Pumppowerideal)/PumpEfficiency; %in hp
            PumppowerrealkW = Pumppowerreal*0.7457;
            PumpingPower = PumppowerrealkW;
        end
        
        % Cost of production pump per well
        function PumpingCost = Pumpcost(ProdPumping,PumppowerrealkW,SunctionDepth)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            if ProdPumping.PumpType == "ESP"
                PumpingUnitCost = 1500*(PumppowerrealkW/0.7457)^0.7+5750*(PumppowerrealkW/0.7457)^0.2; % NOT CORRECT. JUST A PLACEHOLDER
            elseif ProdPumping.PumpType == "Lineshaft"
                PumpingUnitCost = 1750*(PumppowerrealkW/0.7457)^0.7+5750*(PumppowerrealkW/0.7457)^0.2; % 2002 dollar year
            else
                PumpingUnitCost = 0.8;
            end
            
            WorkoverCost = 10000; % in $
            PumpCasingUnitCost = 44.74; % in $/ft
            InstallationUnitCost = 5.0; % in $/ft
            PumpCasingCost = PumpCasingUnitCost * SunctionDepth;
            PumpInstallationCost = PumpCasingCost + WorkoverCost + InstallationUnitCost*SunctionDepth;
            PumpingCost = PumpingUnitCost * ProdPumping.PPImultiplier + PumpInstallationCost;
        end

                % Cost of production pump per well
        function TotalPumpDutyandCost = TotalPumpDutyCost(ProdPumping,PumpingPower,PumpingCost)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            ProdPumping.TotalPumpingDuty = PumpingPower * ProdPumping.NumberProductionWells;
            ProdPumping.TotalPumpingCost = PumpingCost * ProdPumping.NumberProductionWells;
            %disp("Total Production Pumping Cost = $" + ProdPumping.TotalPumpingCost);
            %disp("Total Production Pumping Duty = " + ProdPumping.TotalPumpingDuty + "kW");
            TotalPumpDutyandCost = [ProdPumping.TotalPumpingDuty,ProdPumping.TotalPumpingCost];
        end

         % Maintenance cost per well
         function ProdPumpMaintenanceCost = PumpMaintenanceCost(ProdPumping,SunctionDepth,PumpingCost)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            WorkoverCost = 10000; % in $
            PumpCasingUnitCost = 44.74; % in $/ft
            InstallationUnitCost = 5.0; % in $/ft
            PumpCasingCost = PumpCasingUnitCost * SunctionDepth;
            PumpInstallationCost = PumpCasingCost + WorkoverCost + InstallationUnitCost*SunctionDepth;
            PumpReplacementUnitCost = PumpingCost - PumpInstallationCost;
            PumpReinstallCost = PumpInstallationCost - PumpCasingCost;
            PumpReworkUnitCost = PumpReplacementUnitCost + PumpReinstallCost;

            if ProdPumping.PumpType == "ESP"
                OperatingLife = 2; % years (GETEM)
                LubricatingOilUnitCost = 0; % $ per year (GETEM)
            elseif ProdPumping.PumpType == "Lineshaft"
                OperatingLife = 3; % years (GETEM)
                LubricatingOilUnitCost = 4300 * ProdPumping.PPImultiplier; % $ per year (GETEM)
            end
            
            LubricatingOilCost = LubricatingOilUnitCost * SunctionDepth/500; % in $ per year. 500 ft is the reference depth for cost
            ProdPumpMaintenanceCost = (PumpReworkUnitCost * ProdPumping.NumberProductionWells) / OperatingLife + ...
                LubricatingOilCost; % per year
        end
        
    end
end