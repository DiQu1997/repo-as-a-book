import ast
from parser_engine.models.data_models import FunctionCallElement

class FunctionCallCollector(ast.NodeVisitor):
    def __init__(self, imports_mapping):
        self.imports_mapping = imports_mapping
        self.calls = []

    def visit_Call(self, node):
        function_name = self._get_function_name(node.func)
        if function_name:
            module_name = self._resolve_module(function_name)
            self.calls.append(FunctionCallElement(
                function_name=function_name,
                module_name=module_name,
                line_number=node.lineno
            ))
        self.generic_visit(node)

    def _get_function_name(self, node):
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value = self._get_function_name(node.value)
            if value:
                return f"{value}.{node.attr}"
        return None

    def _resolve_module(self, function_name):
        parts = function_name.split('.')
        first_part = parts[0]
        if first_part in self.imports_mapping:
            return self.imports_mapping[first_part]
        else:
            # Could be built-in or local function
            return None