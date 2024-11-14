"""
Python-specific code parser implementation.
"""

import ast
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from dataclasses import dataclass

from .base_parser import BaseParser
from ..models.data_models import (
    ModuleElement, ClassElement, FunctionElement, DocumentationElement
)

@dataclass
class ContextInfo:
    """Helper class to track parsing context."""
    current_class: Optional[str] = None
    current_function: Optional[str] = None
    in_async_def: bool = False

class PythonParser(BaseParser):
    """Parser for Python source code files."""
    
    language = 'Python'

    def __init__(self):
        super().__init__()
        self.context = ContextInfo()

    def can_parse(self, path: Path) -> bool:
        """Check if file is a Python file."""
        return path.suffix.lower() in self.get_supported_extensions()

    def get_supported_extensions(self) -> List[str]:
        """Get supported Python file extensions."""
        return ['.py', '.pyw']

    def parse_file(self, path: Path) -> ModuleElement:
        """
        Parse a Python source file.
        
        Args:
            path: Path to the Python file
            
        Returns:
            ModuleElement containing the parsed information
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Parse the AST
            tree = ast.parse(content)
            
            # Extract module docstring
            module_doc = self._parse_docstring(tree)
            
            # Parse all module elements
            classes = []
            functions = []
            imports = []
            
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(self._parse_class(path, node))
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append(self._parse_function(path, node))
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    imports.extend(self._parse_imports(node))
                    
            return ModuleElement(
                name=str(path),
                path=str(path),
                language=self.language,
                classes=classes,
                functions=functions,
                imports=imports,
                documentation=module_doc
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing {path}: {e}")
            return self._create_error_module(path, e)

    def _parse_class(self, path: Path, node: ast.ClassDef) -> ClassElement:
        """Parse a class definition."""
        self.context.current_class = node.name
        
        try:
            # Get docstring and decorators
            docstring = self._parse_docstring(node)
            decorators = self._parse_decorators(node)
            
            # Parse methods and nested classes
            methods = []
            nested_classes = []
            attributes = {}
            
            for body_node in node.body:
                if isinstance(body_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append(self._parse_function(path, body_node))
                elif isinstance(body_node, ast.ClassDef):
                    nested_classes.append(self._parse_class(path, body_node))
                elif isinstance(body_node, ast.Assign):
                    # Class attributes
                    for target in body_node.targets:
                        if isinstance(target, ast.Name):
                            attributes[target.id] = self._get_attribute_type(body_node.value)
                            
            return ClassElement(
                name=f"{path}:{node.name}",
                path=str(path),
                documentation=docstring,
                methods=methods,
                base_classes=[self._get_name(base) for base in node.bases],
                attributes=attributes,
                decorators=decorators,
                start_line=node.lineno,
                end_line=node.end_lineno
            )
            
        finally:
            self.context.current_class = None

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

    def _parse_function(self, path: Path, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> FunctionElement:
        """Parse a function or method definition."""
        self.context.current_function = node.name
        self.context.in_async_def = isinstance(node, ast.AsyncFunctionDef)
        
        try:
            # Get docstring and decorators
            docstring = self._parse_docstring(node)
            decorators = self._parse_decorators(node)
            
            # Get parameters
            parameters = []
            for arg in node.args.args:
                param_type = self._get_annotation_type(arg.annotation)
                parameters.append(f"{arg.arg}: {param_type}")
                
            # Get return type
            return_type = self._get_annotation_type(node.returns)
            
            # Calculate complexity (simple version)
            complexity = self._calculate_complexity(node)
            
            return FunctionElement(
                name=f"{path}:{node.name}({', '.join(parameters)}) -> {return_type} : {node.lineno}",
                path=str(path),
                documentation=docstring,
                parameters=parameters,
                return_type=return_type,
                decorators=decorators,
                complexity=complexity,
                start_line=node.lineno,
                end_line=node.end_lineno,
                is_async=self.context.in_async_def
            )
            
        finally:
            self.context.current_function = None
            self.context.in_async_def = False

    def _parse_imports(self, node: Union[ast.Import, ast.ImportFrom]) -> List[str]:
        """Parse import statements."""
        imports = []
        if isinstance(node, ast.Import):
            for name in node.names:
                imports.append(name.name)
        else:  # ImportFrom
            module = node.module or ''
            for name in node.names:
                imports.append(f"from {module} import {name.name}")
        return imports

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