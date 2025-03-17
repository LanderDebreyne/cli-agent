#!/usr/bin/env python3
"""
AgentCLI - A lightweight CLI agent using Anthropic's Claude API with built-in tool calling
"""

import os
import argparse
import logging
from dotenv import load_dotenv

from core.agent import Agent
from utils.constants import DEFAULT_MODEL, MAX_TOKENS, DEFAULT_REPO_PATH

# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("agent_cli")


def main():
    """Main entry point for the CLI"""
    parser = argparse.ArgumentParser(description="AgentCLI - A lightweight CLI agent using Anthropic's Claude API")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Claude model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--max-tokens", type=int, default=MAX_TOKENS, help=f"Maximum tokens for response (default: {MAX_TOKENS})")
    parser.add_argument("--no-prompt-caching", action="store_true", help="Disable prompt caching")
    parser.add_argument("--repo-path", default=DEFAULT_REPO_PATH, help=f"Path to the repository (default: {DEFAULT_REPO_PATH})")
    
    args = parser.parse_args()
    
    # Check for API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY environment variable not set")
        print("Please set your API key with: export ANTHROPIC_API_KEY='your-api-key'")
        return
    
    # Create agent
    agent = Agent(
        model=args.model,
        max_tokens=args.max_tokens,
        use_token_efficient_tools=args.token_efficient_tools,
        use_prompt_caching=not args.no_prompt_caching,
        repo_path=args.repo_path
    )
    
    print("🤖 AgentCLI - A lightweight CLI agent using Anthropic's Claude API")
    print(f"Model: {args.model}, Max tokens: {args.max_tokens}")
    print(f"Repository path: {args.repo_path}")
    if args.no_prompt_caching:
        print("Prompt caching: Disabled")
    print("Type 'exit' or 'quit' to end the session")
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
    # Load environment variables
    load_dotenv()
    main() 