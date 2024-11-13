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
        assert isinstance(parser.context, ContextInfo)
        assert parser.context.current_class is None
        assert parser.context.current_function is None
        assert parser.context.in_async_def is False

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
        func = parser._parse_function(func_node)
        
        assert isinstance(func, FunctionElement)
        assert func.name == 'test_func'
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
        cls = parser._parse_class(class_node)
        
        assert isinstance(cls, ClassElement)
        assert cls.name == 'TestClass'
        assert cls.base_classes == ['BaseClass']
        assert cls.decorators == ['@decorator']
        assert len(cls.methods) == 1
        assert cls.methods[0].name == 'method'
        assert 'class_attr' in cls.attributes
        assert isinstance(cls.documentation, DocumentationElement)
        assert cls.documentation.content == "Test class"

    def test_parse_imports(self, parser):
        """Test import statement parsing"""
        code = '''
        import os
        from pathlib import Path
        from typing import List, Optional
        '''
        tree = ast.parse(dedent(code))
        imports = []
        for node in tree.body:
            imports.extend(parser._parse_imports(node))
            
        assert 'os' in imports
        assert 'from pathlib import Path' in imports
        assert 'from typing import List' in imports
        assert 'from typing import Optional' in imports

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
        assert module.name == 'test'
        assert module.language == 'Python'
        assert len(module.classes) == 1
        assert len(module.functions) == 1
        assert len(module.imports) == 1
        assert isinstance(module.documentation, DocumentationElement)
        assert module.documentation.content == "Module docstring"

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
