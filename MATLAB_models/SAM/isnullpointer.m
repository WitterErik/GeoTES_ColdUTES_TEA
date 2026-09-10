function bb = isnullpointer(p)
    bb = false;
    try
        setdatatype(p, 'voidPtr', 1, 1);
        deref = get(p);
    catch
        e = lasterror();
        if strcmp(e.identifier, 'MATLAB:libpointer:ValueNotDefined')
            bb = true;
        end
    end
end