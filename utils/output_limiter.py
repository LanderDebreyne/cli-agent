"""
Output Limiter for AgentCLI Tools

This module provides utilities for limiting the size of tool outputs
to prevent token explosions in the agent's context.
"""

import logging
from typing import Any, Dict, List, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("output_limiter")

class OutputLimiter:
    """Utility for limiting the size of tool outputs"""
    
    @staticmethod
    def truncate_text(text: str, max_chars: int = 10000, add_note: bool = True) -> str:
        """Truncate text to a maximum number of characters
        
        Args:
            text: The text to truncate
            max_chars: Maximum number of characters
            add_note: Whether to add a note about truncation
            
        Returns:
            Truncated text
        """
        if len(text) <= max_chars:
            return text
            
        truncated = text[:max_chars]
        
        if add_note:
            note = f"\n\n[Output truncated to {max_chars} characters. Original length: {len(text)} characters]"
            # Make sure we have room for the note
            truncated = truncated[:max_chars - len(note)] + note
            
        return truncated
    
    @staticmethod
    def limit_file_matches(matches: List[Dict[str, Any]], max_matches: int = 10) -> List[Dict[str, Any]]:
        """Limit the number of file matches
        
        Args:
            matches: List of file matches
            max_matches: Maximum number of matches to return
            
        Returns:
            Limited list of matches
        """
        if len(matches) <= max_matches:
            return matches
            
        return matches[:max_matches]
    
    @staticmethod
    def limit_content_matches(results: Dict[str, List[Dict[str, Any]]], max_total_matches: int = 50, max_matches_per_file: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Limit the number of content matches
        
        Args:
            results: Dictionary of file paths to matching lines
            max_total_matches: Maximum total number of matches
            max_matches_per_file: Maximum number of matches per file
            
        Returns:
            Limited results
        """
        limited_results = {}
        total_matches = 0
        
        for file_path, matches in results.items():
            # Limit matches per file
            file_matches = matches[:max_matches_per_file]
            limited_results[file_path] = file_matches
            
            total_matches += len(file_matches)
            
            # Stop if we've reached the maximum total matches
            if total_matches >= max_total_matches:
                break
                
        return limited_results
    
    @staticmethod
    def format_file_search_results(results: List[Dict[str, Any]], query: str, max_chars: int = 5000) -> str:
        """Format file search results with size limiting
        
        Args:
            results: List of file matches
            query: The search query
            max_chars: Maximum number of characters in the output
            
        Returns:
            Formatted results
        """
        if not results:
            return f"No files found matching '{query}'"
            
        content = f"Found {len(results)} files matching '{query}':\n\n"
        
        for i, result in enumerate(results, 1):
            line = f"{i}. {result['path']} (Score: {result['score']})\n"
            
            # Check if adding this line would exceed the limit
            if len(content) + len(line) > max_chars:
                remaining = len(results) - i + 1
                content += f"\n[{remaining} more matches not shown due to output size limit]"
                break
                
            content += line
            
        return content
    
    @staticmethod
    def format_content_search_results(results: Dict[str, List[Dict[str, Any]]], query: str, max_chars: int = 10000) -> str:
        """Format content search results with size limiting
        
        Args:
            results: Dictionary of file paths to matching lines
            query: The search query
            max_chars: Maximum number of characters in the output
            
        Returns:
            Formatted results
        """
        if not results:
            return f"No content matches found for '{query}'"
            
        total_matches = sum(len(matches) for matches in results.values())
        content = f"Found {total_matches} matches for '{query}' in {len(results)} files:\n\n"
        
        files_shown = 0
        matches_shown = 0
        total_files = len(results)
        
        for file_path, matches in results.items():
            file_header = f"File: {file_path} ({len(matches)} matches)\n"
            
            # Check if adding the file header would exceed the limit
            if len(content) + len(file_header) > max_chars:
                remaining_files = total_files - files_shown
                content += f"\n[{remaining_files} more files with matches not shown due to output size limit]"
                break
                
            content += file_header
            files_shown += 1
            
            for match in matches:
                match_content = f"  Line {match['line_number']}: {match['content']}\n"
                match_content += "  Context:\n"
                
                for ctx in match['context']:
                    prefix = "  > " if ctx['is_match'] else "    "
                    match_content += f"{prefix}Line {ctx['line_number']}: {ctx['content']}\n"
                
                match_content += "\n"
                
                # Check if adding this match would exceed the limit
                if len(content) + len(match_content) > max_chars:
                    remaining_matches = total_matches - matches_shown
                    content += f"  [... and {remaining_matches} more matches not shown due to output size limit]\n"
                    break
                    
                content += match_content
                matches_shown += 1
                
        return content 