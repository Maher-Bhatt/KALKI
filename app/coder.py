"""
KALKI Code Engine — generate code via Groq, save, execute.
Supports Python, PowerShell, Batch, Node.js, and Bash.
"""

import os
import re
import sys
import subprocess
from datetime import datetime
from typing import Optional, Dict, Any, Tuple, Callable, List

SCRIPTS_DIR: Optional[str] = None  # set by server.py


# Extension map
LANG_EXT: Dict[str, str] = {
    "python": "py", "py": "py",
    "powershell": "ps1", "ps": "ps1", "ps1": "ps1",
    "batch": "bat", "bat": "bat", "cmd": "bat",
    "javascript": "js", "js": "js", "node": "js",
    "html": "html",
    "bash": "sh", "sh": "sh",
}


def _safe_name(name: Optional[str]) -> str:
    """Sanitize a string to be used as a safe filename."""
    s = re.sub(r"[^A-Za-z0-9_-]+", "_", (name or "script")).strip("_")
    return s[:40] or "script"


def strip_code_fence(text: str) -> str:
    """
    Pull out the first fenced code block (e.g. ```python ... ```).
    If no code block is found, returns the original text.
    
    Args:
        text (str): The raw text potentially containing a code block.
        
    Returns:
        str: The extracted raw code.
    """
    if not text:
        return ""
    m = re.search(r"```[a-zA-Z0-9_+\-]*\s*\n(.*?)```", text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def save_script(name: str, code: str, lang: str = "python") -> str:
    """
    Save the given code to a uniquely timestamped file in the SCRIPTS_DIR.
    
    Args:
        name (str): The logical name of the script.
        code (str): The code content to write.
        lang (str): The programming language (determines extension).
        
    Returns:
        str: The absolute path to the saved script file.
    """
    ext = LANG_EXT.get(lang.lower(), "txt")
    if SCRIPTS_DIR is None:
        raise RuntimeError("SCRIPTS_DIR is not set")
    os.makedirs(SCRIPTS_DIR, exist_ok=True)
    path = os.path.join(
        SCRIPTS_DIR,
        f"{_safe_name(name)}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}",
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(code)
    return path


def run_script(path: str, lang: str = "python", timeout: int = 60) -> Dict[str, Any]:
    """
    Execute a script file locally as a subprocess.
    
    Args:
        path (str): The path to the script to execute.
        lang (str): The runtime environment to invoke.
        timeout (int): Maximum execution time in seconds.
        
    Returns:
        Dict[str, Any]: A dictionary containing stdout, stderr, and the return code, or an error string.
    """
    lang = lang.lower()
    if lang in ("python", "py"):
        cmd = [sys.executable, path]
    elif lang in ("powershell", "ps", "ps1"):
        cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", path]
    elif lang in ("batch", "bat", "cmd"):
        cmd = [path]
    elif lang in ("javascript", "js", "node"):
        cmd = ["node", path]
    else:
        return {"error": f"can't execute {lang} scripts here"}
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "stdout": (p.stdout or "")[:6000],
            "stderr": (p.stderr or "")[:2000],
            "code": p.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"timeout after {timeout}s"}
    except Exception as e:
        return {"error": str(e)}


def run_inline(code: str, lang: str = "python", name: str = "inline", timeout: int = 60) -> Dict[str, Any]:
    """
    Convenience method to save an inline code snippet to disk and execute it immediately.
    
    Args:
        code (str): The code to execute.
        lang (str): The language of the code.
        name (str): A descriptive name for the script file.
        timeout (int): Timeout in seconds.
        
    Returns:
        Dict[str, Any]: The execution results.
    """
    code = strip_code_fence(code)
    path = save_script(name, code, lang)
    out = run_script(path, lang, timeout)
    out["path"] = path
    return out


# ─── Groq-driven code generation ────────────────────────
CODE_SYSTEM_PROMPT: str = (
    "You are KALKI — Sir's personal coding engine. "
    "Write production-quality {LANG} code that does exactly what Sir asks. "
    "Output ONLY the code in a single fenced block (```{LANG} ... ```). "
    "No prose before or after. No explanations unless explicitly requested. "
    "Code must be self-contained and runnable. "
    "For Python: stdlib only unless Sir names a package. "
    "Include print statements so output is visible when run."
)


def generate_code(ask_ai_fn: Callable[[List[Dict[str, str]]], str], prompt: str, lang: str = "python") -> Tuple[str, str]:
    """
    Generate executable code using the central AI model by passing a specialized system prompt.
    
    Args:
        ask_ai_fn (Callable): The function used to call the LLM backend (e.g. from server.py).
        prompt (str): The user's code generation request.
        lang (str): The requested programming language.
        
    Returns:
        Tuple[str, str]: A tuple of (stripped_code, raw_llm_response).
    """
    sys_msg = CODE_SYSTEM_PROMPT.replace("{LANG}", lang)
    raw = ask_ai_fn([
        {"role": "system", "content": sys_msg},
        {"role": "user", "content": prompt},
    ])
    return strip_code_fence(raw), raw
