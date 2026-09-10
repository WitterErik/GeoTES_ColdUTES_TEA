"""
SAM ssccall wrapper using PySAM library.
Provides a compatibility layer for the low-level SAM C API calls.
"""

import numpy as np
from types import SimpleNamespace

try:
    from PySAM import TroughPhysicalIph
except ImportError:
    raise ImportError("PySAM not installed. Install with: pip install nrel-pysam")


# Global state for module and data management
_active_modules = {}
_active_data = {}
_data_counter = 0
_module_counter = 0
_print_enabled = True


def ssccall(command, *args, **kwargs):
    """
    SAM ssccall wrapper supporting common operations.
    
    Supported commands:
    - load: Initialize SAM
    - unload: Cleanup SAM
    - data_create: Create a data container
    - data_free: Free a data container
    - data_set_string/number/array/matrix: Set data values
    - data_get_string/number/array/matrix: Get data values
    - module_create: Create a simulation module
    - module_exec: Execute a module
    - module_free: Free a module
    - module_log: Get module log/error messages
    - module_exec_set_print: Control print output
    """
    
    global _data_counter, _module_counter, _print_enabled
    
    if command == 'load':
        # PySAM is already loaded on import
        return True
    
    elif command == 'unload':
        # Cleanup
        _active_modules.clear()
        _active_data.clear()
        return True
    
    elif command == 'module_exec_set_print':
        # Enable/disable print output
        _print_enabled = bool(args[0]) if args else True
        return True
    
    elif command == 'data_create':
        # Create a new data container
        _data_counter += 1
        data_id = _data_counter
        _active_data[data_id] = SimpleNamespace(__data_dict={})
        return data_id
    
    elif command == 'data_free':
        # Free a data container
        data_id = args[0]
        if data_id in _active_data:
            del _active_data[data_id]
        return True
    
    elif command == 'data_set_string':
        # Set string value
        data_id, key, value = args[0], args[1], args[2]
        if data_id in _active_data:
            _active_data[data_id].__data_dict[key] = str(value)
        return True
    
    elif command == 'data_set_number':
        # Set numeric value
        data_id, key, value = args[0], args[1], args[2]
        if data_id in _active_data:
            _active_data[data_id].__data_dict[key] = float(value)
        return True
    
    elif command == 'data_set_array':
        # Set array value
        data_id, key, value = args[0], args[1], args[2]
        if data_id in _active_data:
            _active_data[data_id].__data_dict[key] = np.asarray(value, dtype=float)
        return True
    
    elif command == 'data_set_matrix':
        # Set matrix value
        data_id, key, value = args[0], args[1], args[2]
        if data_id in _active_data:
            _active_data[data_id].__data_dict[key] = np.asarray(value, dtype=float)
        return True
    
    elif command == 'data_get_string':
        # Get string value
        data_id, key = args[0], args[1]
        if data_id in _active_data and key in _active_data[data_id].__data_dict:
            return _active_data[data_id].__data_dict[key]
        return ""
    
    elif command == 'data_get_number':
        # Get numeric value
        data_id, key = args[0], args[1]
        if data_id in _active_data and key in _active_data[data_id].__data_dict:
            return float(_active_data[data_id].__data_dict[key])
        return 0.0
    
    elif command == 'data_get_array':
        # Get array value
        data_id, key = args[0], args[1]
        if data_id in _active_data and key in _active_data[data_id].__data_dict:
            return np.asarray(_active_data[data_id].__data_dict[key], dtype=float)
        return np.array([])
    
    elif command == 'module_create':
        # Create a simulation module
        module_type = args[0] if args else ""
        _module_counter += 1
        module_id = _module_counter
        
        # Create module with PySAM (if available for this type)
        try:
            if 'trough' in module_type.lower():
                module_obj = TroughPhysicalIph.default('PhysicalTroughIPHCommercial') #changed from PhysicalTroughIPHNone to PhysicalTroughIPHCommercial
            else:
                module_obj = SimpleNamespace(__module_data={}, __module_type=module_type)
        except Exception as e:
            if _print_enabled:
                print(f"Warning: Could not create PySAM module {module_type}: {e}")
            module_obj = SimpleNamespace(__module_data={}, __module_type=module_type)
        
        _active_modules[module_id] = {
            'obj': module_obj,
            'type': module_type,
            'data': None,
            'errors': []
        }
        return module_id
    
    elif command == 'module_exec':
        # Execute a module
        module_id, data_id = args[0], args[1]
        
        if module_id not in _active_modules or data_id not in _active_data:
            return False
        
        module_info = _active_modules[module_id]
        data_obj = _active_data[data_id]
        module_info['data'] = data_obj
        
        try:
            if isinstance(module_info['obj'], TroughPhysicalIph.TroughPhysicalIph):
                _set_pysam_inputs(module_info['obj'], data_obj.__data_dict)
                module_info['obj'].execute(0)
                outputs = module_info['obj'].Outputs
                for key in dir(outputs):
                    if key.startswith('_'):
                        continue
                    try:
                        value = getattr(outputs, key)
                        data_obj.__data_dict[key] = np.asarray(value, dtype=float)
                    except Exception:
                        continue
            return True
        except Exception as e:
            module_info['errors'].append(str(e))
            if _print_enabled:
                print(f"Module execution error: {e}")
            return False
    
    elif command == 'module_free':
        # Free a module
        module_id = args[0]
        if module_id in _active_modules:
            del _active_modules[module_id]
        return True
    
    elif command == 'module_log':
        # Get module error/log messages
        module_id, error_index = args[0], args[1]
        if module_id in _active_modules:
            errors = _active_modules[module_id]['errors']
            if error_index < len(errors):
                return errors[error_index]
        return ""
    
    else:
        raise NotImplementedError(f"ssccall command not implemented: {command}")


def _set_pysam_inputs(module, data_dict):
    """
    Set PySAM module inputs from a data dictionary.
    """
    for key, value in data_dict.items():
        if isinstance(value, np.ndarray):
            value = tuple(
                tuple(row) if isinstance(row, np.ndarray) else row
                for row in value
            ) if value.ndim > 1 else tuple(value)
        for group_name in dir(module):
            if group_name.startswith('_'):
                continue
            try:
                group = getattr(module, group_name)
                setattr(group, key, value)
                break
            except Exception:
                continue
