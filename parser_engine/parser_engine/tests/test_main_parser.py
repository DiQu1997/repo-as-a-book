"""
Tests for the MainParserEngine.
"""

import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

from ..core.main_parser import MainParserEngine
from ..models.data_models import (
    RepositoryData, DirectoryTree, DirectoryNode, FileNode,
    ModuleElement, DocumentationElement
)

class TestMainParserEngine(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory structure for testing
        self.test_repo_path = Path("test_repo")
        self.parser = MainParserEngine(str(self.test_repo_path))
        
        # Mock dependencies
        self.parser._language_detector = Mock()
        self.parser._file_classifier = Mock()
        self.parser._metadata_extractor = Mock()
        self.parser._documentation_parser = Mock()

    def test_initialization(self):
        """Test parser initialization."""
        self.assertEqual(self.parser.repo_path, self.test_repo_path)
        self.assertIsNotNone(self.parser.logger)

    def test_invalid_repository_path(self):
        """Test initialization with invalid repository path."""
        with self.assertRaises(ValueError):
            MainParserEngine("nonexistent_path")

    def test_parse_repository(self):
        """Test the complete repository parsing process."""
        # Mock the component responses
        self.parser._build_directory_tree = Mock(return_value=DirectoryTree(
            root=DirectoryNode(name="test", path=self.test_repo_path)
        ))
        self.parser._detect_languages = Mock(return_value={"Python": 1000})
        self.parser._parse_code_files = Mock(return_value=[])
        self.parser._parse_documentation_files = Mock(return_value=[])
        self.parser._extract_metadata = Mock(return_value=([], []))
        
        # Execute parsing
        result = self.parser.parse_repository()
        
        # Verify result
        self.assertIsInstance(result, RepositoryData)
        self.assertEqual(result.name, self.test_repo_path.name)
        self.assertEqual(result.primary_language, "Python")

    # Add more test methods for other functionality...

if __name__ == '__main__':
    unittest.main()