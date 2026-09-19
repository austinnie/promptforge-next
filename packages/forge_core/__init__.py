# packages/forge_core/__init__.py
"""PromptForge 核心逻辑。

零外部依赖，可在任何 Python 环境使用。
"""

from .composer import PromptComposer
from .context_manager import ContextManager
from .intent import IntentAnalyzer, IntentResult
from .loader import load_all_layers
from .preset_bridge import PresetBridge, get_default_bridge
from .prompt_builder import PromptBuilder
from .safety import SafetyChecker, check_safety, get_safe_prompt, sanitize_text

__all__ = [
    "PromptComposer",
    "ContextManager",
    "IntentAnalyzer",
    "IntentResult",
    "load_all_layers",
    "PresetBridge",
    "get_default_bridge",
    "PromptBuilder",
    "SafetyChecker",
    "check_safety",
    "get_safe_prompt",
    "sanitize_text",
]

__version__ = "0.1.0"