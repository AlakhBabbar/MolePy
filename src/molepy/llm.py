import os
import re
from typing import List, Dict, Any, Optional
from openai import OpenAI

def get_client() -> OpenAI:
    """Instantiates OpenAI SDK client configured for DashScope, SiliconFlow, DeepSeek, or custom API endpoint."""
    api_key = (
        os.environ.get("DASHSCOPE_API_KEY")
        # os.environ.get("SILICONFLOW_API_KEY") or 
        # os.environ.get("DEEPSEEK_API_KEY") or 
        # os.environ.get("OPENAI_API_KEY") or 
        # os.environ.get("GROQ_API_KEY")
    )
    # print(api_key)
    if not api_key:
        raise ValueError(
            "API key missing! Please set DASHSCOPE_API_KEY, SILICONFLOW_API_KEY, DEEPSEEK_API_KEY, or OPENAI_API_KEY."
        )

    # Default to DashScope international compatible mode endpoint if none is provided
    base_url = os.environ.get("LLM_BASE_URL", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
    return OpenAI(api_key=api_key, base_url=base_url)

def clean_reasoning_tags(text: str) -> str:
    """Strips <think>...</think> blocks emitted by reasoning models like DeepSeek R1 or Qwen Max."""
    if not text:
        return ""
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned.strip()

def call_llm(
    messages: List[Dict[str, Any]],
    tools: Optional[List[Dict[str, Any]]] = None,
    model: Optional[str] = None
) -> Any:
    """Sends conversation history and tools to the provider."""
    client = get_client()
    
    # Default to Qwen 3.7 Plus
    selected_model = model or os.environ.get("LLM_MODEL", "qwen3.7-plus")
    
    kwargs: Dict[str, Any] = {
        "model": selected_model,
        "messages": messages,
        "temperature": 0.3,
    }

    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = "auto"
        
        # 🛑 The Parallel Tool Calls Fix 🛑
        # Some OpenAI-compatible APIs (like DashScope) reject the explicit 'parallel_tool_calls' 
        # parameter in their strict validation. We only apply it for known standard providers.
        base_url_lower = client.base_url.host.lower()
        if "dashscope" not in base_url_lower and "aliyuncs" not in base_url_lower:
            kwargs["parallel_tool_calls"] = False 

    try:
        response = client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        # Sanitize content if the model leaves <think> tags in output text
        if getattr(message, "content", None):
            message.content = clean_reasoning_tags(message.content)

        return message
        
    except Exception as e:
        # If the API still complains about the parameter, log it for debugging
        if "parallel_tool_calls" in str(e):
            print(f"\n⚠️ [molepy] Warning: API rejected 'parallel_tool_calls'. Attempting fallback...")
            kwargs.pop("parallel_tool_calls", None)
            response = client.chat.completions.create(**kwargs)
            message = response.choices[0].message
            if getattr(message, "content", None):
                message.content = clean_reasoning_tags(message.content)
            return message
        raise e