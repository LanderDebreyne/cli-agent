"""
Configuration for the text editor tool
"""

# List of folders the text editor tool is allowed to access
# If empty, only the current working directory and its subdirectories are allowed
# The current working directory is always allowed regardless of this setting
ALLOWED_FOLDERS = [
    "tools",
    "core",
    "models",
    "utils",
    "examples",
    "config",
    "tests",
    "docs",
    # Add more allowed folders here
]

# Path to the .toolignore file
TOOLIGNORE_PATH = ".toolignore"

# Directory to store file backups
BACKUP_DIR = ".backups" 