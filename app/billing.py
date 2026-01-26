"""Billing and usage tracking for OpenAI API calls."""

import logging
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

# Pricing per 1K tokens (as of January 2024)
OPENAI_PRICING = {
    "gpt-3.5-turbo": {
        "input": 0.0015,      # $0.0015 per 1K input tokens
        "output": 0.002       # $0.002 per 1K output tokens
    },
    "gpt-4": {
        "input": 0.03,        # $0.03 per 1K input tokens
        "output": 0.06        # $0.06 per 1K output tokens
    },
    "gpt-4-turbo": {
        "input": 0.01,        # $0.01 per 1K input tokens
        "output": 0.03        # $0.03 per 1K output tokens
    }
}

class BillingTracker:
    """Track API usage and estimated costs."""
    
    def __init__(self, log_dir: str = "logs"):
        """Initialize billing tracker."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.usage_file = self.log_dir / "api_usage.json"
        self.stats_file = self.log_dir / "usage_stats.json"
        self.ensure_files_exist()
    
    def ensure_files_exist(self):
        """Ensure log files exist."""
        if not self.usage_file.exists():
            self.usage_file.write_text(json.dumps([], indent=2))
        if not self.stats_file.exists():
            self.stats_file.write_text(json.dumps({
                "total_requests": 0,
                "total_input_tokens": 0,
                "total_output_tokens": 0,
                "total_cost": 0.0,
                "model": "gpt-3.5-turbo",
                "first_request": None,
                "last_request": None
            }, indent=2))
    
    def log_request(self, 
                    query: str,
                    input_tokens: int,
                    output_tokens: int,
                    model: str = "gpt-3.5-turbo",
                    context: Optional[str] = None,
                    response: Optional[str] = None) -> Dict[str, Any]:
        """Log an API request with usage data."""
        
        # Calculate cost
        cost = self._calculate_cost(input_tokens, output_tokens, model)
        
        # Create usage record
        record = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "query": query[:100],  # First 100 chars
            "context_length": len(context) if context else 0,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": round(cost, 6),
            "response_length": len(response) if response else 0
        }
        
        # Append to usage log
        try:
            with open(self.usage_file, 'r') as f:
                usage_data = json.load(f)
            usage_data.append(record)
            with open(self.usage_file, 'w') as f:
                json.dump(usage_data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to log usage: {e}")
        
        # Update statistics
        self._update_stats(input_tokens, output_tokens, cost, model)
        
        logger.info(f"API Call Logged - Model: {model}, Tokens: {input_tokens + output_tokens}, Cost: ${cost:.6f}")
        
        return record
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int, model: str) -> float:
        """Calculate estimated cost for API call."""
        if model not in OPENAI_PRICING:
            logger.warning(f"Unknown model {model}, using gpt-3.5-turbo pricing")
            model = "gpt-3.5-turbo"
        
        pricing = OPENAI_PRICING[model]
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        
        return input_cost + output_cost
    
    def _update_stats(self, input_tokens: int, output_tokens: int, cost: float, model: str):
        """Update cumulative statistics."""
        try:
            with open(self.stats_file, 'r') as f:
                stats = json.load(f)
            
            stats["total_requests"] += 1
            stats["total_input_tokens"] += input_tokens
            stats["total_output_tokens"] += output_tokens
            stats["total_cost"] += cost
            stats["model"] = model
            stats["last_request"] = datetime.now().isoformat()
            
            if not stats["first_request"]:
                stats["first_request"] = datetime.now().isoformat()
            
            with open(self.stats_file, 'w') as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to update statistics: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        try:
            with open(self.stats_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read statistics: {e}")
            return {}
    
    def get_recent_usage(self, limit: int = 10) -> list:
        """Get recent API usage records."""
        try:
            with open(self.usage_file, 'r') as f:
                usage_data = json.load(f)
            return usage_data[-limit:]
        except Exception as e:
            logger.error(f"Failed to read usage data: {e}")
            return []


# Global tracker instance
billing_tracker = BillingTracker()
