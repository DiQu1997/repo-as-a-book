import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

from ..utils.language_detector import LanguageDetector
from ..models.data_models import FileNode, DirectoryNode, DirectoryTree

class TestLanguageDetector:
    @pytest.fixture
    def detector(self):
        return LanguageDetector()
        
    @pytest.fixture
    def mock_directory_tree(self):
        """Create a mock directory tree with various file types"""
        root = DirectoryNode(
            name="test_repo",
            path=Path("/test_repo"),
            files=[
                FileNode(
                    name="main.py",
                    path=Path("/test_repo/main.py"),
                    size_bytes=100,
                    last_modified=datetime.now(),
                    extension=".py",
                    content_type="code"
                ),
                FileNode(
                    name="app.js",
                    path=Path("/test_repo/app.js"),
                    size_bytes=100,
                    last_modified=datetime.now(),
                    extension=".js",
                    content_type="code"
                ),
                FileNode(
                    name="CMakeLists.txt",
                    path=Path("/test_repo/CMakeLists.txt"),
                    size_bytes=100,
                    last_modified=datetime.now(),
                    extension=".txt",
                    content_type="build"
                )
            ]
        )
        return DirectoryTree(root=root)

    def test_detect_common_languages(self, detector):
        """Test detection of common programming languages"""
        test_files = {
            "test.py": "Python",
            "test.js": "JavaScript",
            "test.java": "Java",
            "test.cpp": "C++",
            "test.rb": "Ruby",
            "test.go": "Go"
        }
        
        for filename, expected_language in test_files.items():
            file_node = FileNode(
                name=filename,
                path=Path(f"/test/{filename}"),
                size_bytes=100,
                last_modified=datetime.now(),
                extension=Path(filename).suffix,
                content_type="code"
            )
            assert detector._detect_language(file_node) == expected_language

    def test_detect_build_systems(self, detector):
        """Test detection of build system files"""
        test_files = {
            "Makefile": "Makefile",
            "CMakeLists.txt": "CMake",
            "build.gradle": "Gradle",
            "pom.xml": "Maven",
            "package.json": "NPM"
        }
        
        for filename, expected_system in test_files.items():
            file_node = FileNode(
                name=filename,
                path=Path(f"/test/{filename}"),
                size_bytes=100,
                last_modified=datetime.now(),
                extension=Path(filename).suffix,
                content_type="build"
            )
            assert detector._detect_build_system(file_node) == expected_system

    def test_count_code_lines_cpp(self, detector):
        """Test counting of code lines in C++ with different comment styles"""
        file_path = Path("/test/test.cpp")
        
        # Test basic code without comments
        with patch('builtins.open', new_callable=mock_open, 
                  read_data='int main() {\n    return 0;\n}') as mock_file:
            assert detector._count_code_lines(file_path, "C++") == 3
            
        # Test with single-line comment
        with patch('builtins.open', new_callable=mock_open,
                  read_data='// Single line comment\nint main() {\n    return 0;\n}') as mock_file:
            assert detector._count_code_lines(file_path, "C++") == 3
            
        # Test with multi-line comment
        with patch('builtins.open', new_callable=mock_open,
                  read_data='/* Multi-line\n comment */\nint main() {\n    return 0;\n}') as mock_file:
            assert detector._count_code_lines(file_path, "C++") == 3

        # Test with Python-style triple quotes in string literal
        with patch('builtins.open', new_callable=mock_open,
                  read_data='std::string s = """Python style quotes""";\nint main() {\n    return 0;\n}') as mock_file:
            assert detector._count_code_lines(file_path, "C++") == 4

    def test_count_code_lines_python_comments(self, detector):
        """Test counting of code lines with Python single-line and multi-line comments"""
        file_path = Path("/test/test.py")
        
        # Test single-line comments
        with patch('builtins.open', new_callable=mock_open,
                  read_data='# Single line comment\ndef main():\n    return 0') as mock_file:
            assert detector._count_code_lines(file_path, "Python") == 2
            
        # Test multi-line comments
        with patch('builtins.open', new_callable=mock_open,
                  read_data='"""\nMulti-line\ndocstring\n"""\ndef main():\n    return 0') as mock_file:
            assert detector._count_code_lines(file_path, "Python") == 2

    @patch('builtins.open', new_callable=mock_open, 
           read_data='#[[ Outer comment\n#[[ Nested comment ]]\nstill outer ]]\nadd_executable(main main.cpp)')
    def test_count_code_lines_cmake_nested_comments(self, mock_file, detector):
        """Test counting of code lines with CMake nested comments"""
        file_path = Path("/test/CMakeLists.txt")
        assert detector._count_code_lines(file_path, "CMake") == 1

    def test_detect_languages_integration(self, detector, mock_directory_tree):
        """Test complete language detection process"""
        with patch.object(detector, '_count_code_lines', return_value=10):
            lang_stats, build_stats = detector.detect_languages(mock_directory_tree)
            
            assert "Python" in lang_stats
            assert "JavaScript" in lang_stats
            assert "CMake" in build_stats
            assert lang_stats["Python"] == 10
            assert lang_stats["JavaScript"] == 10
            assert build_stats["CMake"] == 1

    @patch('builtins.open', new_callable=mock_open, 
           read_data='cmake_minimum_required(VERSION 3.10)\nproject(TestProject)')
    def test_analyze_build_content(self, mock_file, detector):
        """Test analysis of build system content"""
        file_path = Path("/test/CMakeLists.txt")
        assert detector._analyze_build_content(file_path) == "CMake"

    def test_error_handling(self, detector):
        """Test error handling for invalid files"""
        with patch('builtins.open', side_effect=IOError):
            file_path = Path("/nonexistent/file.py")
            assert detector._count_code_lines(file_path, "Python") == 0