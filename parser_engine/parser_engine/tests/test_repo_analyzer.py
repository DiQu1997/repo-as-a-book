import pytest
from pathlib import Path
from parser_engine.core.repo_analyzer import RepoIndexer
from parser_engine.models.data_models import (
    ModuleElement, ClassElement, FunctionElement, FunctionCallElement
)

class TestRepoIndexer:
    @pytest.fixture
    def sample_modules(self):
        """Create sample modules for testing with corrected types"""
        # Module 1: Add missing fields and correct types
        module1 = ModuleElement(
            name="module1",
            path=Path("module1.py"),
            language="Python",
            functions=[
                FunctionElement(
                    name="function1",
                    path=Path("module1.py"),
                    start_line=1,
                    end_line=5,
                    # Missing fields from data_models.py:
                    module=None,
                    documentation=None,
                    parameters=[],
                    return_type=None,
                    decorators=[],
                    complexity=None,
                    is_async=False,
                    function_calls=[],
                    qualified_name=None
                )
            ],
            classes=[],
            imports=[],
            imports_mapping={},
            # Missing fields from data_models.py:
            documentation=None,
            size_bytes=0,
            lines_of_code=0,
            error=None,
            body="def function1():\n    print('hello')"
        )

        # Module 2: Add missing fields and correct types
        module2 = ModuleElement(
            name="module2",
            path=Path("module2.py"),
            language="Python",
            functions=[],
            classes=[
                ClassElement(
                    name="Class1",
                    path=Path("module2.py"),
                    start_line=1,
                    end_line=10,
                    # Missing fields from data_models.py:
                    module=None,
                    documentation=None,
                    methods=[
                        FunctionElement(
                            name="method1",
                            path=Path("module2.py"),
                            start_line=2,
                            end_line=5,
                            module=None,
                            documentation=None,
                            parameters=[],
                            return_type=None,
                            decorators=[],
                            complexity=None,
                            is_async=False,
                            function_calls=[],
                            qualified_name=None
                        )
                    ],
                    base_classes=[],
                    attributes={},
                    decorators=[],
                    inner_classes=[],
                    qualified_name=None
                )
            ],
            imports=["module1"],
            imports_mapping={"function1": "module1.function1"},
            # Missing fields from data_models.py:
            documentation=None,
            size_bytes=0,
            lines_of_code=0,
            error=None,
            body="import module1\nclass Class1:\n    def method1(self):\n        module1.function1()"
        )

        return [module1, module2]

    def test_init(self, sample_modules):
        indexer = RepoIndexer(sample_modules)
        assert indexer.modules == sample_modules
        assert isinstance(indexer.symbol_table, dict)
        assert isinstance(indexer.module_name_map, dict)
        assert isinstance(indexer._builtin_functions_set, set)

    def test_build_module_name_map(self, sample_modules):
        indexer = RepoIndexer(sample_modules)
        indexer._build_module_name_map()
        
        assert len(indexer.module_name_map) == 2
        assert indexer.module_name_map["module1"] == sample_modules[0]
        assert indexer.module_name_map["module2"] == sample_modules[1]

    def test_build_symbol_table(self, sample_modules):
        indexer = RepoIndexer(sample_modules)
        indexer._build_module_name_map()
        indexer._build_symbol_table()

        # Check if all functions and classes are in symbol table
        assert "function1" in indexer.symbol_table
        assert "Class1" in indexer.symbol_table
        assert "method1" in indexer.symbol_table

        # Verify qualified names
        assert indexer.symbol_table["function1"].qualified_name == "function1"
        assert indexer.symbol_table["Class1"].qualified_name == "Class1"
        assert indexer.symbol_table["method1"].qualified_name == "method1"

    def test_resolve_function_calls(self, sample_modules):
        indexer = RepoIndexer(sample_modules)
        indexer.index_repository()

        # Get the method that contains the function call
        class1 = sample_modules[1].classes[0]
        method1 = class1.methods[0]

        # Check if function calls were extracted and resolved
        assert len(method1.function_calls) == 1
        call = method1.function_calls[0]
        print(call)
        assert call.name == "module1.function1"
        assert call.resolved_name == "module1.function1"

    def test_resolve_call(self, sample_modules):
        indexer = RepoIndexer(sample_modules)
        indexer._build_module_name_map()
        indexer._build_symbol_table()

        # Test resolving built-in function
        module = sample_modules[0]
        function = module.functions[0]
        resolved_print = indexer._resolve_call("print", function, module)
        assert resolved_print == "print"  # Built-in function

        # Test resolving imported function
        module = sample_modules[1]
        method = module.classes[0].methods[0]
        resolved_func = indexer._resolve_call("module1.function1", method, module)
        assert resolved_func == "module1.function1"

        # Test resolving non-existent function
        resolved_none = indexer._resolve_call("nonexistent", function, module)
        assert resolved_none is None

    def test_extract_function_calls(self, sample_modules):
        indexer = RepoIndexer(sample_modules)
        
        # Test extracting function call from method1
        module = sample_modules[1]
        method = module.classes[0].methods[0]
        calls = indexer._extract_function_calls(method, module)
        
        assert len(calls) == 1
        assert calls[0].name == "module1.function1"
        assert calls[0].line_number == 3  # Line number in the method's body

    def test_is_builtin_function(self, sample_modules):
        indexer = RepoIndexer(sample_modules)
        
        assert indexer._is_builtin_function("print") == True
        assert indexer._is_builtin_function("len") == True
        assert indexer._is_builtin_function("nonexistent") == False
        assert indexer._is_builtin_function("function1") == False

    def test_index_repository_integration(self, sample_modules):
        """Integration test for the complete indexing process"""
        indexer = RepoIndexer(sample_modules)
        indexer.index_repository()

        # Verify module name map
        assert len(indexer.module_name_map) == 2
        assert all(module.name in indexer.module_name_map for module in sample_modules)

        # Verify symbol table
        assert len(indexer.symbol_table) == 3  # function1, Class1, method1
        assert all(name in indexer.symbol_table for name in ["function1", "Class1", "method1"])

        # Verify function call resolution
        method1 = sample_modules[1].classes[0].methods[0]
        assert len(method1.function_calls) == 1
        call = method1.function_calls[0]
        assert call.name == "module1.function1"
        assert call.resolved_name == "module1.function1"

    @pytest.mark.parametrize("test_input,expected", [
        ("print", True),
        ("len", True),
        ("custom_function", False),
        ("", False),
        ("__import__", True),
    ])
    def test_is_builtin_function_parametrized(self, sample_modules, test_input, expected):
        """Parametrized test for builtin function checking"""
        indexer = RepoIndexer(sample_modules)
        assert indexer._is_builtin_function(test_input) == expected

    def test_error_handling(self, sample_modules):
        """Test error handling for invalid inputs"""
        # Test with invalid module
        invalid_module = ModuleElement(
            name="invalid",
            path=Path("invalid.py"),
            language="Python",
            functions=[
                FunctionElement(
                    name="invalid_func",
                    path=Path("invalid.py"),
                    start_line=1,
                    end_line=5,
                    # Missing fields from data_models.py:
                    module=None,
                    documentation=None,
                    parameters=[],
                    return_type=None,
                    decorators=[],
                    complexity=None,
                    is_async=False,
                    function_calls=[],
                    qualified_name=None
                )
            ],
            classes=[],
            imports=[],
            imports_mapping={},
            body="def invalid_func():\n    invalid_syntax :"
        )

        indexer = RepoIndexer([invalid_module])
        indexer.index_repository()  # Should not raise exception

        # Check if function calls is empty due to invalid syntax
        assert len(invalid_module.functions[0].function_calls) == 0