classdef fluid_class
    
    properties
        fluid
        type
        handle
        fname
        tab
        p
        T
        h
        s
        q
        cp
        rho
        mdot
        vdot % m3/s
    end
    
    methods
        function obj = fluid_class(fluid_name)
            obj.fluid = fluid_name;

            switch obj.fluid
                case 'nitrate salt'
                    obj.type = 'tab';
                    obj.fname = '.\data\SolarSalt.dat';
                case'chloride salt'
                    obj.type = 'tab';
                    obj.fname = '.\data\ChlorideSalt.dat';
                case'Therminol VP1'
                    obj.type = 'tab';
                    obj.fname = '.\data\TherminolVP1.dat';
                otherwise
                    obj.type = 'cp';
            end

            switch obj.type
                case 'cp'
                    % Check python installed
                    a = pyenv;

                    % Check CoolProp package works
                    b= py.CoolProp.CoolProp.PropsSI('T','P',101325,'Q',0,'Water');
                case 'tab'
                    obj.tab = readmatrix(obj.fname);
            end

            
        end
        
        % Calculate remaining fluid properties given two properties
        function obj = calc_fluid_props(obj,mode)
            switch mode
                case {'pT','Tp'}
                    for i = 1:numel(obj.T)
                        obj.s(i) = py.CoolProp.CoolProp.PropsSI('S','P',obj.p(i)*1e5,'T',obj.T(i)+273.15,obj.fluid)/1e3;
                        obj.h(i) = py.CoolProp.CoolProp.PropsSI('H','P',obj.p(i)*1e5,'T',obj.T(i)+273.15,obj.fluid)/1e3;
                        obj.q(i) = py.CoolProp.CoolProp.PropsSI('Q','P',obj.p(i)*1e5,'T',obj.T(i)+273.15,obj.fluid);
                        obj.rho(i) = py.CoolProp.CoolProp.PropsSI('D','P',obj.p(i)*1e5,'T',obj.T(i)+273.15,obj.fluid);
                        obj.cp(i)  = py.CoolProp.CoolProp.PropsSI('CPMASS','P',obj.p(i)*1e5,'T',obj.T(i)+273.15,obj.fluid)/1e3;
                    end
                case {'pq','qp'}
                    for i = 1:numel(obj.p)
                        obj.s(i) = py.CoolProp.CoolProp.PropsSI('S','P',obj.p(i)*1e5,'Q',obj.q(i),obj.fluid)/1e3;
                        obj.h(i) = py.CoolProp.CoolProp.PropsSI('H','P',obj.p(i)*1e5,'Q',obj.q(i),obj.fluid)/1e3;
                        obj.T(i) = py.CoolProp.CoolProp.PropsSI('T','P',obj.p(i)*1e5,'Q',obj.q(i),obj.fluid)-273.15;
                        obj.rho(i) = py.CoolProp.CoolProp.PropsSI('D','P',obj.p(i)*1e5,'Q',obj.q(i),obj.fluid);
                        obj.cp(i)  = py.CoolProp.CoolProp.PropsSI('CPMASS','P',obj.p(i)*1e5,'Q',obj.q(i),obj.fluid)/1e3;
                    end
                case {'ph','hp'}
                    for i = 1:numel(obj.p)
                        obj.q(i) = py.CoolProp.CoolProp.PropsSI('Q','P',obj.p(i)*1e5,'H',obj.h(i)*1e3,obj.fluid);
                        obj.s(i) = py.CoolProp.CoolProp.PropsSI('S','P',obj.p(i)*1e5,'H',obj.h(i)*1e3,obj.fluid)/1e3;
                        obj.T(i) = py.CoolProp.CoolProp.PropsSI('T','P',obj.p(i)*1e5,'H',obj.h(i)*1e3,obj.fluid)-273.15;
                        obj.rho(i) = py.CoolProp.CoolProp.PropsSI('D','P',obj.p(i)*1e5,'H',obj.h(i)*1e3,obj.fluid);
                        obj.cp(i)  = py.CoolProp.CoolProp.PropsSI('CPMASS','P',obj.p(i)*1e5,'H',obj.h(i)*1e3,obj.fluid)/1e3;
                    end
                case {'Tq','qT'}
                    for i = 1:numel(obj.T)
                        obj.s(i) = py.CoolProp.CoolProp.PropsSI('S','Q',obj.q(i),'T',obj.T(i)+273.15,obj.fluid)/1e3;
                        obj.h(i) = py.CoolProp.CoolProp.PropsSI('H','Q',obj.q(i),'T',obj.T(i)+273.15,obj.fluid)/1e3;
                        obj.p(i) = py.CoolProp.CoolProp.PropsSI('P','Q',obj.q(i),'T',obj.T(i)+273.15,obj.fluid)/1e5;
                        obj.rho(i) = py.CoolProp.CoolProp.PropsSI('D','Q',obj.q(i),'T',obj.T(i)+273.15,obj.fluid);
                        obj.cp(i)  = py.CoolProp.CoolProp.PropsSI('CPMASS','Q',obj.q(i),'T',obj.T(i)+273.15,obj.fluid)/1e3;
                    end
                case 'T'
                    for i = 1:numel(obj.T)
                        obj.h(i) = interp1(obj.tab(:,1),obj.tab(:,2),obj.T(i)+273.15)/1e3;
                        obj.s(i) = interp1(obj.tab(:,1),obj.tab(:,4),obj.T(i)+273.15)/1e3;
                        obj.rho(i) = interp1(obj.tab(:,1),obj.tab(:,3),obj.T(i)+273.15);
                        obj.cp(i) = interp1(obj.tab(:,1),obj.tab(:,5),obj.T(i)+273.15)/1e3;
                    end
                otherwise
                    error('Not implemeted')
            end
        end

        % Calculate mass flow or volume flow given the other value
        function obj = calc_mdot_vdot(obj,mode)
            switch mode
                case 'vdot'
                    obj.vdot = obj.mdot / obj.rho ;
                case 'mdot'
                    obj.mdot = obj.vdot * obj.rho ;
                otherwise
                    error('Not implemented')
            end
        end
    end
end

