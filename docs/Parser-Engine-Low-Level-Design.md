# Low-Level Design Document: **Parser Engine for "Repo as a Book"**

## Table of Contents

1. [Introduction](#introduction)
2. [Goals and Constraints](#goals-and-constraints)
3. [Overall Architecture](#overall-architecture)
4. [Class Diagrams and Relationships](#class-diagrams-and-relationships)
5. [Detailed Component Design](#detailed-component-design)
   - [1. Main Parser Engine](#1-main-parser-engine)
   - [2. Language Detection Module](#2-language-detection-module)
   - [3. File Classification Module](#3-file-classification-module)
   - [4. Language Parsers](#4-language-parsers)
     - [Python Parser](#python-parser)
     - [JavaScript Parser](#javascript-parser)
     - [Adding Support for New Languages](#adding-support-for-new-languages)
   - [5. Documentation Parser](#5-documentation-parser)
   - [6. Metadata Extractor](#6-metadata-extractor)
   - [7. Data Structuring Module](#7-data-structuring-module)
   - [8. Output Generator](#8-output-generator)
6. [Data Models and Structures](#data-models-and-structures)
   - [Data Classes](#data-classes)
   - [UML Class Diagrams](#uml-class-diagrams)
7. [Algorithms and Logic Flow](#algorithms-and-logic-flow)
   - [Parsing Workflow](#parsing-workflow)
   - [Language Parser Strategy Pattern](#language-parser-strategy-pattern)
8. [Design Patterns Used](#design-patterns-used)
9. [Error Handling and Logging](#error-handling-and-logging)
10. [Dependencies and Libraries](#dependencies-and-libraries)
11. [Example Code Snippets](#example-code-snippets)
12. [Implementation Guidelines](#implementation-guidelines)
13. [Testing Strategy](#testing-strategy)
14. [Conclusion](#conclusion)

---

## Introduction

This low-level design document provides a detailed blueprint for developers to implement the **Parser Engine** component of the **"Repo as a Book"** project. It specifies the classes, methods, data structures, algorithms, and code patterns to guide programmers in coding the Parser Engine effectively.

---

## Goals and Constraints

- **Guiding Principles**:
  - Modularity
  - Extensibility
  - Maintainability
  - Performance
  - Accuracy
- **Constraints**:
  - Must handle repositories with multiple programming languages.
  - Should not execute any code from the repository (security constraint).
  - Should process large codebases efficiently.

---

## Overall Architecture

The Parser Engine consists of several interconnected modules:

1. **Main Parser Engine**: Orchestrates the parsing process.
2. **Language Detection Module**: Identifies programming languages used.
3. **File Classification Module**: Categorizes files.
4. **Language Parsers**: Parses code for specific languages.
5. **Documentation Parser**: Processes documentation files.
6. **Metadata Extractor**: Extracts Git metadata.
7. **Data Structuring Module**: Organizes parsed data into a hierarchical structure.
8. **Output Generator**: Serializes structured data for the Content Generator.

---

## Class Diagrams and Relationships

*(Note: UML diagrams are represented in text format for readability.)*

- **MainParserEngine**
  - uses **LanguageDetectionModule**
  - uses **FileClassificationModule**
  - uses multiple **LanguageParser** instances via **ParserFactory**
  - uses **DocumentationParser**
  - uses **MetadataExtractor**
  - uses **DataStructuringModule**
  - uses **OutputGenerator**

- **ParserFactory**
  - creates **LanguageParser** instances based on language.

- **LanguageParser** (Abstract Base Class)
  - implemented by **PythonParser**, **JavaScriptParser**, etc.

- **Data Models**
  - **RepositoryData**
    - contains **BookStructure**, **CommitData**, **ContributorData**, etc.

---

## Detailed Component Design

### 1. Main Parser Engine

#### Responsibilities

- Coordinates the overall parsing process.
- Manages interactions between modules.
- Handles input and triggers the output generation.

#### Class: `MainParserEngine`

```python
class MainParserEngine:
    def __init__(self, repo_path: str):
        self.repo_path = repo_path
        self.language_detection_module = LanguageDetectionModule()
        self.file_classification_module = FileClassificationModule()
        self.metadata_extractor = MetadataExtractor(repo_path)
        self.data_structuring_module = DataStructuringModule()
        self.output_generator = OutputGenerator()

    def parse_repository(self):
        # Step 1: Detect Languages
        language_files_map = self.language_detection_module.detect_languages(self.repo_path)

        # Step 2: Classify Files
        classified_files = self.file_classification_module.classify_files(self.repo_path)

        # Step 3: Extract Metadata
        commit_data, contributor_data = self.metadata_extractor.extract_metadata()

        # Step 4: Parse Code Files
        code_elements = self._parse_code_files(language_files_map)

        # Step 5: Parse Documentation Files
        documentation_elements = self._parse_documentation_files(classified_files['documentation'])

        # Step 6: Structure Data
        repository_data = self.data_structuring_module.structure_data(
            code_elements,
            documentation_elements,
            commit_data,
            contributor_data
        )

        # Step 7: Generate Output
        self.output_generator.generate_output(repository_data)
```

---

### 2. Language Detection Module

#### Responsibilities

- Scans repository files to detect programming languages.
- Maintains a mapping of file extensions to languages.

#### Class: `LanguageDetectionModule`

```python
class LanguageDetectionModule:
    def __init__(self):
        self.extension_language_map = self._load_extension_language_map()

    def _load_extension_language_map(self) -> Dict[str, str]:
        # Load from a configuration file or define inline
        return {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            # Add more extensions and languages...
        }

    def detect_languages(self, repo_path: str) -> Dict[str, List[str]]:
        language_files_map = defaultdict(list)
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                ext = os.path.splitext(file)[1]
                language = self.extension_language_map.get(ext)
                if language:
                    file_path = os.path.join(root, file)
                    language_files_map[language].append(file_path)
        return dict(language_files_map)
```

---

### 3. File Classification Module

#### Responsibilities

- Categorizes files into code, documentation, configuration, etc.

#### Class: `FileClassificationModule`

```python
class FileClassificationModule:
    def __init__(self):
        self.documentation_extensions = ['.md', '.rst', '.txt']
        self.configuration_extensions = ['.json', '.yaml', '.yml', '.xml']

    def classify_files(self, repo_path: str) -> Dict[str, List[str]]:
        classified_files = {'code': [], 'documentation': [], 'config': [], 'others': []}
        for root, dirs, files in os.walk(repo_path):
            for file in files:
                ext = os.path.splitext(file)[1]
                file_path = os.path.join(root, file)
                if ext in self.documentation_extensions:
                    classified_files['documentation'].append(file_path)
                elif ext in self.configuration_extensions:
                    classified_files['config'].append(file_path)
                elif ext in self._get_code_extensions():
                    classified_files['code'].append(file_path)
                else:
                    classified_files['others'].append(file_path)
        return classified_files

    def _get_code_extensions(self) -> List[str]:
        # Could be extracted from LanguageDetectionModule or defined here
        return ['.py', '.js', '.java', '.cpp', '.c']
```

---

### 4. Language Parsers

#### Responsibilities

- Parse code files for specific programming languages.
- Extract code structures and documentation.

#### Design Pattern Used

- **Strategy Pattern**: Each language parser implements a common interface, allowing the Main Parser Engine to use them interchangeably.

#### Interface: `LanguageParser`

```python
class LanguageParser(ABC):
    @abstractmethod
    def parse_file(self, file_path: str) -> CodeElement:
        pass
```

---

#### Parser Factory

#### Class: `ParserFactory`

```python
class ParserFactory:
    @staticmethod
    def get_parser(language: str) -> LanguageParser:
        parsers = {
            'Python': PythonParser(),
            'JavaScript': JavaScriptParser(),
            # Add additional language parsers here...
        }
        parser = parsers.get(language)
        if parser is None:
            raise NotImplementedError(f"No parser available for language: {language}")
        return parser
```

---

#### Python Parser

##### Class: `PythonParser`

```python
class PythonParser(LanguageParser):
    def parse_file(self, file_path: str) -> ModuleElement:
        with open(file_path, 'r', encoding='utf-8') as file:
            source_code = file.read()
        tree = ast.parse(source_code, filename=file_path)
        module_element = self._process_module(tree, file_path)
        return module_element

    def _process_module(self, node: ast.Module, file_path: str) -> ModuleElement:
        module_element = ModuleElement(name=os.path.basename(file_path), file_path=file_path)
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                class_element = self._process_class(child)
                module_element.classes.append(class_element)
            elif isinstance(child, ast.FunctionDef):
                function_element = self._process_function(child)
                module_element.functions.append(function_element)
            elif isinstance(child, ast.Import) or isinstance(child, ast.ImportFrom):
                import_element = self._process_import(child)
                module_element.imports.append(import_element)
        return module_element

    def _process_class(self, node: ast.ClassDef) -> ClassElement:
        class_element = ClassElement(
            name=node.name,
            docstring=ast.get_docstring(node) or "",
            methods=[],
            properties=[]
        )
        for child in node.body:
            if isinstance(child, ast.FunctionDef):
                method_element = self._process_function(child)
                class_element.methods.append(method_element)
        return class_element

    def _process_function(self, node: ast.FunctionDef) -> FunctionElement:
        function_element = FunctionElement(
            name=node.name,
            docstring=ast.get_docstring(node) or "",
            parameters=[arg.arg for arg in node.args.args]
        )
        return function_element

    def _process_import(self, node: Union[ast.Import, ast.ImportFrom]) -> ImportElement:
        # Handle import statements
        pass  # Implementation details
```

---

#### JavaScript Parser

**Note**: Parsing JavaScript may require integration with Node.js tools like Esprima.

##### Class: `JavaScriptParser`

```python
class JavaScriptParser(LanguageParser):
    def parse_file(self, file_path: str) -> ModuleElement:
        # Use subprocess to call Node.js script for parsing
        parsed_data = self._parse_with_esprima(file_path)
        module_element = self._process_parsed_data(parsed_data)
        return module_element

    def _parse_with_esprima(self, file_path: str) -> Dict:
        command = ['node', 'esprima_parser.js', file_path]
        result = subprocess.run(command, stdout=subprocess.PIPE)
        return json.loads(result.stdout)

    def _process_parsed_data(self, data: Dict) -> ModuleElement:
        # Convert parsed data to ModuleElement and related classes
        pass  # Implementation details
```

##### Sample Node.js Script (`esprima_parser.js`)

```javascript
const fs = require('fs');
const esprima = require('esprima');

const filePath = process.argv[2];
const code = fs.readFileSync(filePath, 'utf-8');
const ast = esprima.parseModule(code, { comment: true, loc: true });
console.log(JSON.stringify(ast));
```

---

#### Adding Support for New Languages

- Implement a new class inheriting from `LanguageParser`.
- Update `ParserFactory` to include the new parser.
- Ensure the new parser adheres to the interface contract.

---

### 5. Documentation Parser

#### Responsibilities

- Parses documentation files like Markdown and reStructuredText.

#### Class: `DocumentationParser`

```python
class DocumentationParser:
    def parse_files(self, file_paths: List[str]) -> List[DocumentationElement]:
        documentation_elements = []
        for file_path in file_paths:
            ext = os.path.splitext(file_path)[1]
            if ext == '.md':
                element = self._parse_markdown(file_path)
            elif ext in ['.rst', '.txt']:
                element = self._parse_restructuredtext(file_path)
            else:
                continue  # Unsupported format
            documentation_elements.append(element)
        return documentation_elements

    def _parse_markdown(self, file_path: str) -> DocumentationElement:
        with open(file_path, 'r', encoding='utf-8') as file:
            text = file.read()
        md = markdown.Markdown(extensions=['toc'])
        html = md.convert(text)
        # Process HTML to extract structure
        element = self._html_to_documentation_element(html)
        return element

    def _parse_restructuredtext(self, file_path: str) -> DocumentationElement:
        # Similar process using docutils
        pass  # Implementation details

    def _html_to_documentation_element(self, html: str) -> DocumentationElement:
        # Parse HTML and build DocumentationElement
        pass  # Implementation details
```

---

### 6. Metadata Extractor

#### Responsibilities

- Extracts commit history and contributor data from the Git repository.

#### Class: `MetadataExtractor`

```python
class MetadataExtractor:
    def __init__(self, repo_path: str):
        self.repo = Repo(repo_path)

    def extract_metadata(self) -> Tuple[List[CommitData], List[ContributorData]]:
        commits = []
        contributors = defaultdict(int)
        for commit in self.repo.iter_commits():
            commit_data = CommitData(
                hash=commit.hexsha,
                author=commit.author.name,
                email=commit.author.email,
                date=commit.committed_datetime,
                message=commit.message.strip(),
                files_changed=commit.stats.files.keys()
            )
            commits.append(commit_data)
            contributors[commit.author.email] += 1
        contributor_data = [
            ContributorData(name=email, commits_count=count)
            for email, count in contributors.items()
        ]
        return commits, contributor_data
```

---

### 7. Data Structuring Module

#### Responsibilities

- Organizes parsed data into a hierarchical structure.

#### Class: `DataStructuringModule`

```python
class DataStructuringModule:
    def structure_data(
        self,
        code_elements: List[ModuleElement],
        documentation_elements: List[DocumentationElement],
        commit_data: List[CommitData],
        contributor_data: List[ContributorData]
    ) -> RepositoryData:
        # Map code elements and documentation to chapters and sections
        book_structure = self._build_book_structure(code_elements, documentation_elements)
        repository_data = RepositoryData(
            title="Repository Title",
            language_stats=self._calculate_language_stats(code_elements),
            contributors=contributor_data,
            commits=commit_data,
            book_structure=book_structure
        )
        return repository_data

    def _build_book_structure(
        self,
        code_elements: List[ModuleElement],
        documentation_elements: List[DocumentationElement]
    ) -> BookStructure:
        # Implementation details for building chapters and sections
        pass

    def _calculate_language_stats(self, code_elements: List[ModuleElement]) -> Dict[str, int]:
        # Calculate percentage or count of each language
        pass
```

---

### 8. Output Generator

#### Responsibilities

- Serializes the structured data into JSON format.

#### Class: `OutputGenerator`

```python
class OutputGenerator:
    def generate_output(self, repository_data: RepositoryData):
        output_path = os.path.join('output', f"{repository_data.title}.json")
        with open(output_path, 'w', encoding='utf-8') as outfile:
            json.dump(repository_data.to_dict(), outfile, indent=4, default=str)

    def to_dict(self, obj):
        # Convert custom objects to dictionaries
        if isinstance(obj, dict):
            return {k: self.to_dict(v) for k, v in obj.items()}
        elif hasattr(obj, '__dict__'):
            return self.to_dict(vars(obj))
        elif isinstance(obj, list):
            return [self.to_dict(item) for item in obj]
        else:
            return obj
```

---

## Data Models and Structures

### Data Classes

Data models use the **@dataclass** decorator for simplicity and readability.

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class RepositoryData:
    title: str
    language_stats: Dict[str, int]
    contributors: List['ContributorData']
    commits: List['CommitData']
    book_structure: 'BookStructure'

@dataclass
class ModuleElement:
    name: str
    file_path: str
    classes: List['ClassElement'] = field(default_factory=list)
    functions: List['FunctionElement'] = field(default_factory=list)
    imports: List['ImportElement'] = field(default_factory=list)

@dataclass
class ClassElement:
    name: str
    docstring: str
    methods: List['FunctionElement']
    properties: List[str] = field(default_factory=list)

@dataclass
class FunctionElement:
    name: str
    docstring: str
    parameters: List[str]

# Additional data classes for code elements, documentation, commits, contributors

@dataclass
class DocumentationElement:
    title: str
    content: str
    subsections: List['DocumentationElement'] = field(default_factory=list)

@dataclass
class CommitData:
    hash: str
    author: str
    email: str
    date: datetime
    message: str
    files_changed: List[str]

@dataclass
class ContributorData:
    name: str
    commits_count: int
```

---

### UML Class Diagrams

Due to space limitations, here's a textual representation:

- **RepositoryData**
  - Fields:
    - `title`: str
    - `language_stats`: Dict[str, int]
    - `contributors`: List[ContributorData]
    - `commits`: List[CommitData]
    - `book_structure`: BookStructure

- **BookStructure**
  - Contains multiple **Chapter** instances.

- **Chapter**
  - Fields:
    - `title`: str
    - `sections`: List[Section]

- **Section**
  - Fields:
    - `title`: str
    - `content`: str
    - `subsections`: List[Section]

- **ModuleElement**, **ClassElement**, **FunctionElement** model code structures.

---

## Algorithms and Logic Flow

### Parsing Workflow

1. **Initialization**: The `MainParserEngine` is initialized with the repository path.
2. **Language Detection**: Detect programming languages and associated files.
3. **File Classification**: Categorize files into code, documentation, etc.
4. **Metadata Extraction**: Extract commit history and contributors.
5. **Code Parsing**:
   - For each language:
     - Obtain the corresponding `LanguageParser` via `ParserFactory`.
     - For each file in that language:
       - Use the parser to process the file and extract code elements.
6. **Documentation Parsing**:
   - Use `DocumentationParser` to process documentation files.
7. **Data Structuring**:
   - Organize code elements and documentation into a hierarchical structure.
8. **Output Generation**:
   - Serialize structured data into JSON format.

---

### Language Parser Strategy Pattern

- **Context**: The `MainParserEngine` uses language parsers without needing to know their implementation details.
- **Strategy Interface**: `LanguageParser` defines the `parse_file` method.
- **Concrete Strategies**: `PythonParser`, `JavaScriptParser`, etc.

---

## Design Patterns Used

- **Strategy Pattern**: For selecting the appropriate language parser.
- **Factory Pattern**: `ParserFactory` creates instances of language parsers.
- **Facade Pattern**: `MainParserEngine` provides a simplified interface to complex subsystems.
- **Data Transfer Object (DTO)**: Data classes act as DTOs to transfer data between components.
- **Singleton Pattern**: Could be used for `LanguageDetectionModule` if needed.

---

## Error Handling and Logging

- Use Python's `logging` module to log messages at different levels: DEBUG, INFO, WARNING, ERROR.
- Implement exception handling in all modules.
  - For example, if a parser fails on a file, log the exception and continue processing other files.
- Use `try-except` blocks around critical code sections.

```python
try:
    module_element = parser.parse_file(file_path)
    code_elements.append(module_element)
except Exception as e:
    logging.error(f"Failed to parse {file_path}: {e}")
```

---

## Dependencies and Libraries

- **ast**: For parsing Python code.
- **GitPython**: For interacting with Git repositories.
- **markdown**: For parsing Markdown files.
- **dataclasses**: For data models (Python 3.7+).
- **typing**: For type hints and generics.
- **os, sys, json, subprocess, datetime**: Standard libraries.
- **logging**: For logging.
- **Optional libraries for other languages**:
  - **Esprima**: For parsing JavaScript (Node.js).
  - **JPype**: For Java parsing if needed.

---

## Example Code Snippets

### Parsing a Python Function with AST

```python
def _process_function(self, node: ast.FunctionDef) -> FunctionElement:
    function_element = FunctionElement(
        name=node.name,
        docstring=ast.get_docstring(node) or "",
        parameters=[arg.arg for arg in node.args.args],
        decorators=[d.id for d in node.decorator_list if isinstance(d, ast.Name)]
    )
    return function_element
```

### Calculating Language Statistics

```python
def _calculate_language_stats(self, code_elements: List[ModuleElement]) -> Dict[str, int]:
    language_counts = defaultdict(int)
    for module in code_elements:
        language = self._get_language_from_extension(module.file_path)
        language_counts[language] += 1
    total = sum(language_counts.values())
    language_stats = {lang: (count / total) * 100 for lang, count in language_counts.items()}
    return language_stats

def _get_language_from_extension(self, file_path: str) -> str:
    ext = os.path.splitext(file_path)[1]
    return self.extension_language_map.get(ext, 'Unknown')
```

---

## Implementation Guidelines

- **Code Style**: Follow PEP 8 guidelines for Python code.
- **Type Hints**: Use type annotations for better readability and tooling support.
- **Documentation**: Use docstrings for all classes and methods.
- **Modularity**: Keep functions and methods short and focused.
- **Testing**: Write unit tests for each module and critical function.

---

## Testing Strategy

### Unit Tests

- Test individual modules in isolation.
- Use `unittest` or `pytest` frameworks.
- Mock external dependencies where necessary.

### Integration Tests

- Test the interaction between modules.
- Use test repositories with known content.

### End-to-End Tests

- Process complete repositories and verify the final output.
- Compare output against expected structures.

### Test Cases

- **Valid Inputs**: Repositories with various languages and structures.
- **Edge Cases**: Empty repositories, repositories with uncommon file structures.
- **Error Handling**: Invalid code files, unsupported languages.

---

## Conclusion

This low-level design provides a comprehensive blueprint for developers to implement the Parser Engine for the **"Repo as a Book"** project. By following the outlined classes, methods, data structures, and algorithms, programmers can build a robust, extensible, and efficient Parser Engine that fulfills the project's requirements.

---