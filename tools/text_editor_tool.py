"""
Text Editor Tool for AgentCLI

This file implements the text editor tool for AgentCLI as described in the Anthropic documentation.
The text editor tool allows Claude to view and modify text files.
"""

import os
import logging
import shutil
import difflib
from typing import Dict, Any, Tuple, List, Optional

# Import shared modules
from utils.path_validator import PathValidator
from utils.output_limiter import OutputLimiter

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("text_editor_tool")

class TextEditorTool:
    """Implementation of the text editor tool for Claude"""
    
    def __init__(self, backup_dir: str = ".backups", allowed_folders: Optional[List[str]] = None, toolignore_path: str = ".toolignore", repo_path: str = "."):
        """Initialize the text editor tool
        
        Args:
            backup_dir: Directory to store file backups
            allowed_folders: List of folders the tool is allowed to access (None means all folders)
            toolignore_path: Path to the .toolignore file
            repo_path: Path to the repository (default: current directory)
        """
        self.repo_path = os.path.abspath(repo_path)
        self.backup_dir = os.path.join(self.repo_path, backup_dir) if not os.path.isabs(backup_dir) else backup_dir
        # Use the shared path validator
        self.path_validator = PathValidator(
            allowed_folders=allowed_folders,
            toolignore_path=toolignore_path,
            repo_path=repo_path
        )
        # Use the output limiter
        self.output_limiter = OutputLimiter()
        self._ensure_backup_dir()
        self.last_edits = {}  # Store last edits for undo functionality
        
    def _ensure_backup_dir(self):
        """Ensure the backup directory exists"""
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
            logger.info(f"Created backup directory: {self.backup_dir}")
    
    def _create_backup(self, file_path: str) -> str:
        """Create a backup of a file before modifying it
        
        Args:
            file_path: Path to the file to backup
            
        Returns:
            Path to the backup file
        """
        if not os.path.exists(file_path):
            return ""
            
        # Create a unique backup filename
        backup_filename = os.path.join(
            self.backup_dir, 
            f"{os.path.basename(file_path)}.bak"
        )
        
        # Copy the file to the backup location
        shutil.copy2(file_path, backup_filename)
        logger.info(f"Created backup of {file_path} at {backup_filename}")
        
        return backup_filename
    
    def _validate_path(self, path: str) -> Tuple[bool, str]:
        """Validate a file path to prevent directory traversal
        
        Args:
            path: The file path to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Use the shared path validator
        return self.path_validator.validate_path(path)
    
    def _handle_directory_listing(self, path: str) -> str:
        """Handle listing the contents of a directory
        
        Args:
            path: Path to the directory to list
            
        Returns:
            Formatted directory listing
        """
        try:
            # Get the list of files and directories
            items = os.listdir(path)
            
            # Sort items (directories first, then files)
            dirs = []
            files = []
            
            for item in items:
                item_path = os.path.join(path, item)
                
                # Skip ignored items
                if self.path_validator.is_path_ignored(item_path):
                    continue
                    
                if os.path.isdir(item_path):
                    dirs.append(item + '/')
                else:
                    files.append(item)
                    
            dirs.sort()
            files.sort()
            
            # Format the output
            result = f"Directory listing for: {path}\n\n"
            
            if dirs:
                result += "Directories:\n"
                for d in dirs:
                    result += f"- {d}\n"
                result += "\n"
                
            if files:
                result += "Files:\n"
                for f in files:
                    # Get file size
                    size = os.path.getsize(os.path.join(path, f))
                    size_str = self._format_size(size)
                    result += f"- {f} ({size_str})\n"
            
            if not dirs and not files:
                result += "Directory is empty or all items are ignored by .toolignore"
                
            # Limit the output size
            return self.output_limiter.truncate_text(result, 5000)
        except Exception as e:
            return f"Error listing directory: {str(e)}"
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size in a human-readable format
        
        Args:
            size_bytes: Size in bytes
            
        Returns:
            Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def handle_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a tool call from Claude
        
        Args:
            tool_call: The tool call from Claude
            
        Returns:
            The result of the tool call
        """
        input_params = tool_call.get("input", {})
        command = input_params.get("command", "")
        path = input_params.get("path", "")
        
        # Handle paths starting with a slash - treat them as relative paths from the current directory
        if path.startswith('/'):
            # Remove the leading slash to make it a relative path
            path = path[1:] if len(path) > 1 else '.'
            logger.info(f"Converting absolute path to relative path: {path}")
        
        # Validate the path
        is_valid, validated_path = self._validate_path(path)
        if not is_valid:
            return {
                "tool_use_id": tool_call.get("id"),
                "content": f"Error: Invalid file path: {validated_path}",
                "is_error": True
            }
        
        try:
            # Handle directory listing for view command
            if command == "view" and os.path.isdir(validated_path):
                result = self._handle_directory_listing(validated_path)
                logger.info(f"Successfully listed directory: {validated_path}")
                return {
                    "tool_use_id": tool_call.get("id"),
                    "content": result
                }
            
            # Handle different commands for files
            if command == "view":
                result = self._handle_view(validated_path, input_params)
            elif command == "str_replace":
                result = self._handle_str_replace(validated_path, input_params)
            elif command == "create":
                result = self._handle_create(validated_path, input_params)
            elif command == "insert":
                result = self._handle_insert(validated_path, input_params)
            elif command == "undo_edit":
                result = self._handle_undo_edit(validated_path)
            else:
                result = f"Error: Unknown command '{command}'"
                logger.error(result)
                return {
                    "tool_use_id": tool_call.get("id"),
                    "content": result,
                    "is_error": True
                }
            
            logger.info(f"Successfully executed {command} command on {path}")
            return {
                "tool_use_id": tool_call.get("id"),
                "content": result
            }
        except Exception as e:
            error_msg = f"Error executing {command} command on {path}: {str(e)}"
            logger.error(error_msg)
            return {
                "tool_use_id": tool_call.get("id"),
                "content": error_msg,
                "is_error": True
            }
    
    def _handle_view(self, path: str, params: Dict[str, Any]) -> str:
        """Handle the view command
        
        Args:
            path: Path to the file to view
            params: Additional parameters
            
        Returns:
            The file contents
        """
        if not os.path.exists(path):
            return f"Error: File '{path}' not found"
            
        view_range = params.get("view_range")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # If view_range is specified, return only those lines
            if view_range and isinstance(view_range, list) and len(view_range) == 2:
                start_line = max(1, view_range[0])
                end_line = view_range[1] if view_range[1] != -1 else len(lines)
                
                # Enforce a maximum of 250 lines to prevent excessive output
                if end_line - start_line + 1 > 250:
                    end_line = start_line + 249  # Limit to 250 lines
                
                # Adjust for 1-indexed line numbers
                start_idx = start_line - 1
                end_idx = min(end_line, len(lines))
                
                # Add line numbers to the output
                result = ""
                for i in range(start_idx, end_idx):
                    result += f"{i+1}: {lines[i]}"
                    
                # If we didn't show the whole file, add a note
                if start_line > 1 or end_line < len(lines):
                    result += f"\n(Showing lines {start_line} to {end_line} of {len(lines)} total lines)"
                    if end_line - start_line + 1 == 250:
                        result += f"\n(Maximum view limit is 250 lines at a time)"
            else:
                # Return the entire file with line numbers, but limit to 250 lines
                max_lines = min(len(lines), 250)
                result = ""
                for i in range(max_lines):
                    result += f"{i+1}: {lines[i]}"
                
                # Add a note if we truncated the file
                if len(lines) > 250:
                    result += f"\n(Showing first 250 lines of {len(lines)} total lines)"
                    result += f"\n(Maximum view limit is 250 lines at a time)"
                    
            return result
        except Exception as e:
            return f"Error reading file: {str(e)}"
    
    def _handle_str_replace(self, path: str, params: Dict[str, Any]) -> str:
        """Handle the str_replace command
        
        Args:
            path: Path to the file to modify
            params: Additional parameters
            
        Returns:
            Result message
        """
        if not os.path.exists(path):
            return f"Error: File '{path}' not found"
            
        old_str = params.get("old_str", "")
        new_str = params.get("new_str", "")
        confirm = params.get("confirm", True)
        
        if not old_str:
            return "Error: old_str parameter is required"
            
        # Create a backup
        backup_path = self._create_backup(path)
        
        try:
            # Read the file
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Check if the old string exists exactly once
            if content.count(old_str) == 0:
                return f"Error: The text to replace was not found in the file"
            elif content.count(old_str) > 1:
                return f"Error: The text to replace was found multiple times ({content.count(old_str)}). Please provide more context to make the replacement unique."
                
            # Generate the new content
            new_content = content.replace(old_str, new_str)
            
            # If confirmation is requested, show a diff and ask for confirmation
            if confirm:
                # Generate a unified diff
                old_lines = content.splitlines(True)
                new_lines = new_content.splitlines(True)
                diff = difflib.unified_diff(
                    old_lines, 
                    new_lines,
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    n=3  # Context lines
                )
                
                # Format the diff for display
                diff_text = "".join(diff)
                
                # Return the diff with a special marker to indicate confirmation is needed
                return f"CONFIRM_EDIT\n\nProposed changes:\n\n{diff_text}\n\nDo you want to apply these changes? (yes/no)"
            
            # Write the file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            # Store the edit for undo
            self.last_edits[path] = {
                "backup_path": backup_path,
                "operation": "str_replace",
                "old_content": content,
                "new_content": new_content
            }
                
            return "Successfully replaced text at exactly one location."
        except Exception as e:
            return f"Error replacing text: {str(e)}"
    
    def _handle_create(self, path: str, params: Dict[str, Any]) -> str:
        """Handle the create command
        
        Args:
            path: Path to the file to create
            params: Additional parameters
            
        Returns:
            Result message
        """
        file_text = params.get("file_text", "")
        confirm = params.get("confirm", True)
        
        # Check if file already exists
        if os.path.exists(path):
            return f"Error: File '{path}' already exists"
            
        try:
            # If confirmation is requested, show the content and ask for confirmation
            if confirm:
                # Format the content for display
                preview = file_text[:1000] + "..." if len(file_text) > 1000 else file_text
                
                # Return the preview with a special marker to indicate confirmation is needed
                return f"CONFIRM_EDIT\n\nProposed file creation '{path}':\n\n{preview}\n\nDo you want to create this file? (yes/no)"
            
            # Create parent directories if they don't exist
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
            
            # Write the file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(file_text)
                
            # Store the edit for undo
            self.last_edits[path] = {
                "backup_path": "",
                "operation": "create",
                "old_content": "",
                "new_content": file_text
            }
                
            return f"Successfully created file '{path}'."
        except Exception as e:
            return f"Error creating file: {str(e)}"
    
    def _handle_insert(self, path: str, params: Dict[str, Any]) -> str:
        """Handle the insert command
        
        Args:
            path: Path to the file to modify
            params: Additional parameters
            
        Returns:
            Result message
        """
        if not os.path.exists(path):
            return f"Error: File '{path}' not found"
            
        insert_line = params.get("insert_line", 0)
        new_str = params.get("new_str", "")
        confirm = params.get("confirm", True)
        
        # Create a backup
        backup_path = self._create_backup(path)
        
        try:
            # Read the file
            with open(path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
            # Validate insert_line
            if insert_line < 0 or insert_line > len(lines):
                return f"Error: Invalid insert_line {insert_line}. File has {len(lines)} lines."
                
            # Prepare the new content
            if insert_line == 0:
                # Insert at the beginning
                new_content = new_str + "\n" + "".join(lines)
            else:
                # Insert after the specified line
                new_content = "".join(lines[:insert_line]) + new_str + "\n" + "".join(lines[insert_line:])
            
            # If confirmation is requested, show a diff and ask for confirmation
            if confirm:
                # Generate a unified diff
                old_lines = "".join(lines).splitlines(True)
                new_lines = new_content.splitlines(True)
                diff = difflib.unified_diff(
                    old_lines, 
                    new_lines,
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                    n=3  # Context lines
                )
                
                # Format the diff for display
                diff_text = "".join(diff)
                
                # Return the diff with a special marker to indicate confirmation is needed
                return f"CONFIRM_EDIT\n\nProposed changes:\n\n{diff_text}\n\nDo you want to apply these changes? (yes/no)"
                
            # Write the file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
            # Store the edit for undo
            self.last_edits[path] = {
                "backup_path": backup_path,
                "operation": "insert",
                "old_content": "".join(lines),
                "new_content": new_content
            }
                
            return f"Successfully inserted text after line {insert_line}."
        except Exception as e:
            return f"Error inserting text: {str(e)}"
    
    def _handle_undo_edit(self, path: str) -> str:
        """Handle the undo_edit command
        
        Args:
            path: Path to the file to undo edits for
            
        Returns:
            Result message
        """
        if path not in self.last_edits:
            return f"Error: No previous edits found for '{path}'"
            
        last_edit = self.last_edits[path]
        
        try:
            if last_edit["operation"] == "create":
                # Delete the created file
                if os.path.exists(path):
                    os.remove(path)
                return f"Successfully undid file creation by deleting '{path}'."
            else:
                # Restore from backup or from stored old content
                if last_edit["backup_path"] and os.path.exists(last_edit["backup_path"]):
                    # Restore from backup file
                    shutil.copy2(last_edit["backup_path"], path)
                    return f"Successfully undid changes to '{path}' from backup."
                elif "old_content" in last_edit:
                    # Restore from stored old content
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(last_edit["old_content"])
                    return f"Successfully undid changes to '{path}' from stored content."
                else:
                    return f"Error: Could not undo changes to '{path}'. No backup or stored content available."
        except Exception as e:
            return f"Error undoing edits: {str(e)}"


def register_text_editor_tool(agent, allowed_folders=None, toolignore_path=".toolignore", backup_dir=".backups", repo_path="."):
    """Register the text editor tool with the agent
    
    Args:
        agent: The AgentCLI agent instance
        allowed_folders: List of folders the tool is allowed to access (None means all folders)
        toolignore_path: Path to the .toolignore file
        backup_dir: Directory to store file backups
        repo_path: Path to the repository (default: current directory)
        
    Returns:
        The updated agent instance
    """
    
    # Create the text editor tool instance
    text_editor = TextEditorTool(
        allowed_folders=allowed_folders,
        toolignore_path=toolignore_path,
        backup_dir=backup_dir,
        repo_path=repo_path
    )
    
    # Define the tool function
    def str_replace_editor(command, path, **kwargs):
        """Text editor tool for Claude
        
        This tool allows Claude to view and modify text files.
        """
        # Create a tool call object in the format expected by the handler
        tool_call = {
            "input": {
                "command": command,
                "path": path,
                **kwargs
            }
        }
        
        # Handle the tool call
        result = text_editor.handle_tool_call(tool_call)
        content = result.get("content", "Error: No result content")
        
        # Check if confirmation is needed
        if content.startswith("CONFIRM_EDIT"):
            # Extract the confirmation message
            confirmation_message = content.replace("CONFIRM_EDIT\n\n", "")
            
            # Display the confirmation message to the user
            print("\n" + confirmation_message)
            
            # Prompt for user confirmation
            while True:
                user_response = input("\nConfirm changes (yes/no): ").strip().lower()
                if user_response in ["yes", "y"]:
                    # User confirmed, proceed with the operation
                    # Create a new tool call without the confirm flag
                    new_kwargs = kwargs.copy()
                    new_kwargs["confirm"] = False  # Don't ask for confirmation again
                    
                    # Create a new tool call
                    new_tool_call = {
                        "input": {
                            "command": command,
                            "path": path,
                            **new_kwargs
                        }
                    }
                    
                    # Execute the tool call
                    new_result = text_editor.handle_tool_call(new_tool_call)
                    return new_result.get("content", "Error: No result content")
                elif user_response in ["no", "n"]:
                    # User rejected the changes
                    return "Changes were rejected by the user."
                else:
                    print("Please enter 'yes' or 'no'.")
        
        # Return the content
        return content
    
    # Register the tool with the agent
    agent.tool_registry.register(
        name="str_replace_editor",
        func=str_replace_editor,
        description="""
Text editor tool for viewing and modifying text files.
This tool allows you to examine and edit files directly, helping with debugging, fixing, and improving code or other text documents.

Available commands:
- view: Read the contents of a file or list the contents of a directory. Limited to 250 lines at a time.
- str_replace: Replace a specific string in a file with a new string
- create: Create a new file with specified content
- insert: Insert text at a specific location in a file
- undo_edit: Revert the last edit made to a file

Path access rules:
- The current working directory and all files within it are accessible, EXCEPT those matching .toolignore patterns
- Subdirectories of the current working directory are accessible, EXCEPT those matching .toolignore patterns
- Additional allowed folders can be configured for access outside the current directory
- All paths are checked against patterns in the .toolignore file before any other access rules
- When viewing a directory, the tool will list its contents (excluding ignored files)
- Path traversal (using '../') is not allowed
- Paths can be specified with or without a leading slash (e.g., '/README.md' or 'README.md')

Best practices:
- Always search for a file's existence using the search tool before trying to view or edit it
- Use the view command with a specific line range when working with large files
- Create backups of important files before making significant changes
- Use the undo_edit command if you need to revert changes
        """.strip(),
        parameters={
            "command": {
                "type": "string",
                "description": "The command to execute (view, str_replace, create, insert, or undo_edit)",
                "enum": ["view", "str_replace", "create", "insert", "undo_edit"]
            },
            "path": {
                "type": "string",
                "description": "The path to the file or directory to view or modify. Use '.' for the current directory. Can be specified with or without a leading slash."
            },
            "view_range": {
                "type": "array",
                "description": "An array of two integers specifying the start and end line numbers to view. Line numbers are 1-indexed, and -1 for the end line means read to the end of the file.",
                "items": {
                    "type": "integer"
                }
            },
            "old_str": {
                "type": "string",
                "description": "The text to replace (must match exactly, including whitespace and indentation)"
            },
            "new_str": {
                "type": "string",
                "description": "The new text to insert in place of the old text"
            },
            "confirm": {
                "type": "boolean",
                "description": "Whether to show a diff and ask for confirmation before applying the changes",
                "default": False
            },
            "file_text": {
                "type": "string",
                "description": "The content to write to the new file"
            },
            "insert_line": {
                "type": "integer",
                "description": "The line number after which to insert the text (0 for beginning of file)"
            }
        },
        required_params=["command", "path"]
    )
    
    # Create the schema-less tool spec
    schema_less_tool_spec = {
        "type": "text_editor_20250124",
        "name": "str_replace_editor"
    }
    
    # Add the schema-less tool spec to the agent's tool specs
    agent.schema_less_tools = agent.schema_less_tools or []
    agent.schema_less_tools.append(schema_less_tool_spec)
    
    logger.info("Registered text editor tool")
    
    return agent


# Example usage
if __name__ == "__main__":
    from core.agent import Agent
    
    # Create agent and register text editor tool
    agent = Agent()
    register_text_editor_tool(agent)
    
    # Print available tools
    print("Available tools:")
    for tool_name in agent.tool_registry.list_tools():
        print(f"- {tool_name}") 