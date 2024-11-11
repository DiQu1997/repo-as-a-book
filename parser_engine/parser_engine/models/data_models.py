from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set, Union
from pathlib import Path

"""
Data models for the Parser Engine.
This module contains the core data models used throughout the Parser Engine.

The data models are implemented as dataclasses and represent different aspects of a code repository:

ContributorData:
    Stores information about repository contributors including their name, email,
    commit counts, and contribution statistics.

CommitData: 
    Represents individual git commits with details like hash, author, date,
    commit message and changed files.

DocumentationElement:
    Models documentation blocks found in the code, including docstrings,
    comments and markdown files. Tracks content, location and context.

FunctionElement:
    Represents function and method definitions, capturing name, location,
    parameters, return type, decorators and complexity metrics.

ClassElement:
    Models class definitions with their methods, attributes and inheritance
    relationships.

These models provide a structured way to store and access repository data
during parsing and analysis. They include appropriate type hints and default
values where needed.

The models are designed to be immutable and hashable to ensure data integrity
during processing. Optional fields use the Optional type hint to explicitly
indicate nullable attributes.

"""

@dataclass(frozen=True)  # Make immutable for better data integrity
class ContributorData:
    """Represents a repository contributor."""
    name: str
    email: str
    commits_count: int
    first_commit_date: datetime
    last_commit_date: datetime
    lines_added: int = 0
    lines_deleted: int = 0
    
    @property
    def active_days(self) -> int:
        """Calculate the number of days between first and last commit."""
        return (self.last_commit_date - self.first_commit_date).days

@dataclass(frozen=True)
class CommitData:
    """Represents a git commit."""
    hash: str
    author: ContributorData
    date: datetime
    message: str
    files_changed: List[str]
    lines_added: int
    lines_deleted: int
    branch: str = 'main'  # Add branch tracking

@dataclass(frozen=True)
class DocumentationElement:
    """Represents a documentation block."""
    content: str
    path: Path  # Change to Path
    line_number: int
    type: str  # e.g., 'docstring', 'comment', 'markdown'
    context: Optional[str] = None
    
    @property
    def is_docstring(self) -> bool:
        """Check if this is a docstring."""
        return self.type == 'docstring'

@dataclass
class FunctionElement:
    """Represents a function or method."""
    name: str
    path: Path  # Change to Path
    start_line: int
    end_line: int  # Add end line tracking
    documentation: Optional[DocumentationElement] = None
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    complexity: Optional[int] = None
    is_async: bool = False
    
    @property
    def length(self) -> int:
        """Calculate function length in lines."""
        return self.end_line - self.line_number + 1

@dataclass
class ClassElement:
    """Represents a class definition."""
    name: str
    path: Path  # Change to Path
    start_line: int
    end_line: int  # Add end line tracking
    documentation: Optional[DocumentationElement] = None
    methods: List[FunctionElement] = field(default_factory=list)
    base_classes: List[str] = field(default_factory=list)
    attributes: Dict[str, str] = field(default_factory=dict)
    decorators: List[str] = field(default_factory=list)
    inner_classes: List['ClassElement'] = field(default_factory=list)  # Add inner classes support

@dataclass
class ModuleElement:
    """Represents a code module (file)."""
    name: str
    path: Path  # Change to Path
    language: str
    classes: List[ClassElement] = field(default_factory=list)
    functions: List[FunctionElement] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    documentation: Optional[DocumentationElement] = None
    size_bytes: int = 0
    lines_of_code: int = 0
    
    @property
    def is_package(self) -> bool:
        """Check if this module is a package (__init__.py)."""
        return self.name == '__init__'

@dataclass
class FileNode:
    """Represents a file in the repository."""
    name: str
    path: Path  # Change to Path
    size_bytes: int
    last_modified: datetime
    extension: str
    content_type: str  # e.g., 'code', 'documentation', 'configuration', 'binary'
    language: Optional[str] = None
    lines_of_code: int = 0
    module_data: Optional[ModuleElement] = None
    
    @property
    def is_code(self) -> bool:
        """Check if this is a code file."""
        return self.content_type == 'code'
    
    @property
    def is_documentation(self) -> bool:
        """Check if this is a documentation file."""
        return self.content_type == 'documentation'

@dataclass
class DirectoryNode:
    """Represents a directory in the repository."""
    name: str
    path: Path  # Change to Path
    files: List[FileNode] = field(default_factory=list)
    subdirectories: List['DirectoryNode'] = field(default_factory=list)
    last_modified: Optional[datetime] = None
    total_files: int = 0
    total_size_bytes: int = 0
    
    def add_file(self, file: FileNode) -> None:
        """Add a file to the directory and update statistics."""
        self.files.append(file)
        self.total_files += 1
        self.total_size_bytes += file.size_bytes
        if not self.last_modified or file.last_modified > self.last_modified:
            self.last_modified = file.last_modified
    
    def add_directory(self, directory: 'DirectoryNode') -> None:
        """Add a subdirectory and update statistics."""
        self.subdirectories.append(directory)
        self.total_files += directory.total_files
        self.total_size_bytes += directory.total_size_bytes
        if not self.last_modified or directory.last_modified > self.last_modified:
            self.last_modified = directory.last_modified
    
    def get_all_files(self) -> List[FileNode]:
        """Get all files in this directory and subdirectories."""
        all_files = self.files.copy()
        for subdir in self.subdirectories:
            all_files.extend(subdir.get_all_files())
        return all_files

@dataclass
class DirectoryTree:
    """Represents the complete directory structure of a repository."""
    root: DirectoryNode
    total_files: int = 0
    total_size_bytes: int = 0
    max_depth: int = 0
    file_types: Dict[str, int] = field(default_factory=dict)  # extension -> count
    language_stats: Dict[str, int] = field(default_factory=dict)  # language -> lines of code
    
    def calculate_stats(self) -> Dict[str, Union[int, Dict[str, int]]]:
        """Calculate and return repository statistics."""
        self._calculate_stats_recursive(self.root, 0)
        return {
            'total_files': self.total_files,
            'total_size_bytes': self.total_size_bytes,
            'max_depth': self.max_depth,
            'file_types': self.file_types,
            'language_stats': self.language_stats
        }
    
    def _calculate_stats_recursive(self, node: DirectoryNode, depth: int) -> None:
        """Recursively calculate statistics for the directory tree."""
        self.max_depth = max(self.max_depth, depth)
        
        for file in node.files:
            self.total_files += 1
            self.total_size_bytes += file.size_bytes
            self.file_types[file.extension] = self.file_types.get(file.extension, 0) + 1
            if file.language:
                self.language_stats[file.language] = (
                    self.language_stats.get(file.language, 0) + file.lines_of_code
                )
        
        for subdir in node.subdirectories:
            self._calculate_stats_recursive(subdir, depth + 1)

@dataclass
class RepositoryData:
    """Represents the analyzed repository data."""
    name: str
    url: str
    primary_language: str
    directory_tree: DirectoryTree
    languages: Dict[str, int] = field(default_factory=dict)  # language -> lines of code
    modules: List[ModuleElement] = field(default_factory=list)
    documentation_files: List[DocumentationElement] = field(default_factory=list)
    contributors: List[ContributorData] = field(default_factory=list)
    commit_history: List[CommitData] = field(default_factory=list)
    creation_date: Optional[datetime] = None
    last_update_date: Optional[datetime] = None
    
    @property
    def total_files(self) -> int:
        """Get total number of files in the repository."""
        return self.directory_tree.total_files
    
    @property
    def total_size_bytes(self) -> int:
        """Get total size of the repository in bytes."""
        return self.directory_tree.total_size_bytes
    
    def get_stats(self) -> Dict[str, Union[int, str, dict]]:
        """Generate comprehensive repository statistics."""
        return {
            'name': self.name,
            'primary_language': self.primary_language,
            'total_files': self.total_files,
            'total_size_bytes': self.total_size_bytes,
            'languages': self.languages,
            'total_modules': len(self.modules),
            'total_documentation_files': len(self.documentation_files),
            'total_contributors': len(self.contributors),
            'total_commits': len(self.commit_history),
            'age_days': (datetime.now() - self.creation_date).days if self.creation_date else None,
            'directory_stats': self.directory_tree.calculate_stats()
        }