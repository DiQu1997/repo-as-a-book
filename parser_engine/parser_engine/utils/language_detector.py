"""
Language detection module for identifying programming languages and build systems in a repository.
"""

from pathlib import Path
from typing import Dict, Set, Optional, Tuple
import logging
import re

class LanguageDetector:
    """
    Detects programming languages and build systems used in repository files.
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Map of file extensions to programming languages
        self._extension_map = {
            # Common programming languages
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.cs': 'C#',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.go': 'Go',
            '.rs': 'Rust',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            
            # Web technologies
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.sass': 'SASS',
            '.jsx': 'React',
            '.tsx': 'React',
            '.vue': 'Vue',
            
            # Shell scripts
            '.sh': 'Shell',
            '.bash': 'Shell',
            '.zsh': 'Shell',
            
            # Data formats
            '.sql': 'SQL',
            '.r': 'R',
            '.json': 'JSON',
            '.yml': 'YAML',
            '.yaml': 'YAML',
            '.xml': 'XML',
            '.proto': 'Protobuf',
        }
        
        # Build system and infrastructure files
        self._build_systems = {
            # Make
            'makefile': 'Makefile',
            'gnumakefile': 'Makefile',
            'kbuild': 'Makefile',
            
            # CMake
            'cmakelists.txt': 'CMake',
            'cmakefile': 'CMake',
            
            # Gradle
            'build.gradle': 'Gradle',
            'build.gradle.kts': 'Gradle',
            'settings.gradle': 'Gradle',
            'settings.gradle.kts': 'Gradle',
            
            # Maven
            'pom.xml': 'Maven',
            
            # Ant
            'build.xml': 'Ant',
            
            # Bazel
            'build.bazel': 'Bazel',
            'workspace.bazel': 'Bazel',
            'build': 'Bazel',
            'workspace': 'Bazel',
            
            # NPM/Node.js
            'package.json': 'NPM',
            'package-lock.json': 'NPM',
            
            # Python
            'setup.py': 'Python-Build',
            'requirements.txt': 'Python-Build',
            'pyproject.toml': 'Python-Build',
            'poetry.lock': 'Python-Build',
            
            # Docker
            'dockerfile': 'Docker',
            'docker-compose.yml': 'Docker',
            'docker-compose.yaml': 'Docker',
            
            # Other build systems
            'rakefile': 'Rake',
            'gruntfile.js': 'Grunt',
            'gulpfile.js': 'Gulp',
            'webpack.config.js': 'Webpack',
        }
        
        # Languages that might need content verification
        self._ambiguous_extensions = {'.h', '.txt', '.in'}

        # Language-specific comment patterns
        self._comment_patterns = {
            'Python': {
                'single_line': ['#'],
                'multi_line': ['"""', "'''"],
                'nested_allowed': True  # Python allows nested multi-line comments
            },
            'JavaScript': {
                'single_line': ['//'],
                'multi_line': [('/*', '*/')],
                'nested_allowed': False
            },
            'TypeScript': {
                'single_line': ['//'],
                'multi_line': [('/*', '*/')],
                'nested_allowed': False
            },
            'Java': {
                'single_line': ['//'],
                'multi_line': [('/*', '*/')],
                'nested_allowed': False
            },
            'C': {
                'single_line': ['//'],
                'multi_line': [('/*', '*/')],
                'nested_allowed': False
            },
            'C++': {
                'single_line': ['//'],
                'multi_line': [('/*', '*/')],
                'nested_allowed': False
            },
            'Ruby': {
                'single_line': ['#'],
                'multi_line': [('=begin', '=end')],
                'nested_allowed': False
            },
            'PHP': {
                'single_line': ['//','#'],
                'multi_line': [('/*', '*/'), ('/**', '*/')],
                'nested_allowed': False
            },
            'Go': {
                'single_line': ['//'],
                'multi_line': [('/*', '*/')],
                'nested_allowed': False
            },
            'Shell': {
                'single_line': ['#'],
                'multi_line': [],
                'nested_allowed': False
            },
            'SQL': {
                'single_line': ['--'],
                'multi_line': [('/*', '*/')],
                'nested_allowed': False
            },
            'HTML': {
                'single_line': [],
                'multi_line': [('<!--', '-->')],
                'nested_allowed': False
            },
            'CSS': {
                'single_line': [],
                'multi_line': [('/*', '*/')],
                'nested_allowed': False
            },
            'Makefile': {
                'single_line': ['#'],
                'multi_line': [],
                'nested_allowed': False
            },
            'CMake': {
                'single_line': ['#'],
                'multi_line': [('#[[', ']]')],
                'nested_allowed': True
            }
        }
        
    def detect_languages(self, directory_tree) -> Tuple[Dict[str, int], Dict[str, int]]:
        """
        Detect programming languages and build systems used in the repository.
        
        Args:
            directory_tree: DirectoryTree object representing the repository structure
            
        Returns:
            Tuple of (language_stats, build_system_stats) where each is a Dict mapping
            names to lines of code/occurrences
        """
        language_stats = {}
        build_system_stats = {}
        
        def process_file(file_node) -> None:
            # Check for build systems first
            build_system = self._detect_build_system(file_node)
            if build_system:
                build_system_stats[build_system] = build_system_stats.get(build_system, 0) + 1
                file_node.language = build_system
                file_node.content_type = 'build'
                return
                
            # Then check for programming languages
            if file_node.extension:
                language = self._detect_language(file_node)
                if language:
                    lines = self._count_code_lines(file_node.path)
                    if lines > 0:
                        language_stats[language] = language_stats.get(language, 0) + lines
                        file_node.language = language
                        file_node.lines_of_code = lines
        
        # Process all files in the directory tree
        for file_node in directory_tree.root.get_all_files():
            try:
                process_file(file_node)
            except Exception as e:
                self.logger.error(f"Error processing {file_node.path}: {e}")
        
        return language_stats, build_system_stats
    
    def _detect_build_system(self, file_node) -> Optional[str]:
        """
        Detect if a file is part of a build system.
        
        Args:
            file_node: FileNode object representing the file
            
        Returns:
            Build system name or None
        """
        filename = file_node.name.lower()
        
        # Direct filename match
        if filename in self._build_systems:
            return self._build_systems[filename]
            
        # Check for Makefile variants (they might not have extensions)
        if filename.startswith('makefile.'):
            return 'Makefile'
            
        # Check for CMake module files
        if filename.endswith('.cmake'):
            return 'CMake'
            
        # Additional build system detection based on content
        if filename.endswith(('.in', '.ac', '.am')):
            return self._analyze_build_content(file_node.path)
            
        return None
    
    def _analyze_build_content(self, file_path: Path) -> Optional[str]:
        """
        Analyze file content to determine the build system type.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Build system name or None
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read(1024)  # Read first 1KB for analysis
                
            # Autotools detection
            if 'AC_INIT' in content or 'AM_INIT' in content:
                return 'Autotools'
                
            # CMake detection
            if re.search(r'cmake_minimum_required|project\s*\(', content, re.I):
                return 'CMake'
                
            # Makefile detection
            if re.search(r'^\w+\s*:.*\n\t.*$', content, re.M):
                return 'Makefile'
                
        except Exception as e:
            self.logger.warning(f"Error analyzing build content of {file_path}: {e}")
            
        return None
    
    def _detect_language(self, file_node) -> Optional[str]:
        """Rest of the method remains the same"""
        extension = file_node.extension.lower()
        
        # Direct extension mapping
        if extension in self._extension_map:
            return self._extension_map[extension]
            
        # Handle ambiguous extensions
        if extension in self._ambiguous_extensions:
            return self._analyze_content(file_node.path)
            
        return None
    
    def _count_code_lines(self, file_path: Path, language: str) -> int:
        """
        Count lines of code in a file, properly handling language-specific comments.
        
        Args:
            file_path: Path to the file
            language: Programming language of the file
            
        Returns:
            Number of lines of code
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Get language-specific comment patterns
            patterns = self._comment_patterns.get(language, {
                'single_line': [],
                'multi_line': [],
                'nested_allowed': False
            })

            # Remove string literals to avoid false positives
            content = self._mask_string_literals(content, language)
            
            # Handle multi-line comments first
            if patterns['multi_line']:
                content = self._remove_multi_line_comments(
                    content, 
                    patterns['multi_line'],
                    patterns['nested_allowed']
                )

            # Split into lines and handle single-line comments
            lines = content.split('\n')
            code_lines = []
            
            for line in lines:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                    
                # Check for single-line comments
                is_comment = False
                for comment_start in patterns['single_line']:
                    if line.strip().startswith(comment_start):
                        is_comment = True
                        break
                
                if not is_comment:
                    code_lines.append(line)

            return len(code_lines)
            
        except Exception as e:
            self.logger.warning(f"Error counting lines in {file_path}: {e}")
            return 0

    def _mask_string_literals(self, content: str, language: str) -> str:
        """
        Mask string literals to avoid false positives in comment detection.
        
        Args:
            content: File content
            language: Programming language
            
        Returns:
            Content with string literals masked
        """
        import re
        
        # Language-specific string patterns
        string_patterns = {
            'Python': [
                r'"""(?:[^"]|\\")*"""',  # Triple double quotes
                r"'''(?:[^']|\\')*'''",  # Triple single quotes
                r'"(?:[^"\\]|\\.)*"',    # Double quotes
                r"'(?:[^'\\]|\\.)*'"     # Single quotes
            ],
            'C++': [
                r'"(?:[^"\\]|\\.)*"',    # Double quotes
                r"'(?:[^'\\]|\\.)*'"     # Single quotes
            ],
            'C': [
                r'"(?:[^"\\]|\\.)*"',    # Double quotes
                r"'(?:[^'\\]|\\.)*'"     # Single quotes
            ],
            'Java': [
                r'"(?:[^"\\]|\\.)*"',    # Double quotes
                r"'(?:[^'\\]|\\.)*'"     # Single quotes
            ],
            'R': [
                r'"(?:[^"\\]|\\.)*"',    # Double quotes
                r"'(?:[^'\\]|\\.)*'"     # Single quotes
            ],
            'Rust': [
                r'"(?:[^"\\]|\\.)*"',    # Double quotes
                r"'(?:[^'\\]|\\.)*'"     # Single quotes
            ],
            "Go": [
                r'"(?:[^"\\]|\\.)*"',    # Double quotes
                r"'(?:[^'\\]|\\.)*'"     # Single quotes
            ],
            # Add patterns for other languages as needed
        }
        
        patterns = string_patterns.get(language, [r'"(?:[^"\\]|\\.)*"'])  # Default to simple strings
        
        # Replace string literals with placeholder
        masked_content = content
        for pattern in patterns:
            masked_content = re.sub(pattern, '', masked_content)
            
        return masked_content

    def _remove_multi_line_comments(self, content: str, patterns: list, nested_allowed: bool) -> str:
        """
        Remove multi-line comments from the content.
        
        Args:
            content: File content
            patterns: List of multi-line comment patterns
            nested_allowed: Whether nested comments are allowed
            
        Returns:
            Content with multi-line comments removed
        """
        for pattern in patterns:
            if isinstance(pattern, tuple):  # Start/end style comments (/* */)
                start, end = pattern
                if nested_allowed:
                    # Handle nested comments for languages like CMake
                    nesting_level = 0
                    result = []
                    i = 0
                    while i < len(content):
                        if content[i:].startswith(start):
                            nesting_level += 1
                            i += len(start)
                        elif content[i:].startswith(end):
                            nesting_level -= 1
                            i += len(end)
                        elif nesting_level == 0:
                            result.append(content[i])
                            i += 1
                        else:
                            i += 1
                    content = ''.join(result)
                else:
                    # Simple non-nested comment removal
                    import re
                    pattern = f'{re.escape(start)}.*?{re.escape(end)}'
                    content = re.sub(pattern, '', content, flags=re.DOTALL)
            else:  # Python-style comments (""")
                # Handle simple multi-line comments
                parts = content.split(pattern)
                if len(parts) > 1:
                    content = ''.join(parts[::2])  # Take every other part

        return content