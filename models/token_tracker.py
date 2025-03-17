"""
TokenTracker - Track token usage and context window size
"""

from typing import Dict


class TokenTracker:
    """Track token usage and context window size"""
    
    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0
        self.context_size = 0
        self.cache_creation_input_tokens = 0
        self.cache_read_input_tokens = 0
    
    def update(self, prompt_tokens: int, completion_tokens: int, cache_creation_input_tokens: int = 0, cache_read_input_tokens: int = 0):
        """Update token counts"""
        self.prompt_tokens += prompt_tokens
        self.completion_tokens += completion_tokens
        self.total_tokens += prompt_tokens + completion_tokens
        self.cache_creation_input_tokens += cache_creation_input_tokens
        self.cache_read_input_tokens += cache_read_input_tokens
        
    def get_stats(self) -> Dict[str, int]:
        """Get current token statistics"""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "cache_creation_input_tokens": self.cache_creation_input_tokens,
            "cache_read_input_tokens": self.cache_read_input_tokens
        }
    
    def __str__(self) -> str:
        """String representation of token usage"""
        stats = self.get_stats()
        return (
            f"Tokens: {stats['total_tokens']} total "
            f"({stats['prompt_tokens']} prompt, {stats['completion_tokens']} completion)\n"
            f"Cache: {stats['cache_creation_input_tokens']} created, {stats['cache_read_input_tokens']} read"
        ) 