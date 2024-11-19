from typing import List, Dict, Union
from parser_engine.models.data_models import ModuleElement, FunctionElement, ClassElement
from typing import Optional

class RepoIndexer:
    def __init__(self, modules: List[ModuleElement]):
        self.modules = modules
        self.symbol_table: Dict[str, Union[FunctionElement, ClassElement]] = {}
        self.module_name_map: Dict[str, ModuleElement] = {}
        self._builtin_functions_set = set(__builtins__.keys())
    
    def index_repository(self):
        self._build_module_name_map()
        self._build_symbol_table()
        self._resolve_imports()
        self._resolve_function_calls()
    
    def _build_module_name_map(self):
        for module in self.modules:
            self.module_name_map[module.name] = module

    def _build_symbol_table(self):
        for module in self.modules:
            module_prefix = module.name
            # Index classes
            for class_element in module.classes:
                fq_class_name = f"{module_prefix}.{class_element.name}"
                class_element.qualified_name = fq_class_name
                self.symbol_table[fq_class_name] = class_element
                # Index methods
                for method in class_element.methods:
                    fq_method_name = f"{fq_class_name}.{method.name}"
                    method.qualified_name = fq_method_name
                    self.symbol_table[fq_method_name] = method
            # Index functions
            for function_element in module.functions:
                fq_function_name = f"{module_prefix}.{function_element.name}"
                function_element.qualified_name = fq_function_name
                self.symbol_table[fq_function_name] = function_element
    
    def _resolve_imports(self):
        for module in self.modules:
            imports_mapping = {}
            for import_name, import_source in module.imports_mapping.items():
                resolved_source = self._resolve_import_source(import_source, module)
                if resolved_source:
                    imports_mapping[import_name] = resolved_source
            module.imports_mapping = imports_mapping  # Update with resolved sources
    
    def _resolve_import_source(self, import_source: str, current_module: ModuleElement) -> Optional[str]:
        # Handle absolute and relative imports
        if import_source in self.module_name_map:
            return import_source  # Absolute import resolved
        # Handle relative imports
        if import_source.startswith('.'):
            # Calculate the absolute module name
            module_name = self._resolve_relative_import(current_module.name, import_source)
            if module_name in self.module_name_map:
                return module_name
        # Import source not found in repository
        return None

    def _resolve_relative_import(self, current_module_name: str, relative_import: str) -> str:
        # Count the number of dots to determine the level
        level = len(relative_import) - len(relative_import.lstrip('.'))
        # Get the current module's package path
        parts = current_module_name.split('.')
        if level > len(parts):
            raise ImportError(f"Cannot perform relative import beyond top-level package in {current_module_name}")
        base = parts[:-level]
        module_suffix = relative_import.lstrip('.')
        if module_suffix:
            base.append(module_suffix)
        return '.'.join(base)

    def _resolve_function_calls(self):
        for module in self.modules:
            for function in module.functions:
                self._resolve_function_calls_in_function(function, module)
            for class_element in module.classes:
                for method in class_element.methods:
                    self._resolve_function_calls_in_function(method, module)
    
    def _resolve_function_calls_in_function(self, function: FunctionElement, module: ModuleElement):
        for call in function.function_calls:
            resolved_name = self._resolve_call(call.function_name, function, module)
            call.resolved_name = resolved_name  # Add this field to FunctionCallElement
    
    def _resolve_call(self, function_name: str, function: FunctionElement, module: ModuleElement) -> Optional[str]:
        # 1. Check if the function is a built-in function
        if self._is_builtin_function(function_name):
            return function_name  # Indicate that it's a built-in function
        
        # 2. Check local scope (within the same module)
        local_name = f"{module.name}.{function_name}"
        if local_name in self.symbol_table:
            return local_name
        
        # 3. Check imports mapping
        if function_name in module.imports_mapping:
            imported_module_name = module.imports_mapping[function_name]
            imported_name = f"{imported_module_name}.{function_name}"
            if imported_name in self.symbol_table:
                return imported_name
        
        # 4. Check global symbol table
        if function_name in self.symbol_table:
            return function_name  # Fully qualified name matches
        
        # 5. Unable to resolve
        return None
    
    def _is_builtin_function(self, function_name: str) -> bool:
        # Use Python's built-in function list or a predefined set
        return function_name in self._builtin_functions_set