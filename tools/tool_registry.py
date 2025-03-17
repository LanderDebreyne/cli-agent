"""
ToolRegistry - Registry for tools that can be called by the agent
"""

import logging
from typing import Dict, List, Any, Callable, Optional

# Configure logging
logger = logging.getLogger("agent_cli.tool_registry")


class ToolRegistry:
    """Registry for tools that can be called by the agent"""
    
    def __init__(self):
        self.tools = {}
        
    def register(self, name: str, func: Callable, description: str, parameters: Dict[str, Any] = None, required_params: List[str] = None):
        """Register a tool with the registry
        
        Args:
            name: The name of the tool
            func: The function to call when the tool is invoked
            description: A description of what the tool does
            parameters: A dictionary of parameters the tool accepts
            required_params: A list of required parameter names
        """
        if parameters is None:
            parameters = {}
            
        if required_params is None:
            required_params = []
            
        # Create JSON schema for parameters
        properties = {}
        for param_name, param_info in parameters.items():
            properties[param_name] = param_info
            
        # Create tool spec
        tool_spec = {
            "name": name,
            "description": description,
            "input_schema": {
                "type": "object",
                "properties": properties,
                "required": required_params
            }
        }
        
        # Store tool function and spec
        self.tools[name] = {
            "func": func,
            "spec": tool_spec
        }
        
        logger.info(f"Registered tool: {name}")
        
    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool function by name"""
        if name in self.tools:
            return self.tools[name]["func"]
        return None
        
    def list_tools(self) -> List[str]:
        """List all registered tool names"""
        return list(self.tools.keys())
        
    def get_tool_specs(self) -> List[Dict[str, Any]]:
        """Get tool specifications for the API call"""
        tool_specs = [tool["spec"] for tool in self.tools.values()]
        
        # Add cache_control to the last tool if there are any tools
        if tool_specs:
            tool_specs[-1]["cache_control"] = {"type": "ephemeral"}
            
        return tool_specs 