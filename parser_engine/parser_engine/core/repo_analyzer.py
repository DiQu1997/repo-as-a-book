from typing import List, Dict, Union, Tuple
from parser_engine.models.data_models import ModuleElement, FunctionElement, ClassElement, FunctionCallElement
from typing import Optional
from parser_engine.language_parsers.python_parser import PythonFunctionCallVisitor
import ast

class RepoIndexer:
    def __init__(self, modules: List[ModuleElement]):
        self.modules = modules
        self.symbol_table: Dict[str, Union[FunctionElement, ClassElement]] = {}
        self.module_name_map: Dict[str, ModuleElement] = {}
        self._builtin_functions_set = set(__builtins__.keys())
    
    def index_repository(self):
        self._build_module_name_map()
        self._build_symbol_table()
        self._resolve_function_calls()
    
    def _build_module_name_map(self):
        for module in self.modules:
            self.module_name_map[module.name] = module

    def _build_symbol_table(self):
        for module in self.modules:
            module_prefix = module.name
            # Index classes
            for class_element in module.classes:
                fq_class_name = f"{class_element.name}"
                class_element.qualified_name = fq_class_name
                self.symbol_table[fq_class_name] = class_element
                # Index methods
                for method in class_element.methods:
                    fq_method_name = f"{method.name}"
                    method.qualified_name = fq_method_name
                    self.symbol_table[fq_method_name] = method
            # Index functions
            for function_element in module.functions:
                fq_function_name = f"{function_element.name}"
                function_element.qualified_name = fq_function_name
                self.symbol_table[fq_function_name] = function_element

    def _resolve_function_calls(self):
        for module in self.modules:
            for function in module.functions:
                self._resolve_function_calls_in_function(function, module)
            for class_element in module.classes:
                for method in class_element.methods:
                    self._resolve_function_calls_in_function(method, module)
    
    def _resolve_function_calls_in_function(self, function: FunctionElement, module: ModuleElement):
        # Extract function calls
        print(f"extracting function calls in {function.qualified_name}")
        function.function_calls = self._extract_function_calls(function, module)
        print(f"    extracted function calls internally: {function.function_calls}")
        for call in function.function_calls:
            resolved_name = self._resolve_call(call.name, function, module)
            print(f"        call: {call.name}, resolved call: {resolved_name}")
            call.resolved_name = resolved_name  # Add this field to FunctionCallElement
    
    def _extract_function_calls(self, function: FunctionElement, module: ModuleElement) -> List[FunctionCallElement]:
        """Extract function calls from a function's AST body.
    
        Args:
            function: The FunctionElement containing the function's AST body
        
        Returns:
            List of FunctionCallElement representing all function calls
        """
        visitor = PythonFunctionCallVisitor(module.imports_mapping)
        # Visit all nodes in function body
        try:
            # Extract just the function's source by line numbers
            module_lines = module.body.splitlines()
            function_source = '\n'.join(module_lines[function.start_line-1:function.end_line])
            
            # Parse and visit just the function source
            function_tree = ast.parse(function_source)
            visitor.visit(function_tree)
            return visitor.calls
            
        except Exception as e:
            return []
        

    def _resolve_call(self, function_name: str, function: FunctionElement, module: ModuleElement) -> Optional[str]:
        
        if '.' in function_name:
            module_part, func_part = function_name.split('.', 1)
            # Check if the module part is in imports_mapping (handles case: from A import B, then B.F)
            if module_part in module.imports_mapping:
                base_module = module.imports_mapping[module_part]
                return f"{base_module}.{func_part}"
            return function_name  # Return as-is for direct module imports (import A, then A.B)

        # 2. Check if the function is a built-in function
        if self._is_builtin_function(function_name):
            return function_name  # Indicate that it's a built-in function
        
        # 2. Check local scope (within the same module)
        local_name = f"{module.name}.{function_name}"
        if local_name in self.symbol_table:
            return local_name
        
        # 3. Check imports mapping
        print(f"module.imports_mapping: {module.imports_mapping}")
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