#!/usr/bin/env python3
"""
Run script for AgentCLI with text editor and search tools
"""

import os
import argparse
from dotenv import load_dotenv

from core.agent import Agent
from tools.text_editor_tool import register_text_editor_tool
from tools.search_tool import register_search_tool
from utils.constants import DEFAULT_MODEL, MAX_TOKENS, DEFAULT_REPO_PATH
from config.text_editor_config import ALLOWED_FOLDERS, TOOLIGNORE_PATH, BACKUP_DIR

def main():
    """Main entry point for running the agent with all tools"""
    # Load environment variables
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="AgentCLI - Run with text editor and search tools")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS, help=f"Maximum tokens for response (default: {MAX_TOKENS})")
    parser.add_argument("--no-prompt-caching", action="store_true", help="Disable prompt caching")
    parser.add_argument("--output-limit", type=int, default=1000, help="Maximum characters for tool outputs (default: 1000)")
    parser.add_argument("--repo-path", default=DEFAULT_REPO_PATH, help=f"Path to the repository (default: {DEFAULT_REPO_PATH})")
    
    args = parser.parse_args()
    
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Please set your API key in the .env file or with: export ANTHROPIC_API_KEY='your-api-key'")
        return
    
    # Create agent with CLI visibility
    agent = Agent(
        model=args.model,
        max_tokens=args.max_tokens,
        use_prompt_caching=not args.no_prompt_caching,
        cli_visibility=True,  # Enable CLI visibility for tool calls
        repo_path=args.repo_path
    )
    
    # Register all tools
    register_text_editor_tool(
        agent,
        allowed_folders=ALLOWED_FOLDERS,
        toolignore_path=TOOLIGNORE_PATH,
        backup_dir=BACKUP_DIR,
        repo_path=args.repo_path
    )
    
    # Register the search tool with the same access permissions as the text editor
    register_search_tool(
        agent,
        allowed_folders=ALLOWED_FOLDERS,
        toolignore_path=TOOLIGNORE_PATH,
        repo_path=args.repo_path
    )
    
    print("🤖 AgentCLI - Running with text editor and search tools")
    print(f"Model: {args.model}, Max tokens: {args.max_tokens}")
    print(f"Repository path: {args.repo_path}")
    print("Available tools:")
    for tool_name in agent.tool_registry.list_tools():
        print(f"- {tool_name}")
    print("Type 'exit' or 'quit' to end the session")
    print("=" * 50)
    
    # Print text editor configuration
    print("\nTool Configuration:")
    print(f"- Allowed folders: {', '.join(ALLOWED_FOLDERS) if ALLOWED_FOLDERS else 'All folders'}")
    print(f"- .toolignore file: {TOOLIGNORE_PATH}")
    print(f"- Backup directory: {BACKUP_DIR}")
    print("=" * 50)
    
    while True:
        try:
            user_input = input("\n👤 You: ")
            
            if user_input.lower() in ["exit", "quit"]:
                print("\nGoodbye! 👋")
                break
                
            print("\n🤖 Agent: ", end="", flush=True)
            
            response = agent.process_request(user_input)
            print(response)
            
            # Print token usage
            print(f"\n📊 {agent.token_tracker}")
            
        except KeyboardInterrupt:
            print("\nSession interrupted. Goodbye! 👋")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")


if __name__ == "__main__":
    main() 