"""
Search Tool for AgentCLI

This file implements the search tool for AgentCLI, providing:
1. Fuzzy file search - Find files by name using fuzzy matching
2. Content search - Search for text within files

The tool respects the same access rules and .toolignore patterns as the text editor tool.
"""

import os
import logging
import re
from typing import Dict, Any, List, Optional

# For fuzzy file search
from fuzzywuzzy import fuzz

# Import shared modules
from utils.path_validator import PathValidator
from utils.output_limiter import OutputLimiter

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("search_tool")

class SearchTool:
    """Implementation of the search tool for Claude"""
    
    def __init__(self, allowed_folders: Optional[List[str]] = None, toolignore_path: str = ".toolignore", repo_path: str = "."):
        """Initialize the search tool
        
        Args:
            allowed_folders: List of folders the tool is allowed to access (None means all folders)
            toolignore_path: Path to the .toolignore file
            repo_path: Path to the repository (default: current directory)
        """
        # Use the shared path validator
        self.path_validator = PathValidator(
            allowed_folders=allowed_folders,
            toolignore_path=toolignore_path,
            repo_path=repo_path
        )
        
        # Use the output limiter
        self.output_limiter = OutputLimiter()
    
    def _fuzzy_search_files(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search for files using fuzzy matching
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of matching files with scores
        """
        all_files = self.path_validator.get_all_files()
        
        # Use fuzzywuzzy to find the best matches
        matches = []
        for file_path in all_files:
            # Get the filename for matching
            filename = os.path.basename(file_path)
            
            # Calculate the match score
            score = fuzz.partial_ratio(query.lower(), filename.lower())
            
            # Add to matches if score is above threshold
            if score > 50:  # Adjust threshold as needed
                matches.append({
                    "path": file_path,
                    "score": score,
                    "filename": filename
                })
        
        # Sort by score (highest first)
        matches.sort(key=lambda x: x["score"], reverse=True)
        
        # Limit the number of matches
        return self.output_limiter.limit_file_matches(matches, max_results)
    
    def _search_file_content(self, query: str, file_path: str, case_sensitive: bool = False) -> List[Dict[str, Any]]:
        """Search for content within a file
        
        Args:
            query: The search query
            file_path: Path to the file to search
            case_sensitive: Whether the search should be case sensitive
            
        Returns:
            List of matching lines with context
        """
        matches = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                
            # Compile the regex pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(re.escape(query), flags)
            
            # Search each line
            for i, line in enumerate(lines):
                if pattern.search(line):
                    # Get context (lines before and after)
                    context_start = max(0, i - 2)
                    context_end = min(len(lines), i + 3)
                    
                    context = []
                    for j in range(context_start, context_end):
                        context.append({
                            "line_number": j + 1,
                            "content": lines[j].rstrip(),
                            "is_match": j == i
                        })
                    
                    matches.append({
                        "line_number": i + 1,
                        "content": line.rstrip(),
                        "context": context
                    })
        except Exception as e:
            logger.error(f"Error searching file {file_path}: {str(e)}")
            
        return matches
    
    def _search_content_in_files(self, query: str, directory: str = '.', case_sensitive: bool = False, max_results: int = 50, max_per_file: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Search for content in all files
        
        Args:
            query: The search query
            directory: The directory to search in
            case_sensitive: Whether the search should be case sensitive
            max_results: Maximum number of results to return
            max_per_file: Maximum number of results per file
            
        Returns:
            Dictionary of file paths to matching lines
        """
        all_files = self.path_validator.get_all_files(directory)
        results = {}
        total_matches = 0
        
        for file_path in all_files:
            # Skip binary files and very large files
            try:
                if os.path.getsize(file_path) > 1024 * 1024:  # Skip files larger than 1MB
                    continue
                    
                # Try to read the first few bytes to check if it's a text file
                with open(file_path, 'rb') as f:
                    is_binary = b'\0' in f.read(1024)
                    
                if is_binary:
                    continue
            except Exception:
                continue
                
            # Search the file
            file_matches = self._search_file_content(query, file_path, case_sensitive)
            
            # Limit matches per file
            if file_matches:
                file_matches = file_matches[:max_per_file]
                results[file_path] = file_matches
                total_matches += len(file_matches)
                
                # Stop if we've reached the maximum number of results
                if total_matches >= max_results:
                    break
                    
        # Limit the total number of matches
        return self.output_limiter.limit_content_matches(results, max_results, max_per_file)
    
    def handle_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a tool call from Claude
        
        Args:
            tool_call: The tool call from Claude
            
        Returns:
            The result of the tool call
        """
        input_params = tool_call.get("input", {})
        search_type = input_params.get("search_type", "")
        query = input_params.get("query", "")
        
        if not query:
            return {
                "tool_use_id": tool_call.get("id"),
                "content": "Error: query parameter is required",
                "is_error": True
            }
            
        try:
            if search_type == "fuzzy_file":
                # Fuzzy file search
                max_results = input_params.get("max_results", 10)
                results = self._fuzzy_search_files(query, max_results)
                
                # Format the results with size limiting
                content = self.output_limiter.format_file_search_results(results, query)
                    
            elif search_type == "content":
                # Content search
                directory = input_params.get("directory", ".")
                case_sensitive = input_params.get("case_sensitive", False)
                max_results = input_params.get("max_results", 50)
                max_per_file = input_params.get("max_per_file", 10)
                
                # Validate the directory
                is_valid, validated_dir = self.path_validator.validate_path(directory)
                if not is_valid:
                    return {
                        "tool_use_id": tool_call.get("id"),
                        "content": f"Error: Invalid directory: {validated_dir}",
                        "is_error": True
                    }
                
                # Search for content
                results = self._search_content_in_files(query, validated_dir, case_sensitive, max_results, max_per_file)
                
                # Format the results with size limiting
                content = self.output_limiter.format_content_search_results(results, query)
            else:
                content = f"Error: Unknown search_type '{search_type}'"
                logger.error(content)
                return {
                    "tool_use_id": tool_call.get("id"),
                    "content": content,
                    "is_error": True
                }
            
            logger.info(f"Successfully executed {search_type} search for '{query}'")
            return {
                "tool_use_id": tool_call.get("id"),
                "content": content
            }
        except Exception as e:
            error_msg = f"Error executing {search_type} search for '{query}': {str(e)}"
            logger.error(error_msg)
            return {
                "tool_use_id": tool_call.get("id"),
                "content": error_msg,
                "is_error": True
            }


def register_search_tool(agent, allowed_folders=None, toolignore_path=".toolignore", repo_path="."):
    """Register the search tool with the agent
    
    Args:
        agent: The AgentCLI agent instance
        allowed_folders: List of folders the tool is allowed to access (None means all folders)
        toolignore_path: Path to the .toolignore file
        repo_path: Path to the repository (default: current directory)
        
    Returns:
        The updated agent instance
    """
    
    # Create the search tool instance
    search_tool = SearchTool(
        allowed_folders=allowed_folders,
        toolignore_path=toolignore_path,
        repo_path=repo_path
    )
    
    # Define the tool function
    def file_content_search(search_type, query, **kwargs):
        """Search tool for finding files and content
        
        This tool allows searching for files by name or content within files.
        """
        # Create a tool call object in the format expected by the handler
        tool_call = {
            "input": {
                "search_type": search_type,
                "query": query,
                **kwargs
            }
        }
        
        # Handle the tool call
        result = search_tool.handle_tool_call(tool_call)
        content = result.get("content", "Error: No result content")
        
        return content
    
    # Register the tool with the agent
    agent.tool_registry.register(
        name="file_content_search",
        func=file_content_search,
        description="""
Search tool for finding files and content within files.
This tool allows you to search for files by name using fuzzy matching or search for specific content within files.

Available search types:
- fuzzy_file: Find files with names similar to the query
- content: Search for specific text within files

Path access rules:
- The current working directory and all files within it are accessible, EXCEPT those matching .toolignore patterns
- Subdirectories of the current working directory are accessible, EXCEPT those matching .toolignore patterns
- Additional allowed folders can be configured for access outside the current directory
- All paths are checked against patterns in the .toolignore file before any other access rules
- Path traversal (using '../') is not allowed

Best practices:
- Always search for a file's existence using fuzzy_file before trying to view its content
- Use specific search terms to avoid excessive results
- For content search, specify a directory to narrow the search scope when possible
- Content search automatically skips binary files and files larger than 1MB
        """.strip(),
        parameters={
            "search_type": {
                "type": "string",
                "description": "The type of search to perform (fuzzy_file or content)",
                "enum": ["fuzzy_file", "content"]
            },
            "query": {
                "type": "string",
                "description": "The search query"
            },
            "directory": {
                "type": "string",
                "description": "The directory to search in (for content search). Default is the current directory."
            },
            "case_sensitive": {
                "type": "boolean",
                "description": "Whether the search should be case sensitive (for content search). Default is false."
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results to return. Default is 10 for fuzzy_file and 50 for content."
            },
            "max_per_file": {
                "type": "integer",
                "description": "Maximum number of matches per file (for content search). Default is 10."
            }
        },
        required_params=["search_type", "query"]
    )
    
    logger.info("Registered search tool")
    
    return agent


# Example usage
if __name__ == "__main__":
    from core.agent import Agent
    
    # Create agent and register search tool
    agent = Agent()
    register_search_tool(agent)
    
    # Print available tools
    print("Available tools:")
    for tool_name in agent.tool_registry.list_tools():
        print(f"- {tool_name}") 