"""
Constants - Shared constants for the agent
"""

# Model constants
DEFAULT_MODEL = "claude-3-7-sonnet-20250219"
MAX_TOKENS = 4096

# Repository configuration
DEFAULT_REPO_PATH = "."  # Default to current directory

# System prompt
SYSTEM_PROMPT = """You are a helpful AI assistant with access to tools.

In this environment you have access to a set of tools you can use to answer the user's question.
You should use these tools when they would be helpful for addressing the user's request.
Always wait for tool results before continuing. Do not make up or simulate tool results.

When you need to use a tool, carefully follow the tool's description and provide all required parameters.
If a tool returns an error, try to fix the error and call the tool again with corrected parameters.
"""

# Function to get a customized system prompt with the specified repository path
def get_system_prompt(repo_path=DEFAULT_REPO_PATH):
    """Get a customized system prompt with the specified repository path
    
    Args:
        repo_path: Path to the repository (default: DEFAULT_REPO_PATH)
        
    Returns:
        Customized system prompt
    """
    # Create a customized system prompt with the repository path
    custom_prompt = SYSTEM_PROMPT + f"""
You are working with a repository located at: {repo_path}

When using tools that require file paths:
1. Use this repository path as the base directory for all operations
2. All file paths should be relative to this repository path
3. Do NOT assume files are in a "/repo" directory - use the repository path provided above
4. When searching for files, start your search in this repository path
5. When creating or editing files, make sure they are created within this repository path

This ensures that all file operations are performed in the correct location.
"""
    return custom_prompt 