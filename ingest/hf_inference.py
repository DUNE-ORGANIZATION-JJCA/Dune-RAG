"""
HuggingFace Inference Client
Uses HF Inference API for LLM generation
"""

import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class GenerationConfig:
    """Configuration for text generation"""
    model: str = "Qwen/Qwen2.5-7B-Instruct"
    max_tokens: int = 800
    temperature: float = 0.2
    top_p: float = 0.9
    repetition_penalty: float = 1.1


class HFInferenceClient:
    """
    Client for HuggingFace Inference API.
    Supports both paid API and free tier.
    """
    
    def __init__(
        self,
        api_token: str = None,
        model: str = None,
        config: GenerationConfig = None
    ):
        self.api_token = api_token or os.getenv("HF_TOKEN") or os.getenv("HF_API_KEY")
        self.api_url = os.getenv("HF_API_URL", "https://api-inference.huggingface.co/models/")
        # Override model from env
        model = model or os.getenv("HF_MODEL") or "Qwen/Qwen2.5-7B-Instruct"
        self.config = config or GenerationConfig(model=model)
        self._initialized = False
    
    def initialize(self):
        """Validate connection"""
        if not self.api_token:
            raise ValueError("HF_TOKEN not set. Get from https://huggingface.co/settings/tokens")
        
        self._initialized = True
        logger.info(f"HF Inference initialized with model: {self.config.model}")
    
    def generate(
        self,
        prompt: str,
        system_prompt: str = None,
        max_tokens: int = None,
        temperature: float = None,
        **kwargs
    ) -> str:
        """
        Generate text from prompt.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            max_tokens: Override max tokens
            temperature: Override temperature
            
        Returns:
            Generated text
        """
        if not self._initialized:
            self.initialize()
        
        # Build messages for chat-based models
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        # API call
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "inputs": messages,
            "parameters": {
                "max_new_tokens": max_tokens or self.config.max_tokens,
                "temperature": temperature or self.config.temperature,
                "top_p": self.config.top_p,
                "repetition_penalty": self.config.repetition_penalty,
                "return_full_text": False
            },
            "options": {
                "use_cache": True,
                "wait_for_model": True
            }
        }
        
        model_url = f"{self.api_url}{self.config.model}"
        
        try:
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    model_url,
                    headers=headers,
                    json=payload
                )
                response.raise_for_status()
                
                result = response.json()
                
                # Handle different response formats
                if isinstance(result, list) and len(result) > 0:
                    generated_text = result[0].get("generated_text", "")
                    # Extract assistant response
                    for msg in generated_text:
                        if msg.get("role") == "assistant":
                            return msg.get("content", "")
                    return generated_text[-1].get("content", "") if generated_text else ""
                elif isinstance(result, dict):
                    return result.get("generated_text", "")
                else:
                    return str(result)
                    
        except httpx.HTTPError as e:
            logger.error(f"HF API error: {e}")
            raise
    
    def generate_sync(
        self,
        prompt: str,
        **kwargs
    ) -> str:
        """
        Synchronous generation (alias for compatibility).
        """
        return self.generate(prompt, **kwargs)
    
    def close(self):
        """Close client"""
        pass  # No connection to close