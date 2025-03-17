"""
Path Validator for AgentCLI Tools

This module provides shared functionality for path validation, ignore patterns,
and allowed folders logic used by multiple tools.
"""

import os
import logging
import fnmatch
import pathlib
from typing import List, Optional, Tuple

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("path_validator")

class PathValidator:
    """Shared path validation logic for AgentCLI tools"""
    
    def __init__(self, allowed_folders: Optional[List[str]] = None, toolignore_path: str = ".toolignore", repo_path: str = "."):
        """Initialize the path validator
        
        Args:
            allowed_folders: List of folders the tools are allowed to access (None means all folders)
            toolignore_path: Path to the .toolignore file
            repo_path: Path to the repository (default: current directory)
        """
        self.allowed_folders = allowed_folders or []
        self.repo_path = os.path.abspath(repo_path)
        self.toolignore_path = os.path.join(self.repo_path, toolignore_path) if not os.path.isabs(toolignore_path) else toolignore_path
        self.ignore_patterns = self._load_ignore_patterns()
        
    def _load_ignore_patterns(self) -> List[str]:
        """Load ignore patterns from .toolignore file
        
        Returns:
            List of ignore patterns
        """
        patterns = []
        if os.path.exists(self.toolignore_path):
            try:
                with open(self.toolignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # Skip empty lines and comments
                        if line and not line.startswith('#'):
                            patterns.append(line)
                logger.info(f"Loaded {len(patterns)} ignore patterns from {self.toolignore_path}")
            except Exception as e:
                logger.error(f"Error loading ignore patterns: {str(e)}")
        return patterns
    
    def is_path_ignored(self, path: str) -> bool:
        """Check if a path matches any ignore pattern
        
        Args:
            path: Path to check
            
        Returns:
            True if the path should be ignored, False otherwise
        """
        # Normalize path for matching
        norm_path = os.path.normpath(path)
        
        # Check each pattern
        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(norm_path, pattern):
                logger.info(f"Path {path} matches ignore pattern {pattern}")
                return True
                
            # Also check if any parent directory matches
            parts = pathlib.Path(norm_path).parts
            for i in range(1, len(parts) + 1):
                partial_path = os.path.join(*parts[:i])
                if fnmatch.fnmatch(partial_path, pattern):
                    logger.info(f"Parent path {partial_path} matches ignore pattern {pattern}")
                    return True
        
        return False
    
    def is_path_allowed(self, path: str) -> bool:
        """Check if a path is in the allowed folders
        
        Args:
            path: Path to check
            
        Returns:
            True if the path is allowed, False otherwise
        """
        # Normalize path for matching
        norm_path = os.path.normpath(path)
        
        # Get the repository directory
        repo_dir = self.repo_path
        
        # Files in the repository directory are always allowed (if not ignored)
        if norm_path == repo_dir or norm_path == '.':
            return True
            
        # Files directly in the repository directory are always allowed (if not ignored)
        if os.path.dirname(norm_path) == '' or os.path.dirname(norm_path) == '.':
            return True
            
        # Check if the path is a subdirectory of the repository directory
        try:
            # Use os.path.relpath to check if the path is relative to the repository directory
            rel_path = os.path.relpath(norm_path, repo_dir)
            # If the relative path doesn't start with '..' then it's within the repository directory
            if not rel_path.startswith('..'):
                return True
        except ValueError:
            # This can happen if the paths are on different drives (Windows)
            pass
            
        # If no additional allowed folders are specified, only the repository directory is allowed
        if not self.allowed_folders:
            logger.warning(f"Path {path} is not in the repository directory and no additional allowed folders are specified")
            return False
            
        # Check if the path is in any of the allowed folders
        for allowed_folder in self.allowed_folders:
            # Make the allowed folder path absolute if it's relative
            if not os.path.isabs(allowed_folder):
                allowed_path = os.path.normpath(os.path.join(self.repo_path, allowed_folder))
            else:
                allowed_path = os.path.normpath(allowed_folder)
            
            # Check if the path is the allowed folder or a subfolder
            if norm_path == allowed_path or norm_path.startswith(allowed_path + os.sep):
                return True
                
            # Also check if the path is relative to the allowed folder
            try:
                rel_to_allowed = os.path.relpath(norm_path, allowed_path)
                if not rel_to_allowed.startswith('..'):
                    return True
            except ValueError:
                # This can happen if the paths are on different drives (Windows)
                pass
        
        logger.warning(f"Path {path} is not in the repository directory or allowed folders: {self.allowed_folders}")
        return False
    
    def validate_path(self, path: str) -> Tuple[bool, str]:
        """Validate a file path to prevent directory traversal
        
        Args:
            path: The file path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Normalize the path to handle different path separators
        original_path = path
        
        # Handle paths starting with a slash
        if path.startswith('/'):
            path = path[1:] if len(path) > 1 else '.'
        
        # If the path is not absolute, make it relative to the repository path
        if not os.path.isabs(path):
            path = os.path.join(self.repo_path, path)
        
        # Normalize the path to resolve any '..' components
        norm_path = os.path.normpath(path)
        
        # Check for path traversal attempts (going up directories)
        if '..' in norm_path.split(os.sep):
            return False, f"Path traversal not allowed: {original_path}"
        
        # Check if path is ignored by .toolignore
        if self.is_path_ignored(norm_path):
            return False, f"Path is ignored by .toolignore: {norm_path}"
        
        # Check if path is in allowed folders
        if not self.is_path_allowed(norm_path):
            return False, f"Path is not in allowed folders: {norm_path}"
            
        return True, norm_path
    
    def get_all_files(self, directory: str = '.') -> List[str]:
        """Get all files in a directory and its subdirectories
        
        Args:
            directory: The directory to search in
            
        Returns:
            List of file paths
        """
        # If the directory is not absolute, make it relative to the repository path
        if not os.path.isabs(directory):
            directory = os.path.join(self.repo_path, directory)
            
        all_files = []
        
        for root, dirs, files in os.walk(directory):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if not self.is_path_ignored(os.path.join(root, d))]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip ignored files
                if self.is_path_ignored(file_path):
                    continue
                    
                # Check if file is in allowed folders
                if not self.is_path_allowed(file_path):
                    continue
                    
                all_files.append(file_path)
                
        return all_files 