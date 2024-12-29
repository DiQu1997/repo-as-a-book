"""
Python-specific code parser implementation.
"""

import ast
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass

from .base_parser import BaseParser
from ..models.data_models import (
    ModuleElement, ClassElement, FunctionElement, DocumentationElement, FunctionCallElement
)

@dataclass
class ContextInfo:
    """Helper class to track parsing context."""
    module: Optional[ModuleElement] = None
    parent_class: Optional[ClassElement] = None
    parent_function: Optional[FunctionElement] = None
    in_async_def: bool = False

class PythonParser(BaseParser):
    """Parser for Python source code files."""
    
    language = 'Python'

    def __init__(self):
        super().__init__()

    def can_parse(self, path: Path) -> bool:
        """Check if file is a Python file."""
        return path.suffix.lower() in self.get_supported_extensions()

    def get_supported_extensions(self) -> List[str]:
        """Get supported Python file extensions."""
        return ['.py', '.pyw']

    def parse_file(self, path: Path, package_name = "", repo_root: Optional[Path] = None) -> ModuleElement:
        """
        Parse a Python source file.
        
        Args:
            path: Path to the Python file
            package_name: Name of the package containing the file
            repo_root: Root directory of the repository
            
        Returns:
            ModuleElement containing the parsed information
        """
        self.repo_root = repo_root
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse the AST
            tree = ast.parse(content)
            
            # Convert path to module name
            # Assuming path is absolute, find common project root
            # You might want to pass this as a parameter or detect it
            project_root = path.parent.parent  # Example: adjust based on your needs
            
            try:
                relative_path = path.relative_to(project_root)
                module_name = str(relative_path.parent / relative_path.stem)  # Include parent dirs
                module_name = module_name.replace('/', '.').replace('\\', '.')
                parent_module = str(relative_path.parent).replace('/', '.').replace('\\', '.')
                if parent_module == '.':
                    parent_module = ''
            except ValueError:
                # Fallback if path is not relative to project_root
                module_name = path.stem
                parent_module = ''
            
            if package_name:
                module_name = f"{package_name}.{module_name}"
            
            module = ModuleElement(
                name=module_name,  # Will look like 'package.subpackage.module'
                path=path,
                language=self.language,
                classes=[],
                functions=[],
                imports=[],
                imports_mapping=dict(),
                documentation=None,
                body=content
            )
            
            # Create initial context
            context = ContextInfo(module=module)
            
            # Extract module docstring
            module.documentation = self._parse_docstring(tree)
            # Parse all module elements
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    module.classes.append(self._parse_class(path, node, context, module_name))
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    module.functions.append(self._parse_function(path, node, context, module_name))
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports = self._parse_imports(node, parent_module)
                    module.imports.extend(imports.keys())
                    module.imports_mapping.update(imports)
            return module
            
        except Exception as e:
            self.logger.error(f"Error parsing {path}: {e}")
            return self._create_error_module(path, e)

    def _parse_class(self, path: Path, node: ast.ClassDef, context: ContextInfo, parent_name: str) -> ClassElement:
        """Parse a class definition."""
        # Build qualified name based on context
        qualified_name = [parent_name, f"{node.name}"]
        
        # Create class element first
        class_element = ClassElement(
            name=".".join(qualified_name),  # <parent_name>.<parent_name>....<class_name>
            path=path,
            documentation=None,
            methods=[],
            base_classes=[],
            attributes=dict(),
            decorators=[],
            start_line=node.lineno,
            end_line=node.end_lineno,
            module=context.module
        )
        
        # Create new context for class contents
        class_context = ContextInfo(
            module=context.module,
            parent_class=class_element,
            parent_function=context.parent_function,
            in_async_def=context.in_async_def
        )
        
        # Get docstring and decorators
        class_element.documentation = self._parse_docstring(node)
        class_element.decorators = self._parse_decorators(node)
        
        # Parse methods and nested classes
        for body_node in node.body:
            if isinstance(body_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                class_element.methods.append(self._parse_function(path, body_node, class_context, class_element.name))
            elif isinstance(body_node, ast.ClassDef):
                class_element.inner_classes.append(self._parse_class(path, body_node, class_context, class_element.name))
            elif isinstance(body_node, ast.Assign):
                # Class attributes
                for target in body_node.targets:
                    if isinstance(target, ast.Name):
                        class_element.attributes[target.id] = self._get_attribute_type(body_node.value)
                        
        class_element.base_classes = [self._get_name(base) for base in node.bases]
        
        return class_element

    def _parse_decorators(self, node: Union[ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef]) -> List[str]:
        """
        Parse decorators from a class or function node.
        
        Args:
            node: AST node for class or function
            
        Returns:
            List of decorator strings
        """
        decorators = []
        for decorator in node.decorator_list:
            try:
                if isinstance(decorator, ast.Call):
                    # Handle decorators with arguments: @decorator(arg1, arg2)
                    decorator_name = self._get_decorator_name(decorator.func)
                    args = []
                    
                    # Process positional arguments
                    for arg in decorator.args:
                        if isinstance(arg, ast.Constant):
                            args.append(repr(arg.value))
                        elif isinstance(arg, ast.Name):
                            args.append(arg.id)
                        else:
                            args.append(ast.unparse(arg))
                    
                    # Process keyword arguments
                    for keyword in decorator.keywords:
                        if isinstance(keyword.value, ast.Constant):
                            args.append(f"{keyword.arg}={repr(keyword.value.value)}")
                        else:
                            args.append(f"{keyword.arg}={ast.unparse(keyword.value)}")
                    
                    decorators.append(f"@{decorator_name}({', '.join(args)})")
                
                elif isinstance(decorator, ast.Attribute):
                    # Handle decorators with attributes: @module.decorator
                    decorators.append(f"@{self._get_decorator_name(decorator)}")
                
                elif isinstance(decorator, ast.Name):
                    # Handle simple decorators: @decorator
                    decorators.append(f"@{decorator.id}")
                
                else:
                    # Handle any other decorator forms
                    decorators.append(f"@{ast.unparse(decorator)}")
                    
            except Exception as e:
                self.logger.warning(f"Error parsing decorator: {e}")
                decorators.append(f"@<error_parsing_decorator>")
        
        return decorators

    def _get_decorator_name(self, node: Union[ast.Name, ast.Attribute]) -> str:
        """
        Get the full name of a decorator node.
        
        Args:
            node: AST node representing the decorator name
            
        Returns:
            Full decorator name as a string
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_decorator_name(node.value)}.{node.attr}"
        return ast.unparse(node)

    def _parse_function(self, path: Path, node: Union[ast.FunctionDef, ast.AsyncFunctionDef], context: ContextInfo, parent_name: str) -> FunctionElement:
        """Parse a function or method definition."""
        # Get parameters and return type
        params = []
        for arg in node.args.args:
            param_type = self._get_annotation_type(arg.annotation)
            params.append(f"{arg.arg}: {param_type}")
        return_type = self._get_annotation_type(node.returns)
        
        # Build simple name for symbol table lookup
        simple_name = [parent_name, node.name]
        
        # Build full qualified name with signature
        full_qualified_name = [parent_name, f"{node.name}({', '.join(params)}) -> {return_type}"]
        
        # Create function element
        function_element = FunctionElement(
            name=".".join(simple_name),  # Simple name for symbol table lookup
            path=path,
            module=context.module,
            documentation=None,
            parameters=params,
            return_type=return_type,
            decorators=[],
            complexity=None,
            start_line=node.lineno,
            end_line=node.end_lineno,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            qualified_name=".".join(full_qualified_name)  # Full name with signature
        )
        
        # Create new context for function contents
        function_context = ContextInfo(
            module=context.module,
            parent_class=context.parent_class,
            parent_function=function_element,
            in_async_def=isinstance(node, ast.AsyncFunctionDef)
        )
        
        # Get docstring and decorators
        function_element.documentation = self._parse_docstring(node)
        function_element.decorators = self._parse_decorators(node)
        
        # Calculate complexity
        function_element.complexity = self._calculate_complexity(node)
        
        return function_element

    def _parse_imports(self, node: Union[ast.Import, ast.ImportFrom], parent_module: str = '') -> Dict[str, str]:
        """Parse import statements and build a mapping."""
        imports_mapping = dict()
        top_level = parent_module.split('.')[0] if parent_module else ''

        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                asname = alias.asname if alias.asname else alias.name.split('.')[0]
                if parent_module and not name.startswith('.'):
                    if not name.startswith(top_level) and self._is_local_module(name):
                        name = f"{top_level}.{name}"
                imports_mapping[asname] = name
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            
            # Handle relative imports
            if node.level > 0:  # This is a relative import
                if parent_module:
                    parts = parent_module.split('.')
                    # For level=1 (current directory), we want all parts
                    # For level=2 (parent directory), we want all parts except last one
                    base_path = parts[:-node.level] if node.level > 1 else parts
                    module = '.'.join(base_path + ([module] if module else []))
            else:
                # For absolute imports
                if module == top_level:
                    # Case: from model_parallel import utils
                    for alias in node.names:
                        name = alias.name
                        asname = alias.asname if alias.asname else name
                        full_name = f"{module}.{name}"
                        imports_mapping[asname] = full_name
                    return imports_mapping
                elif module.startswith(top_level + '.'):
                    # Case: from model_parallel.utils import split_tensor
                    pass  # Keep the module name as is
                elif parent_module and not module.startswith(top_level):
                    # Other imports - prepend top-level module if needed
                    if self._is_local_module(module):
                        module = f"{top_level}.{module}"
            
            for alias in node.names:
                name = alias.name
                asname = alias.asname if alias.asname else name
                full_name = f"{module}.{name}" if module else name
                imports_mapping[asname] = full_name
        
        return imports_mapping

    def _is_local_module(self, module_name: str) -> bool:
        """Check if a module is local to the repository."""
        if not self.repo_root:
            return False
            
        # Convert module name to potential file paths
        possible_paths = [
            self.repo_root / module_name.replace('.', '/'),  # as directory
            self.repo_root / f"{module_name.replace('.', '/')}.py",  # as file
            self.repo_root / f"{module_name.replace('.', '/')}/__init__.py"  # as package
        ]
        
        return any(path.exists() for path in possible_paths)

    def _parse_docstring(self, node: ast.AST) -> Optional[DocumentationElement]:
        """Extract docstring from an AST node."""
        docstring = ast.get_docstring(node)
        if docstring:
            return DocumentationElement(
                content=docstring,
                path=str(getattr(node, 'lineno', 0)),
                line_number=getattr(node, 'lineno', 0),
                type='docstring'
            )
        return None

    def _calculate_complexity(self, node: ast.AST) -> int:
        """
        Calculate cyclomatic complexity of a function.
        Very basic implementation - counts branches.
        """
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            # Count branches
            if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor,
                                ast.ExceptHandler, ast.With, ast.AsyncWith)):
                complexity += 1
            # Count boolean operations
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
                
        return complexity

    def _get_annotation_type(self, node: Optional[ast.AST]) -> str:
        """Convert annotation AST node to string representation."""
        if node is None:
            return 'Any'
        return ast.unparse(node)

    def _get_attribute_type(self, node: ast.AST) -> str:
        """Get the type of a class attribute from its value."""
        if isinstance(node, ast.Constant):
            return type(node.value).__name__
        elif isinstance(node, ast.List):
            return 'List'
        elif isinstance(node, ast.Dict):
            return 'Dict'
        elif isinstance(node, ast.Set):
            return 'Set'
        return 'Any'

    def _get_name(self, node: ast.AST) -> str:
        """Convert AST name node to string."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return ast.unparse(node)

class PythonFunctionCallVisitor(ast.NodeVisitor):
    def __init__(self, imports_mapping):
        self.imports_mapping = imports_mapping
        self.calls = []
        self.current_scope = []  # Track nested function/class scopes

    def visit_Call(self, node):
        function_name = self._get_function_name(node.func)
        if function_name:
            # Handle fully qualified names (e.g., module.submodule.function)
            parts = function_name.split('.')
            module_name = self._resolve_module(parts[0])
            
            # If it's a method call on an imported object
            if module_name and len(parts) > 1:
                module_name = f"{module_name}.{'.'.join(parts[1:-1])}"
            self.calls.append(FunctionCallElement(
                name=function_name,  # Just the function name
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
            # Handle cases where value might be a complex expression
            return node.attr
        return None

    def _resolve_module(self, first_part):
        # Direct import mapping
        if first_part in self.imports_mapping:
            return self.imports_mapping[first_part]
        
        # Check for nested imports (from x import y as z)
        for import_alias, full_path in self.imports_mapping.items():
            if first_part == import_alias.split('.')[-1]:
                return full_path
                
        # Could be built-in, local function, or class method
        if first_part in __builtins__:
            return 'builtins'
        return None

    # Track scope for better context
    def visit_FunctionDef(self, node):
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()

    def visit_ClassDef(self, node):
        self.current_scope.append(node.name)
        self.generic_visit(node)
        self.current_scope.pop()