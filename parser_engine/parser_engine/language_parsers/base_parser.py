"""
Base parser interface for all language-specific parsers.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional
import logging

from ..models.data_models import (
    ModuleElement, ClassElement, FunctionElement, DocumentationElement
)

class BaseParser(ABC):
    """Abstract base class for language parsers."""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def parse_file(self, path: Path) -> ModuleElement:
        """
        Parse a single file and return its module representation.
        
        Args:
            path: Path to the file to parse
            
        Returns:
            ModuleElement containing the parsed file information
        """
        pass

    def parse_directory(self, path: Path) -> List[ModuleElement]:
        """
        Parse all relevant files in a directory.
        
        Args:
            path: Path to the directory
            
        Returns:
            List of ModuleElements for each parsed file
        """
        modules = []
        for file_path in path.rglob('*'):
            if file_path.is_file() and self.can_parse(file_path):
                try:
                    module = self.parse_file(file_path)
                    modules.append(module)
                except Exception as e:
                    self.logger.error(f"Error parsing {file_path}: {e}")
        return modules

    @abstractmethod
    def can_parse(self, path: Path) -> bool:
        """
        Check if this parser can handle the given file.
        
        Args:
            path: Path to the file
            
        Returns:
            True if this parser can handle the file, False otherwise
        """
        pass
        
    def get_supported_extensions(self) -> List[str]:
        """
        Get list of file extensions this parser supports.
        
        Returns:
            List of supported file extensions with dots (e.g., ['.py', '.pyw'])
        """
        return []

    def _create_error_module(self, path: Path, error: Exception) -> ModuleElement:
        """
        Create a ModuleElement representing a parsing error.
        
        Args:
            path: Path to the file that failed to parse
            error: Exception that occurred
            
        Returns:
            ModuleElement with error information
        """
        return ModuleElement(
            name=path.name,
            path=path,
            language=self.language,
            error=str(error)
        )