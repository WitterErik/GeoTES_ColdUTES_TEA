classdef InjectionPumpingCost
    % Pumping Cost calculator for GeoTES
    %   Estimates the injection pumping cost based on the indvidual well flow rate

    properties
        ReservoirTemperature
        InjectionTemperature
        InjWellFlowRate
        ProdWellFlowRate
        PressureThermalSource
        WellInjectivity
        WellDepth
        WellType    % "Small" or "Large" Diameter
        WellTempLoss
        Completion  % "Openhole" or "Liner"
        ProductionThickness
        InjectionCasingSize
        PumpCasingSize
        PumpType    % "ESP", "Lineshaft", or "PCP"
        NumberInjectionWells
        PPImultiplier
        OperationMode   % "Charge" or "Discharge"
        TotalPumpingDuty
        TotalPumpingCost
        


    end

    methods
        function InjPumping = InjectionPumpingCost(ResTemp,InjTemp,InjFlowRate,ProdFlowRate,PThermalSource,NoInjWells,Injectivity,Depth,Thickness,WellType,CompletionType,PPI, OpMode)
            %   Defines the input arguments for the production pumping
            %   calculations
            %   Detailed explanation goes here
            InjPumping.ReservoirTemperature = ResTemp;
            InjPumping.InjectionTemperature = InjTemp;
            InjPumping.InjWellFlowRate = InjFlowRate;
            InjPumping.ProdWellFlowRate = ProdFlowRate;
            InjPumping.PressureThermalSource = PThermalSource;
            InjPumping.NumberInjectionWells = NoInjWells;
            InjPumping.WellDepth = Depth;
            InjPumping.ProductionThickness = Thickness;
            InjPumping.WellType = WellType;
            %InjPumping.PumpType = PumpType;
            InjPumping.TotalPumpingDuty = [];
            InjPumping.TotalPumpingCost = [];
            InjPumping.WellInjectivity = Injectivity;
            InjPumping.Completion = CompletionType;
            InjPumping.WellTempLoss = 0.0005; % C/m
            InjPumping.PPImultiplier = PPI;
            InjPumping.OperationMode = OpMode;
        end
        

        % Pump Head from well head to sunction depth
        function PumpHeadSunction = HeadSunction(InjPumping)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            if InjPumping.WellType == "Small"
                CasingIntDiameter = 9.625 - (2 * 0.4375); % inches
            else 
                CasingIntDiameter = 13.625 - (2 * 0.5625); % inches
            end
            WellDepthft = InjPumping.WellDepth * 3.28084;
            ProdThicknessft = InjPumping.ProductionThickness * 3.28084;
            ColumnDepth = WellDepthft - ProdThicknessft;
            ResTemperatureF = InjPumping.ReservoirTemperature * 1.8 + 32;
            InjTemperatureF = InjPumping.InjectionTemperature * 1.8 + 32;
            WellTempLossFft = InjPumping.WellTempLoss * 1.8/3.28083;
            ProdInjRatio = InjPumping.ProdWellFlowRate/InjPumping.InjWellFlowRate;
            Pexcess = 50; % Excess pressure to ensure that NCG says in solution, in psi
            DeltaPPlant = 40; % pressure drop (in psi) through the surface equipment for binary plants
            Twellhead = ResTemperatureF-WellTempLossFft*WellDepthft;
            Psatwellhead = (-2.55175E-12*Twellhead^5) + 2.41218E-08*Twellhead^4 + (-9.19096E-06*Twellhead^3) + (0.001969537*Twellhead^2) + (-0.197885257*Twellhead) + 8.089410675;         
            
            if InjPumping.OperationMode == "Charge"
                Pwellhead = InjPumping.PressureThermalSource;
            else
                Pwellhead = Psatwellhead + Pexcess - DeltaPPlant;
            end
                        
            SurfaceRoughness = 0.00015; % in ft (K55 casing)
            TavgF = InjTemperatureF+(0.5*WellTempLossFft*ProdInjRatio*ColumnDepth); % Average temperature within a well interval in F
            rho = 1/((1.40682E-18*TavgF^6)+(-2.69957E-15*TavgF^5)+(2.17758E-12*TavgF^4)+(-9.15282E-10*TavgF^3)+(2.2418E-7*TavgF^2)+(-2.3968E-5*TavgF)+0.017070952);
            Psatwater = (-2.55175E-12*TavgF^5) + 2.41218E-08*TavgF^4 + (-9.19096E-06*TavgF^3) + (0.001969537*TavgF^2) + (-0.197885257*TavgF) + 8.089410675;
            PressureRatio = 0.5*((rho*ColumnDepth/144)+Pwellhead)/Psatwater; % Pressure (or average pressure within an interval) / Psat
            rhocorrected = rho*(1+(7.15037E-19*TavgF^5.91303)*(PressureRatio-1)); % Pressure-corrected density
            viscosity = 407.22 * TavgF^(-1.194) / 3600;  % in lb/ft-s
            viscositycorrected = viscosity*(1+(4.02401E-18*TavgF^5.736882)*(PressureRatio-1)); % Pressure-corrected density;
            Velocity = ((InjPumping.InjWellFlowRate*7936.64/rhocorrected)/3600) / (pi() * (CasingIntDiameter/12)^2 / 4); % ft/sec
            ReynoldsNum = rhocorrected * Velocity * (CasingIntDiameter/12)/viscositycorrected;
            Aconst = -2*log10((SurfaceRoughness/(CasingIntDiameter/12))/3.7+12/ReynoldsNum);
            Bconst = -2*log10((SurfaceRoughness/(CasingIntDiameter/12))/3.7+(2.51*Aconst)/ReynoldsNum);
            Cconst = -2*log10((SurfaceRoughness/(CasingIntDiameter/12))/3.7+(2.51*Bconst)/ReynoldsNum);
            FrictionFactor = (Aconst-(Bconst-Aconst)^2/(Cconst-2*Bconst+Aconst))^-2; % Serghide's friction factor
            Headfrictionloss = ((FrictionFactor*1/(CasingIntDiameter/12)) * (Velocity^2)/(2*32.174)); %in ft
            Pfrictionloss = Headfrictionloss*ColumnDepth*rhocorrected/144; % in psi
            PumpHeadSunction = Pwellhead + rhocorrected*ColumnDepth/144 - Pfrictionloss; % in psi
        end


                % Depth of water column from sunction depth to top of production zone       
        function PumpHeadInjection = HeadInjection(InjPumping,PumpHeadSunction)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            if InjPumping.WellType == "Small" && InjPumping.Completion == "Openhole"
                WellDiameter = 8.5; % inches
            elseif InjPumping.WellType == "Small" && InjPumping.Completion == "Liner"
                WellDiameter = 7; % inches
            elseif InjPumping.WellType == "Large" && InjPumping.Completion == "Openhole"
                WellDiameter = 12.25; % inches
            else 
                WellDiameter = 9.625; % inches
            end

            WellDepthft = InjPumping.WellDepth * 3.28084;
            ProdThicknessft = InjPumping.ProductionThickness * 3.28084;
            ColumnDepth = WellDepthft - ProdThicknessft;
%             ResTemperatureF = InjPumping.ReservoirTemperature * 1.8 + 32;
            InjTemperatureF = InjPumping.InjectionTemperature * 1.8 + 32;
            WellTempLossFft = InjPumping.WellTempLoss * 1.8/3.28083;
            ProdInjRatio = InjPumping.ProdWellFlowRate/InjPumping.InjWellFlowRate;
            Tsurf = 52.88; % surface temp in degree Farenheit
%             Psatsurf = (-2.55175E-12*Tsurf^5) + 2.41218E-08*Tsurf^4 + (-9.19096E-06*Tsurf^3) + (0.001969537*Tsurf^2) + (-0.197885257*Tsurf) + 8.089410675;
                        
            if InjPumping.Completion == "Openhole"
                SurfaceRoughness = 0.02; % in ft
            else
                SurfaceRoughness = 0.001; % in ft
            end

            rhosurf =  (-0.00000000017845*Tsurf^4 + 0.00000020215*Tsurf^3 - 0.00012456*Tsurf^2 + 0.0072343*Tsurf + 62.329) * 16.01846; %density at surface conditions
            % density at any temperature (in F) below surface in lb/ft^3
            Psurf = 1.01325; % atmospheric pressure in bar
            tauT = (InjPumping.ReservoirTemperature-((Tsurf-32)/1.8))/InjPumping.WellDepth; % Earth temperature gradient in C/m User can specify
            Cp = 0.000000000464; % Pressure Gradient in 1/bar
            CT = (9E-4)/(30.796 * InjPumping.ReservoirTemperature^-0.552); % Temperature gradient coefficient 1/degree celcius
            Phydrostatic = Psurf + 1/Cp*((exp(rhosurf*9.807*Cp*(InjPumping.WellDepth-(0.5*CT*tauT*InjPumping.WellDepth^2))/100000))-1); % in bar
            Phydropsi = 14.50377 * Phydrostatic; % Hydrostatic pressure in psi
            Buildup = InjPumping.InjWellFlowRate * 7936.64 / InjPumping.WellInjectivity; % Pressure drawdown in psi
                        
            TavgF = InjTemperatureF + (WellTempLossFft*ProdInjRatio*(ColumnDepth+0.5*ProdThicknessft)); % Average temperature within a well interval in F
            Psatwater = (-2.55175E-12*TavgF^5) + 2.41218E-08*TavgF^4 + (-9.19096E-06*TavgF^3) + (0.001969537*TavgF^2) + (-0.197885257*TavgF) + 8.089410675;
            rho = 1/((1.40682E-18*TavgF^6)+(-2.69957E-15*TavgF^5)+(2.17758E-12*TavgF^4)+(-9.15282E-10*TavgF^3)+(2.2418E-7*TavgF^2)+(-2.3968E-5*TavgF)+0.017070952);
            PressureRatio = (PumpHeadSunction+0.5*rho*ProdThicknessft/144)/Psatwater; % Pressure (or average pressure within an interval) / Psat
            rhocorrected = rho*(1+(7.15037E-19*TavgF^5.91303)*(PressureRatio-1)); % Pressure-corrected density
            viscosity = 407.22 * TavgF^(-1.194) / 3600;  % in lb/ft-s
            viscositycorrected = viscosity*(1+(4.02401E-18*TavgF^5.736882)*(PressureRatio-1)); % Pressure-corrected density;
            Velocity = ((InjPumping.InjWellFlowRate*7936.64/rhocorrected)/3600) / (pi() * (WellDiameter/12)^2 / 4); % ft/sec
            ReynoldsNum = rho * Velocity * (WellDiameter/12)/viscositycorrected;
            Aconst = -2*log10((SurfaceRoughness/(WellDiameter/12))/3.7+12/ReynoldsNum);
            Bconst = -2*log10((SurfaceRoughness/(WellDiameter/12))/3.7+(2.51*Aconst)/ReynoldsNum);
            Cconst = -2*log10((SurfaceRoughness/(WellDiameter/12))/3.7+(2.51*Bconst)/ReynoldsNum);
            FrictionFactor = (Aconst-(Bconst-Aconst)^2/(Cconst-2*Bconst+Aconst))^-2; % Serghide's friction factor
            Headfrictionloss = ((FrictionFactor*1/(WellDiameter/12)) * (Velocity^2)/(2*32.174)); %in ft
            Pfrictionloss = Headfrictionloss*ProdThicknessft*rhocorrected/144; % in psi
            PbottomholeNoPumping = PumpHeadSunction + rhocorrected*ProdThicknessft/144 - Pfrictionloss; % Bottomhole pressure without pumping in psi
            ExcessPressure = PbottomholeNoPumping - Phydropsi; % Excess pressure at production zone
            
            if ExcessPressure - Buildup > 1
               InjPumpHead = 1 ; % additional excess in psi
            else
               InjPumpHead = Buildup + 1 - ExcessPressure;
            end

            rhoinj = 1/((1.40682E-18*InjTemperatureF^6)+(-2.69957E-15*InjTemperatureF^5)+(2.17758E-12*InjTemperatureF^4)+(-9.15282E-10*InjTemperatureF^3)+(2.2418E-7*InjTemperatureF^2)+(-2.3968E-5*InjTemperatureF)+0.017070952);
            PumpHeadInjection = InjPumpHead * 144 / rhoinj; % in ft
        end
        
        
        % Total power required for injection pumping
        function PumpingPower = Pumppower(InjPumping,PumpHeadInjection)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            Pumppowerideal = ((InjPumping.InjWellFlowRate*7936.64)*PumpHeadInjection)/(60*33000); % in horsepower
            PumpEfficiency = 0.68;
            Pumppowerreal = (Pumppowerideal)/PumpEfficiency; %in hp
            PumppowerrealkW = Pumppowerreal*0.7457;
            PumpingPower = PumppowerrealkW;
        end
        
        % Cost of production pump per well
        function PumpingCost = Pumpcost(InjPumping,Pumpingpower)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            PumpUnits = (Pumpingpower/0.7457)/ceil(Pumpingpower/2000);
            if Pumpingpower/0.7457 < 2000
                PumpingUnitCost = 1750*(Pumpingpower/0.7457)^0.7+3*(Pumpingpower/0.7457)^-0.11;
            else
                PumpingUnitCost = PumpUnits * (1750*((Pumpingpower/0.7457)/PumpUnits)^0.7+3*((Pumpingpower/0.7457)/PumpUnits)^-0.11);
            end
            PumpingCost = PumpingUnitCost * InjPumping.PPImultiplier;
        end

                % Cost of production pump per well
        function TotalPumpDutyandCost = TotalPumpDutyCost(InjPumping,PumpingPower,PumpingCost)
            %METHOD1 Summary of this method goes here
            %   Detailed explanation goes here
            InjPumping.TotalPumpingDuty = PumpingPower * InjPumping.NumberInjectionWells ;
            InjPumping.TotalPumpingCost = PumpingCost * InjPumping.NumberInjectionWells;
            %disp("Total Injection Pumping Cost = $" + InjPumping.TotalPumpingCost);
            %disp("Total Injection Pumping Duty = " + InjPumping.TotalPumpingDuty + "kW");
            TotalPumpDutyandCost = [InjPumping.TotalPumpingDuty,InjPumping.TotalPumpingCost];
        end
        
    end
end