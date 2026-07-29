import os
from pathlib import Path

# Resolve the path to the markdown file relative to this script
PROMPT_FILE = Path(__file__).parent / "prompts" / "system_prompt.md"

def load_system_prompt() -> str:
    """Loads the system prompt from the markdown file."""
    if not PROMPT_FILE.exists():
        # Fallback if the file isn't created yet
        return "You are a helpful AI assistant."
    return PROMPT_FILE.read_text(encoding="utf-8")

SYSTEM_PROMPT = load_system_prompt()