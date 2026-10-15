# /crm/shared/services/prompt_loader.py
import os
from pathlib import Path
from typing import Dict

class PromptLoader:
    ROOT = Path("/crm/shared")
    PROMPTS_DIR = ROOT / "prompts"
    _cache: Dict[str, str] = {}

    @classmethod
    def load(cls, name: str) -> str:
        """
        Load a prompt file by base name (without path), e.g. 'base_steps_prompt.txt'.
        Caches in-memory.
        """
        if name in cls._cache:
            return cls._cache[name]

        path = cls.PROMPTS_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"Prompt file not found: {path}")

        text = path.read_text(encoding="utf-8")
        cls._cache[name] = text
        return text

    @staticmethod
    def render(template: str, vars: Dict[str, str]) -> str:
        """
        Very simple placeholder replacement using <<KEY>> tokens.
        Does NOT escape values; pass safe strings.
        """
        out = template
        for k, v in (vars or {}).items():
            out = out.replace(f"<<{k}>>", v if isinstance(v, str) else str(v))
        return out
