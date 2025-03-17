"""
Agent - Main agent class that processes requests and calls tools
"""

import os
import logging
from typing import Dict, Any
from anthropic import Anthropic

from models.token_tracker import TokenTracker
from tools.tool_registry import ToolRegistry
from utils.output_limiter import OutputLimiter
from utils.constants import DEFAULT_MODEL, MAX_TOKENS, DEFAULT_REPO_PATH, SYSTEM_PROMPT, get_system_prompt

# Configure logging
logger = logging.getLogger("agent_cli.agent")


class Agent:
    """Main agent class that processes requests and calls tools using Anthropic's built-in tool calling"""
    
    def __init__(self, model: str = DEFAULT_MODEL, max_tokens: int = MAX_TOKENS, 
                 use_token_efficient_tools: bool = False, use_prompt_caching: bool = True,
                 cli_visibility: bool = False, repo_path: str = DEFAULT_REPO_PATH):
        self.model = model
        self.max_tokens = max_tokens
        self.use_token_efficient_tools = use_token_efficient_tools
        self.use_prompt_caching = use_prompt_caching
        self.cli_visibility = cli_visibility
        self.repo_path = repo_path
        self.tool_registry = ToolRegistry()
        self.token_tracker = TokenTracker()
        self.output_limiter = OutputLimiter()
        self.conversation_history = []
        self.schema_less_tools = []  # For schema-less tools like text_editor
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        
        # Configure system prompt once during initialization
        system_prompt = get_system_prompt(repo_path)
        if self.use_prompt_caching:
            self.system_config = [
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"}
                }
            ]
        else:
            self.system_config = system_prompt
            
    
    def _execute_tool_call(self, tool_call: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single tool call and return the result"""
        tool_name = tool_call["name"]
        tool_input = tool_call.get("input", {})
        
        logger.info(f"Executing tool: {tool_name} with input: {tool_input}")
        
        # Show tool call in CLI if visibility is enabled
        if self.cli_visibility:
            print(f"\n🔧 Tool Call: {tool_name}")
            if tool_input:
                # Format the input for better readability
                if isinstance(tool_input, dict):
                    for key, value in tool_input.items():
                        print(f"  - {key}: {value}")
                else:
                    print(f"  - Input: {tool_input}")
        
        tool_func = self.tool_registry.get_tool(tool_name)
        if not tool_func:
            error_msg = f"Error: Tool '{tool_name}' not found"
            if self.cli_visibility:
                print(f"❌ {error_msg}")
            return {
                "tool_use_id": tool_call.get("id"),
                "content": error_msg,
                "is_error": True
            }
        
        try:
            if isinstance(tool_input, dict):
                result = tool_func(**tool_input)
            else:
                result = tool_func(tool_input)
                
            # Limit output size
            limited_result = self.output_limiter.truncate_text(str(result))
            
            logger.info(f"Tool result: {limited_result[:100]}...")
            
            # Show tool result in CLI if visibility is enabled
            if self.cli_visibility:
                # Truncate very long results for display
                display_result = limited_result
                if len(display_result) > 500:
                    display_result = display_result[:500] + "... [truncated]"
                print(f"✅ Result: {display_result}")
            
            return {
                "tool_use_id": tool_call.get("id"),
                "content": limited_result
            }
        except Exception as e:
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            logger.error(error_msg)
            
            # Show error in CLI if visibility is enabled
            if self.cli_visibility:
                print(f"❌ {error_msg}")
                
            return {
                "tool_use_id": tool_call.get("id"),
                "content": error_msg,
                "is_error": True
            }
    
    def process_request(self, user_input: str) -> str:
        """Process a user request, execute any tool calls, and return the response
        
        This method handles both single and multiple tool calls according to the Anthropic API documentation.
        While Claude typically uses tools sequentially (one at a time), it may occasionally use multiple
        tools in a single response. This implementation handles both cases.
        
        Args:
            user_input: The user's input message
            
        Returns:
            The assistant's response after processing any tool calls
        """
        # Add user message to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})
        
        # Process tool calls in a loop until we get a final response
        while True:
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "messages": self.conversation_history,
                "system": self.system_config  # Use the pre-configured system prompt
            }
            
            # Add tools to API params
            if self.schema_less_tools and (self.model == "claude-3-5-sonnet-20240229" or self.model == "claude-3-7-sonnet-20250219"):
                # Use schema-less tools if available and model supports them
                api_params["tools"] = self.schema_less_tools
                logger.info(f"Using schema-less tools: {[tool['name'] for tool in self.schema_less_tools]}")
            else:
                # Use regular tools with JSON schema
                api_params["tools"] = self.tool_registry.get_tool_specs()
            
            # Get response from Claude with tool_use capability
            response = self.client.messages.create(**api_params)
            
            # Update token tracker with cache information
            cache_creation = getattr(response.usage, "cache_creation_input_tokens", 0)
            cache_read = getattr(response.usage, "cache_read_input_tokens", 0)
            
            self.token_tracker.update(
                response.usage.input_tokens,
                response.usage.output_tokens,
                cache_creation,
                cache_read
            )
            
            # Log cache usage if applicable
            if self.use_prompt_caching and (cache_creation > 0 or cache_read > 0):
                if cache_creation > 0:
                    logger.info(f"Created cache with {cache_creation} tokens")
                if cache_read > 0:
                    logger.info(f"Read {cache_read} tokens from cache")
            
            # Check if the response requires tool use
            if response.stop_reason == "tool_use":
                logger.info("Tool use requested by Claude")
                
                # Extract tool calls from the response
                tool_calls = []
                for block in response.content:
                    if block.type == "tool_use":
                        tool_calls.append({
                            "name": block.name,
                            "id": block.id,
                            "input": block.input
                        })
                
                # Log if multiple tool calls are detected
                if len(tool_calls) > 1:
                    logger.info(f"Multiple tool calls detected in a single response: {len(tool_calls)}")
                    for i, tc in enumerate(tool_calls):
                        logger.info(f"Tool call {i+1}: {tc['name']}")
                
                # Extract any text content
                content_block = next((block for block in response.content if block.type == "text"), None)
                assistant_response = content_block.text if content_block else ""
                
                # Add assistant response to conversation history
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": response.content  # Use the original content blocks
                })
                
                # Execute tool calls and add results to conversation
                if tool_calls:
                    # Show thinking in CLI if visibility is enabled
                    if self.cli_visibility and assistant_response:
                        print(f"{assistant_response}")
                    
                    tool_results = []
                    for tool_call in tool_calls:
                        tool_result = self._execute_tool_call(tool_call)
                        tool_results.append(tool_result)
                    
                    # Add tool results to conversation
                    tool_result_blocks = []
                    for tr in tool_results:
                        result_block = {
                            "type": "tool_result",
                            "tool_use_id": tr["tool_use_id"],
                            "content": tr["content"]
                        }
                        
                        # Add is_error field if present
                        if "is_error" in tr and tr["is_error"]:
                            result_block["is_error"] = True
                            
                        tool_result_blocks.append(result_block)
                    
                    # Add tool results as user message
                    self.conversation_history.append({
                        "role": "user",
                        "content": tool_result_blocks
                    })
                    
                    # Continue the loop to get the next response
                    # (which might be another tool call or the final response)
                    continue
            else:
                # Regular response without tool use - this is our final response
                logger.info(f"Final response received with stop_reason: {response.stop_reason}")
                
                # Extract text content
                content_block = next((block for block in response.content if block.type == "text"), None)
                assistant_response = content_block.text if content_block else ""
                
                # Add assistant response to conversation history
                self.conversation_history.append({
                    "role": "assistant", 
                    "content": response.content
                })
                
                # Return the final response
                return assistant_response 