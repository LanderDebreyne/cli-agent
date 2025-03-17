# AgentCLI
a lightweight CLI agent using Anthropic's Claude API with built-in tool calling.

🚀 WOOHOO! Agent Claude reporting for duty! 🎮 Ready to supercharge your CLI experience with some digital wizardry! Let's build something AWESOME together! ✨

## Installation

1. Clone the repository:
```bash
git clone https://github.com/LanderDebreyne/cli-agent.git
cd cli-agent
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Copy `.env.example` to `.env`
   - Add your Anthropic API key to `.env`

## Project Structure

The project has a modular structure:

```
├── agent_cli_main.py       # Main entry point for the CLI
├── run.py                  # Run the agent with custom tools
├── core/                   # Core functionality
│   ├── __init__.py
│   └── agent.py            # Main Agent class
├── models/                 # Data models
│   ├── __init__.py
│   └── token_tracker.py    # Token usage tracking
├── tools/                  # Tool-related functionality
│   ├── __init__.py
│   ├── tool_registry.py    # Tool registry
│   └── default_tools.py    # Default tools
└── utils/                  # Utility classes
    ├── __init__.py
    ├── constants.py        # Shared constants
    └── output_limiter.py   # Output limiting utility
```

## Usage

### Basic Usage

```bash
python agent_cli_main.py
```

### With Custom Tools

```bash
python run.py
```

### Command Line Options

- `--model`: Claude model to use (default: claude-3-7-sonnet-20250219)
- `--max-tokens`: Maximum tokens for response (default: 4096)
- `--no-prompt-caching`: Disable prompt caching
- `--output-limit`: Maximum characters for tool outputs (default: 1000, only for run.py)

## Creating Custom Tools

To create custom tools, follow the pattern in `tools/text_editor_tool.py`:

1. Define tool functions
2. Register them with the agent using `agent.tool_registry.register()`
3. Provide a name, function, description, parameters, and required parameters

Example:

```python
def my_custom_tool(param1: str, param2: int = 0):
    """My custom tool implementation"""
    # Tool implementation here
    return f"Result: {param1}, {param2}"

agent.tool_registry.register(
    name="my_tool",
    func=my_custom_tool,
    description="Description of what the tool does",
    parameters={
        "param1": {
            "type": "string",
            "description": "Description of param1"
        },
        "param2": {
            "type": "integer",
            "description": "Description of param2"
        }
    },
    required_params=["param1"]  # Only param1 is required
)
```

## Safety Guardrails in Text Editor Tool

The text editor tool includes several safety guardrails to prevent unauthorized access and modifications:

1. **Path Validation** - All file paths are validated to prevent directory traversal attacks and ensure they are within allowed directories.

2. **Ignore Patterns** - The tool supports a `.toolignore` file that works like `.gitignore`, letting you specify patterns for files and directories that should be protected from access or modification.

3. **Allowed Folders** - You can restrict the tool to only operate within specific directories by configuring the `allowed_folders` parameter.

4. **Backup System** - Automatic backups are created before modifying files, allowing for recovery from unintended changes.

5. **Undo Functionality** - The `undo_edit` command lets you revert the last edit made to any file.

6. **Human in the Loop Confirmation** - Write actions (create, edit, delete) include a confirmation mechanism that:
   - Shows a preview of changes with a diff for edits or the content for new files
   - Prompts the user with "Do you want to apply these changes? (yes/no)"
   - Only proceeds with the modification if the user explicitly confirms with "yes"
   - Completely cancels the operation if the user responds with "no"
   - This confirmation system ensures no file modifications occur without explicit user approval

This makes the tool both powerful and safe for use in production environments.

## Search Tool Functionality

The search tool provides two powerful search capabilities:

1. **Fuzzy File Search** - Find files by name using fuzzy matching, even if you don't know the exact filename.
   ```
   # Example usage by the agent
   file_content_search(search_type="fuzzy_file", query="search")
   ```

2. **Content Search** - Search for specific text within files across the codebase.
   ```
   # Example usage by the agent
   file_content_search(search_type="content", query="def register_tool", directory="tools")
   ```

The search tool respects the same safety guardrails as the text editor tool:
- Honors `.toolignore` patterns
- Restricted to allowed folders
- Path validation to prevent directory traversal

Additional features:
- Case-sensitive or case-insensitive searching
- Configurable maximum number of results
- Context display showing lines before and after matches
- Automatic filtering of binary and large files
- Output limiting to prevent token explosions
- Intelligent truncation with informative messages about omitted content

## Shared Modules

The project includes shared modules to avoid code duplication and ensure consistent behavior:

1. **Path Validator** - Provides shared functionality for path validation, ignore patterns, and allowed folders logic used by multiple tools.

2. **Output Limiter** - Helps control the size of tool outputs to prevent token explosions in the agent's context.

These modules make it easier to maintain the codebase and ensure that all tools follow the same security and performance best practices.

## Environment Variables

The application requires the following environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| ANTHROPIC_API_KEY | Your Anthropic API key for Claude access | Yes |

You can set these variables in two ways:
1. Create a `.env` file in the project root (copy from `.env.example`)
2. Set them as environment variables in your shell

To get an Anthropic API key, visit [Anthropic's Console](https://console.anthropic.com/).
