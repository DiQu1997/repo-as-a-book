import pytest
from pathlib import Path
from unittest.mock import Mock, patch
import ast
from textwrap import dedent

from ..language_parsers.python_parser import PythonParser, ContextInfo
from ..models.data_models import ModuleElement, ClassElement, FunctionElement, DocumentationElement

class TestPythonParser:
    @pytest.fixture
    def parser(self):
        return PythonParser()

    def test_initialization(self, parser):
        """Test parser initialization"""
        assert parser.language == 'Python'

    def test_can_parse(self, parser):
        """Test file extension detection"""
        assert parser.can_parse(Path('test.py'))
        assert parser.can_parse(Path('test.pyw'))
        assert not parser.can_parse(Path('test.js'))
        assert not parser.can_parse(Path('test.txt'))

    def test_supported_extensions(self, parser):
        """Test supported extensions list"""
        extensions = parser.get_supported_extensions()
        assert '.py' in extensions
        assert '.pyw' in extensions
        assert len(extensions) == 2

    def test_parse_docstring(self, parser):
        """Test docstring parsing"""
        code = '''
        """Module docstring."""
        def test():
            """Function docstring."""
            pass
        '''
        tree = ast.parse(dedent(code))
        doc = parser._parse_docstring(tree)
        assert isinstance(doc, DocumentationElement)
        assert doc.content == "Module docstring."
        assert doc.type == 'docstring'

    def test_parse_function(self, parser):
        """Test function parsing"""
        code = '''
        @decorator
        async def test_func(param1: str, param2: int = 0) -> bool:
            """Test function"""
            if True:
                return True
            return False
        '''
        tree = ast.parse(dedent(code))
        func_node = tree.body[0]
        module = ModuleElement(name='test', path=Path('test.py'), language = 'Python')
        func = parser._parse_function(Path('test.py'), func_node, ContextInfo(module=module), str(module.name))
        
        assert isinstance(func, FunctionElement)
        assert func.name == 'test.test_func'
        assert func.qualified_name == 'test.test_func(param1: str, param2: int) -> bool'
        assert func.is_async
        assert func.parameters == ['param1: str', 'param2: int']
        assert func.return_type == 'bool'
        assert func.decorators == ['@decorator']
        assert func.complexity > 1  # Should count if statement
        assert isinstance(func.documentation, DocumentationElement)
        assert func.documentation.content == "Test function"

    def test_parse_class(self, parser):
        """Test class parsing"""
        code = '''
        @decorator
        class TestClass(BaseClass):
            """Test class"""
            class_attr = "test"
            
            def method(self):
                pass
                
            class NestedClass:
                pass
        '''
        tree = ast.parse(dedent(code))
        class_node = tree.body[0]
        module = ModuleElement(name='test', path=Path('test.py'), language = 'Python')
        cls = parser._parse_class(Path('test.py'), class_node, ContextInfo(module=module), str(module.name))
        
        assert isinstance(cls, ClassElement)
        assert cls.name == 'test.TestClass'
        assert cls.base_classes == ['BaseClass']
        assert cls.decorators == ['@decorator']
        assert len(cls.methods) == 1
        assert cls.methods[0].name == 'test.TestClass.method'
        assert cls.methods[0].qualified_name == 'test.TestClass.method(self: Any) -> Any'
        assert 'class_attr' in cls.attributes
        assert isinstance(cls.documentation, DocumentationElement)
        assert cls.documentation.content == "Test class"

    def test_parse_file(self, parser, tmp_path):
        """Test complete file parsing"""
        test_file = tmp_path / "test.py"
        code = '''
        """Module docstring"""
        from typing import List
        
        class TestClass:
            """Test class"""
            def method(self):
                pass
                
        def test_func():
            """Test function"""
            pass
        '''
        test_file.write_text(dedent(code))
        
        module = parser.parse_file(test_file)
        
        assert isinstance(module, ModuleElement)
        assert module.name.endswith('test')
        assert module.language == 'Python'
        assert len(module.classes) == 1
        assert len(module.functions) == 1
        assert len(module.imports) == 1
        assert isinstance(module.documentation, DocumentationElement)
        assert module.documentation.content == "Module docstring"
        assert module.classes[0].name == f'{module.name}.TestClass'
        assert module.functions[0].name == f'{module.name}.test_func'
        assert module.functions[0].qualified_name == f'{module.name}.test_func() -> Any'
        assert module.classes[0].methods[0].name == f'{module.name}.TestClass.method'
        assert module.classes[0].methods[0].qualified_name == f'{module.name}.TestClass.method(self: Any) -> Any'
        assert module.imports[0] == 'List'
        assert module.imports_mapping['List'] == 'typing.List'

    def test_error_handling(self, parser, tmp_path):
        """Test error handling for invalid Python code"""
        test_file = tmp_path / "invalid.py"
        test_file.write_text("this is not valid python code )")
        
        module = parser.parse_file(test_file)
        assert isinstance(module, ModuleElement)
        assert module.name == 'invalid.py'
        assert not module.classes
        assert not module.functions

    def test_complexity_calculation(self, parser):
        """Test cyclomatic complexity calculation"""
        code = '''
        def complex_func():
            if True:
                while True:
                    if False:
                        pass
                    elif True:
                        pass
            try:
                for i in range(10):
                    pass
            except:
                pass
        '''
        tree = ast.parse(dedent(code))
        func_node = tree.body[0]
        complexity = parser._calculate_complexity(func_node)
        assert complexity > 1  # Should count multiple branches

    def test_parse_imports(self, parser):
        """Test various import statement parsing scenarios"""
        test_cases = [
            # Simple import
            (
                "import math",
                "",
                {"math": "math"}
            ),
            # Import with alias
            (
                "import math as m",
                "",
                {"m": "math"}
            ),
            # Multiple imports
            (
                "import os, sys as system",
                "",
                {"os": "os", "system": "sys"}
            ),
            # From import
            (
                "from os import path",
                "",
                {"path": "os.path"}
            ),
            # From import with alias
            (
                "from os import path as p",
                "",
                {"p": "os.path"}
            ),
            # Multiple from imports
            (
                "from os import path, getcwd as get_dir",
                "",
                {"path": "os.path", "get_dir": "os.getcwd"}
            ),
            # Relative imports
            (
                "from . import sibling",
                "pkg.parent",
                {"sibling": "pkg.parent.sibling"}
            ),
            (
                "from .. import uncle",
                "pkg.parent.child",
                {"uncle": "pkg.uncle"}
            ),
            (
                "from .cousin import func",
                "pkg.parent",
                {"func": "pkg.parent.cousin.func"}
            ),
            # Nested imports
            (
                "import pkg.subpkg.module",
                "",
                {"pkg": "pkg.subpkg.module"}
            ),
            # Import all
            (
                "from os import *",
                "",
                {"*": "os.*"}
            ),
            # Empty from import
            (
                "from . import module",
                "pkg.parent",
                {"module": "pkg.parent.module"}
            ),
            
            # Same function name from different modules with aliases
            (
                dedent('''
                    from os.path import basename as os_basename
                    from ntpath import basename as nt_basename
                '''),
                "",
                {"os_basename": "os.path.basename", "nt_basename": "ntpath.basename"}
            ),
        ]

        for import_str, parent_module, expected in test_cases:
            # Parse all import statements in the string
            nodes = ast.parse(import_str).body
            result = {}
            # Process each import statement and merge results
            for node in nodes:
                result.update(parser._parse_imports(node, parent_module))
            assert result == expected, f"Failed for import: {import_str}"

    def test_parse_imports_with_local_modules(self, parser, tmp_path):
        """Test import parsing with local module resolution"""
        # Setup mock repository structure
        mock_project = tmp_path / "myproject"
        mock_project.mkdir()
        
        # Create package structure
        (mock_project / "__init__.py").touch()
        (mock_project / "utils").mkdir()
        (mock_project / "utils/__init__.py").touch()
        (mock_project / "utils/helpers.py").touch()
        (mock_project / "core").mkdir()
        (mock_project / "core/__init__.py").touch()
        
        parser.repo_root = tmp_path

        test_cases = [
            # Local package imports
            (
                "from myproject.utils import helpers",
                "myproject.core",
                {"helpers": "myproject.utils.helpers"}
            ),
            # Relative imports within package
            (
                "from ..utils import helpers",
                "myproject.core.submodule",
                {"helpers": "myproject.utils.helpers"}
            ),
            # Import from sibling module
            (
                "from .utils import helpers",
                "myproject",
                {"helpers": "myproject.utils.helpers"}
            ),
            # Direct local package import
            (
                "import myproject.utils.helpers",
                "",
                {"myproject": "myproject.utils.helpers"}
            ),
            # Import with alias
            (
                "from myproject.utils.helpers import some_func as helper",
                "myproject.core",
                {"helper": "myproject.utils.helpers.some_func"}
            ),
        ]

        for import_str, parent_module, expected in test_cases:
            node = ast.parse(import_str).body[0]
            result = parser._parse_imports(node, parent_module)
            assert result == expected, f"Failed for import: {import_str}"
