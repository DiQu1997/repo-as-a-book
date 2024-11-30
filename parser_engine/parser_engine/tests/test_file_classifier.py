import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

from ..utils.file_classifier import FileClassifier

class TestFileClassifier:
    @pytest.fixture
    def classifier(self):
        return FileClassifier()

    def test_classify_code_files(self, classifier):
        """Test classification of code files"""
        code_files = [
            "test.py",
            "main.cpp",
            "app.js",
            "index.html",
            "styles.css"
        ]
        
        for filename in code_files:
            path = Path(f"/test/{filename}")
            assert classifier.classify_file(path) == "code"

    def test_classify_documentation_files(self, classifier):
        """Test classification of documentation files"""
        doc_files = [
            "README.md",
            "CONTRIBUTING.rst",
            "docs.txt",
            "api.wiki",
            "guide.adoc"
        ]
        
        for filename in doc_files:
            path = Path(f"/test/{filename}")
            assert classifier.classify_file(path) == "documentation"

    def test_classify_configuration_files(self, classifier):
        """Test classification of configuration files"""
        config_files = [
            "config.json",
            "settings.yml",
            ".env",
            "setup.cfg",
            "webpack.config.js"
        ]
        
        for filename in config_files:
            path = Path(f"/test/{filename}")
            assert classifier.classify_file(path) == "configuration"

    @patch('mimetypes.guess_type')
    def test_binary_file_detection(self, mock_guess_type, classifier):
        """Test detection of binary files"""
        mock_guess_type.return_value = ('application/octet-stream', None)
        
        with patch('builtins.open', mock_open(read_data=b'\x00\x01\x02\x03')):
            path = Path("/test/binary.bin")
            assert classifier.classify_file(path) == "binary"

    def test_ignored_files(self, classifier):
        """Test detection of files that should be ignored"""
        ignored_files = [
            ".git/config",
            "__pycache__/module.pyc",
            "node_modules/package/index.js",
            ".DS_Store"
        ]
        
        for filename in ignored_files:
            path = Path(filename)
            assert classifier.classify_file(path) == "ignored"

    @patch('builtins.open', new_callable=mock_open, 
           read_data='# Documentation\n## Overview\nThis is a guide.')
    def test_documentation_content_detection(self, mock_file, classifier):
        """Test detection of documentation based on content"""
        path = Path("/test/guide")  # No extension
        assert classifier.classify_file(path) == "documentation"

    @patch('builtins.open', new_callable=mock_open, 
           read_data='[settings]\nkey=value')
    def test_configuration_content_detection(self, mock_file, classifier):
        """Test detection of configuration based on content"""
        path = Path("/test/config")  # No extension
        assert classifier.classify_file(path) == "configuration"

    def test_error_handling(self, classifier):
        """Test error handling for problematic files"""
        # Test with non-existent file
        path = Path("/nonexistent/file.txt")
        assert classifier.classify_file(path) == "other"
        
        # Test with permission error
        with patch('builtins.open', side_effect=PermissionError):
            path = Path("/test/restricted.txt")
            assert classifier.classify_file(path) == "other"

    def test_special_cases(self, classifier):
        """Test classification of special case files"""
        special_cases = {
            "Dockerfile": "configuration",
            "Makefile": "build",
            "requirements.txt": "configuration",
            "LICENSE": "documentation",
            ".gitignore": "configuration"
        }
        
        for filename, expected_type in special_cases.items():
            path = Path(f"/test/{filename}")
            assert classifier.classify_file(path) == expected_type

    @patch('builtins.open', side_effect=UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid'))
    def test_unicode_error_handling(self, mock_open, classifier):
        """Test handling of files with encoding errors"""
        path = Path("/test/binary.data")
        assert classifier.classify_file(path) == "binary"

    def test_nested_paths(self, classifier):
        """Test classification of files in nested directories"""
        test_paths = {
            "src/main.py": "code",
            "docs/api/reference.md": "documentation",
            "config/prod/settings.json": "configuration",
            "build/lib/binary.so": "binary"
        }
        
        for path_str, expected_type in test_paths.items():
            path = Path(path_str)
            assert classifier.classify_file(path) == expected_type

    @pytest.mark.parametrize("filename,expected_type", [
        ("test.unknown", "other"),
        ("noextension", "other"),
        (".", "other"),
        ("", "other")
    ])
    def test_edge_cases(self, classifier, filename, expected_type):
        """Test classification of edge cases"""
        path = Path(f"/test/{filename}")
        assert classifier.classify_file(path) == expected_type