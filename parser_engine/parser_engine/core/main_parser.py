from pathlib import Path
import logging
from typing import Dict, List, Optional, Set
from datetime import datetime

from ..models.data_models import (
    RepositoryData, DirectoryTree, DirectoryNode, FileNode,
    ModuleElement, DocumentationElement, CommitData, ContributorData
)

"""
Main orchestrator for the repository parsing process.
Coordinates different parsing components and assembles the final repository data.

Workflow:
1. Build directory tree
2. Detect languages
3. Parse code files
4. Parse documentation files
5. Extract Git metadata
6. Assemble repository data
"""

class MainParserEngine:
    """
    Main orchestrator for the repository parsing process.
    Coordinates different parsing components and assembles the final repository data.
    """

    def __init__(self, repository_path: str, logger: Optional[logging.Logger] = None):
        """
        Initialize the parser engine.

        Args:
            repository_path: Path to the Git repository
            logger: Optional logger instance
        """
        self.repo_path = Path(repository_path)
        if not self.repo_path.exists():
            raise ValueError(f"Repository path does not exist: {repository_path}")
        if not self.repo_path.is_dir():
            raise ValueError(f"Repository path is not a directory: {repository_path}")

        self.logger = logger or logging.getLogger(__name__)
        
        # Will be initialized as needed
        self._language_detector = None
        self._file_classifier = None
        self._metadata_extractor = None
        self._documentation_parser = None
        
    def parse_repository(self) -> RepositoryData:
        """
        Parse the entire repository and generate comprehensive data.

        Returns:
            RepositoryData object containing all parsed information
        """
        try:
            self.logger.info(f"Starting repository parsing: {self.repo_path}")
            
            # Step 1: Build directory tree and detect languages
            directory_tree = self._build_directory_tree()
            languages = self._detect_languages(directory_tree)
            
            # Step 2: Parse code files
            modules = self._parse_code_files(directory_tree)
            
            # Step 3: Parse documentation
            documentation = self._parse_documentation_files(directory_tree)
            
            # Step 4: Extract Git metadata
            contributors, commits = self._extract_metadata()
            
            # Step 5: Assemble repository data
            repo_data = RepositoryData(
                name=self.repo_path.name,
                url=self._get_repository_url(),
                primary_language=self._determine_primary_language(languages),
                directory_tree=directory_tree,
                languages=languages,
                modules=modules,
                documentation_files=documentation,
                contributors=contributors,
                commit_history=commits,
                creation_date=self._get_creation_date(commits),
                last_update_date=self._get_last_update_date(commits)
            )
            
            self.logger.info("Repository parsing completed successfully")
            return repo_data
            
        except Exception as e:
            self.logger.error(f"Error parsing repository: {str(e)}")
            raise

    def _build_directory_tree(self) -> DirectoryTree:
        """Build the directory tree structure."""
        def _build_node(path: Path) -> DirectoryNode:
            node = DirectoryNode(
                name=path.name,
                path=path,
                files=[],
                subdirectories=[]
            )
            
            try:
                # Process all entries in the directory
                for entry in path.iterdir():
                    if entry.name.startswith('.'):  # Skip hidden files/dirs
                        continue
                        
                    if entry.is_file():
                        file_node = FileNode(
                            name=entry.name,
                            path=entry,
                            size_bytes=entry.stat().st_size,
                            last_modified=datetime.fromtimestamp(entry.stat().st_mtime),
                            extension=entry.suffix.lower(),
                            content_type=self._determine_content_type(entry),
                            language=None  # Will be set later
                        )
                        node.add_file(file_node)
                    
                    elif entry.is_dir():
                        subnode = _build_node(entry)
                        node.add_directory(subnode)
                
            except PermissionError as e:
                self.logger.warning(f"Permission denied accessing {path}: {e}")
            except Exception as e:
                self.logger.error(f"Error processing {path}: {e}")
            
            return node

        root_node = _build_node(self.repo_path)
        tree = DirectoryTree(root=root_node)
        tree.calculate_stats()
        return tree

    def _detect_languages(self, directory_tree: DirectoryTree) -> Dict[str, int]:
        """Detect programming languages used in the repository."""
        if not self._language_detector:
            from .language_detection import LanguageDetector
            self._language_detector = LanguageDetector()
        
        return self._language_detector.detect_languages(directory_tree)

    def _parse_code_files(self, directory_tree: DirectoryTree) -> List[ModuleElement]:
        """Parse all code files in the repository."""
        modules = []
        for file_node in self._get_code_files(directory_tree):
            try:
                parser = self._get_parser_for_language(file_node.language)
                if parser:
                    module = parser.parse_file(file_node.path)
                    modules.append(module)
            except Exception as e:
                self.logger.error(f"Error parsing {file_node.path}: {e}")
        return modules

    def _parse_documentation_files(self, directory_tree: DirectoryTree) -> List[DocumentationElement]:
        """Parse documentation files."""
        if not self._documentation_parser:
            from .documentation_parser import DocumentationParser
            self._documentation_parser = DocumentationParser()
        
        docs = []
        for file_node in self._get_documentation_files(directory_tree):
            try:
                doc = self._documentation_parser.parse_file(file_node.path)
                docs.append(doc)
            except Exception as e:
                self.logger.error(f"Error parsing documentation {file_node.path}: {e}")
        return docs

    def _extract_metadata(self) -> tuple[List[ContributorData], List[CommitData]]:
        """Extract Git metadata including commits and contributors."""
        if not self._metadata_extractor:
            from .metadata_extractor import MetadataExtractor
            self._metadata_extractor = MetadataExtractor(self.repo_path)
        
        return self._metadata_extractor.extract_metadata()

    def _determine_content_type(self, path: Path) -> str:
        """Determine the content type of a file."""
        if not self._file_classifier:
            from .file_classifier import FileClassifier
            self._file_classifier = FileClassifier()
        
        return self._file_classifier.classify_file(path)

    def _get_repository_url(self) -> str:
        """Get the repository's remote URL."""
        try:
            import git
            repo = git.Repo(self.repo_path)
            return next(repo.remote().urls, '')
        except Exception as e:
            self.logger.warning(f"Could not determine repository URL: {e}")
            return ''

    def _determine_primary_language(self, languages: Dict[str, int]) -> str:
        """Determine the primary programming language used in the repository."""
        if not languages:
            return 'unknown'
        return max(languages.items(), key=lambda x: x[1])[0]

    def _get_creation_date(self, commits: List[CommitData]) -> Optional[datetime]:
        """Get repository creation date from first commit."""
        if not commits:
            return None
        return min(commit.date for commit in commits)

    def _get_last_update_date(self, commits: List[CommitData]) -> Optional[datetime]:
        """Get repository last update date from latest commit."""
        if not commits:
            return None
        return max(commit.date for commit in commits)

    def _get_code_files(self, directory_tree: DirectoryTree) -> List[FileNode]:
        """Get all code files from the directory tree."""
        return [
            file for file in directory_tree.root.get_all_files()
            if file.is_code
        ]

    def _get_documentation_files(self, directory_tree: DirectoryTree) -> List[FileNode]:
        """Get all documentation files from the directory tree."""
        return [
            file for file in directory_tree.root.get_all_files()
            if file.is_documentation
        ]

    def _get_parser_for_language(self, language: str):
        """Get the appropriate parser for a given language."""
        from .parser_factory import ParserFactory
        return ParserFactory.get_parser(language)