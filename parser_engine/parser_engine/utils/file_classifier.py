"""
File classification module for determining file types in a repository.
"""

from pathlib import Path
from typing import Set, Dict
import logging
import mimetypes

class FileClassifier:
    """
    Classifies repository files into different categories based on extension and content.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Initialize file type mappings
        self._code_extensions = {
            '.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs',
            '.rb', '.php', '.go', '.rs', '.swift', '.kt', '.scala',
            '.html', '.css', '.scss', '.sass', '.jsx', '.tsx', '.vue'
        }
        
        self._doc_extensions = {
            '.md', '.rst', '.txt', '.doc', '.docx', '.pdf',
            '.adoc', '.wiki', '.org', '.rdoc'
        }
        
        self._config_extensions = {
            '.json', '.yml', '.yaml', '.xml', '.ini', '.conf',
            '.cfg', '.properties', '.env', '.toml'
        }
        
        self._ignore_patterns = {
            '.git', '__pycache__', 'node_modules', '.idea',
            '.vscode', '.DS_Store'
        }
        
    def classify_file(self, file_path: Path) -> str:
        """
        Classify a single file into a specific type.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Classification string: 'code', 'documentation', 'configuration', 'binary', or 'other'
        """
        try:
            # Check if file should be ignored
            if any(part in file_path.parts for part in self._ignore_patterns):
                return 'ignored'
                
            extension = file_path.suffix.lower()
            
            # Check if it's a binary file
            if self._is_binary_file(file_path):
                return 'binary'
                
            # Classify based on extension
            if extension in self._code_extensions:
                return 'code'
            elif extension in self._doc_extensions:
                return 'documentation'
            elif extension in self._config_extensions:
                return 'configuration'
                
            # Additional checks for files without clear extensions
            if self._is_documentation(file_path):
                return 'documentation'
            elif self._is_configuration(file_path):
                return 'configuration'
                
            return 'other'
            
        except Exception as e:
            self.logger.error(f"Error classifying {file_path}: {e}")
            return 'other'
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """
        Check if a file is binary.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is binary, False otherwise
        """
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and not mime_type.startswith(('text/', 'application/json')):
            return True
            
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return b'\0' in chunk
        except Exception:
            return False
    
    def _is_documentation(self, file_path: Path) -> bool:
        """
        Check if a file is documentation based on content patterns.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is documentation, False otherwise
        """
        try:
            if file_path.name.lower() in {'readme', 'contributing', 'changelog', 'license'}:
                return True
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(1024).lower()
                doc_patterns = {'# documentation', '## overview', '# introduction',
                              '# guide', '# tutorial', '# readme'}
                return any(pattern in content for pattern in doc_patterns)
                
        except Exception:
            return False
    
    def _is_configuration(self, file_path: Path) -> bool:
        """
        Check if a file is configuration based on content patterns.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is configuration, False otherwise
        """
        try:
            config_filenames = {
                'config', 'settings', '.env', 'dockerfile', 'makefile',
                'requirements.txt', 'package.json', 'setup.cfg'
            }
            
            if file_path.stem.lower() in config_filenames:
                return True
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(1024).lower()
                config_patterns = {'config:', 'settings:', '[settings]', 'env ='}
                return any(pattern in content for pattern in config_patterns)
                
        except Exception:
            return False