from pathlib import Path
from typing import List, Dict, Optional
from collections import defaultdict
from ..language_parsers.python_parser import PythonParser
from ..models.data_models import FunctionElement, ModuleElement, FunctionCallElement
from .repo_analyzer import RepoIndexer


class MainParser:
    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.parser = PythonParser()
        self.modules = []
        self.indexer = None
        self.call_graph = {}

    def parse_repo(self):
        """
        Parse all Python files in the repository and store the resulting modules.
        """
        self.modules = []
        if not self.repo_path.exists():
            raise FileNotFoundError(f"The repository path {self.repo_path} does not exist.")
        for file_path in self.repo_path.rglob("*.py"):
            if self.parser.can_parse(file_path):
                try:
                    module = self.parser.parse_file(file_path, repo_root=self.repo_path)
                    self.modules.append(module)
                except Exception as e:
                    print(f"Error parsing {file_path}: {e}")

        # Create and run the indexer
        self.indexer = RepoIndexer(self.modules)
        self.indexer.index_repository()

    def build_call_graph(self):
        """
        Build the function call graph for the parsed repository.
        """
        if not self.indexer:
            raise RuntimeError("Repository must be parsed before building the call graph.")

        call_graph = defaultdict(list)
        symbol_table = self.indexer.symbol_table

        for module in self.modules:
            # Process functions
            for func in module.functions:
                caller = func.qualified_name
                if caller and caller in symbol_table:
                    for call in func.function_calls:
                        if call.resolved_name and call.resolved_name in symbol_table:
                            call_graph[caller].append(call.resolved_name)

            # Process class methods
            for cls in module.classes:
                for method in cls.methods:
                    caller = method.qualified_name
                    if caller and caller in symbol_table:
                        for call in method.function_calls:
                            if call.resolved_name and call.resolved_name in symbol_table:
                                call_graph[caller].append(call.resolved_name)

        self.call_graph = dict(call_graph)

    def get_function_source_code(self, function_name: str) -> str:
        """
        Retrieve the source code of a specific function by its name.
        """
        if not self.indexer:
            raise RuntimeError("Repository must be parsed before retrieving function source code.")

        func_elem = self.indexer.symbol_table.get(function_name)
        if not func_elem:
            raise ValueError(f"Function {function_name} not found in symbol table.")

        module = func_elem.module
        source_lines = module.body.splitlines()[func_elem.start_line - 1:func_elem.end_line]
        return "\n".join(source_lines)

    def group_calls_by_line(self, function: FunctionElement) -> Dict[int, List[FunctionCallElement]]:
        """
        Group function calls by line number within a function.
        """
        calls_by_line = defaultdict(list)
        for call in function.function_calls:
            if call.resolved_name in self.indexer.symbol_table:
                calls_by_line[call.line_number - 1].append(call)
        return dict(calls_by_line)

    def display_function_source_and_calls(
        self,
        func_fqn: str,
        visited_stack: Optional[List[str]] = None,
        indent: int = 0
    ):
        """
        Display the source code of a function and its calls, expanding inlined calls recursively.
        """
        if not self.indexer:
            raise RuntimeError("Repository must be parsed before displaying function source and calls.")

        if visited_stack is None:
            visited_stack = []

        if func_fqn in visited_stack:
            print(" " * indent + f"(cycle) {func_fqn} ... {' -> '.join(visited_stack)} -> {func_fqn}")
            return

        visited_stack.append(func_fqn)
        func_elem = self.indexer.symbol_table.get(func_fqn)

        if not func_elem:
            print(" " * indent + f"* {func_fqn} (unresolved or built-in)")
            visited_stack.pop()
            return

        print(" " * indent + f"{func_elem.name}()")
        function_source_code = self.get_function_source_code(func_fqn)
        if function_source_code:
            source_lines = function_source_code.splitlines()
            calls_by_line = self.group_calls_by_line(func_elem)

            for idx, line in enumerate(source_lines):
                print(" " * (indent + 2) + line)
                if idx in calls_by_line:
                    for call in calls_by_line[idx]:
                        callee_fqn = call.resolved_name
                        if callee_fqn:
                            previous_line_length = len(source_lines[idx-1]) + indent + 4 if idx > 0 else 0
                            print(" " * previous_line_length + f"-> calls {callee_fqn}")
                            self.display_function_source_and_calls(callee_fqn, visited_stack, previous_line_length + 3)
                        else:
                            print(" " * (indent + 4) + f"-> calls {call.name} (unresolved)")
        else:
            print(" " * (indent + 2) + "<No source available>")

        visited_stack.pop()