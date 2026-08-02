import os
import json
import time
import socket
import urllib.request
from typing import Dict, Any, List, Optional

import config

# Default routing roles
ROLE_MODELS = {
    "chat": "llama-3.3-70b-versatile",
    "vision": "meta-llama/llama-4-scout-17b-16e-instruct",
    "coding": "llama-3.3-70b-versatile",
    "voice": "llama-3.1-8b-instant"
}

# Cost estimate sheet per 1k tokens (input, output) in USD
MODEL_PRICING = {
    "llama-3.3-70b-versatile": (0.00059, 0.00079),
    "llama-3.1-8b-instant": (0.00005, 0.00008),
    "gpt-4o-mini": (0.00015, 0.0006),
    "gpt-4o": (0.0025, 0.010),
    "gemini-2.5-flash": (0.000075, 0.0003),
    "gemini-2.5-pro": (0.00125, 0.005),
    "ollama": (0.0, 0.0),
    "lm_studio": (0.0, 0.0)
}

# Track token usage, cost, and latency locally
USAGE_LOG_PATH = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI", "ai_usage.json")
_metrics_lock = socket.getaddrinfo # just generic token lock, we can use threading.Lock()
import threading
_metrics_lock = threading.Lock()


def get_role_model(role: str) -> str:
    """Retrieve the model routed for a specific role (chat, vision, coding, voice)."""
    return ROLE_MODELS.get(role, "llama-3.3-70b-versatile")


def set_role_model(role: str, model_name: str) -> None:
    """Assign a model to a specific role."""
    if role in ROLE_MODELS:
        ROLE_MODELS[role] = model_name


def check_internet() -> bool:
    """Ping a public DNS resolver to verify internet connectivity."""
    try:
        # Check connection to google DNS
        socket.create_connection(("8.8.8.8", 53), timeout=2)
        return True
    except OSError:
        return False


def check_service_health(url: str) -> bool:
    """Checks if a local model endpoint is active."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=1.5) as r:
            return r.status == 200 or r.status == 204
    except Exception:
        return False


def get_local_providers_status() -> Dict[str, bool]:
    """Retrieve status (online/offline) of local LLM providers."""
    return {
        "Ollama": check_service_health(f"{getattr(config, 'OLLAMA_URL', 'http://localhost:11434')}/api/tags"),
        "LM Studio": check_service_health("http://localhost:1234/v1/models"),
        "llama.cpp": check_service_health("http://localhost:8080/v1/models")
    }


def route_request(requested_model: str) -> tuple[str, bool]:
    """
    Checks connection health and routes requested model.
    Returns (resolved_model_name, is_offline_fallback)
    """
    is_offline = not check_internet()
    if is_offline:
        # Check if local Ollama or LM Studio is running, otherwise fall back to Ollama default
        providers = get_local_providers_status()
        if providers.get("LM Studio"):
            return "lm_studio", True
        return "ollama", True
    
    return requested_model, False


def track_usage(model_name: str, prompt_tokens: int, completion_tokens: int, latency_ms: float) -> None:
    """Update local token metrics and cost log."""
    prices = MODEL_PRICING.get(model_name, (0.0, 0.0))
    cost = ((prompt_tokens / 1000.0) * prices[0]) + ((completion_tokens / 1000.0) * prices[1])

    with _metrics_lock:
        data = {}
        if os.path.exists(USAGE_LOG_PATH):
            try:
                with open(USAGE_LOG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        
        # Increment total metrics
        data["total_prompt_tokens"] = data.get("total_prompt_tokens", 0) + prompt_tokens
        data["total_completion_tokens"] = data.get("total_completion_tokens", 0) + completion_tokens
        data["total_cost_usd"] = data.get("total_cost_usd", 0.0) + cost
        
        # Add latency tracking
        count = data.get("total_calls", 0) + 1
        data["total_calls"] = count
        data["avg_latency_ms"] = ((data.get("avg_latency_ms", 0.0) * (count - 1)) + latency_ms) / count
        
        # Daily logs
        today = time.strftime("%Y-%m-%d")
        daily = data.setdefault("daily", {})
        day_data = daily.setdefault(today, {"cost": 0.0, "tokens": 0, "calls": 0, "avg_latency": 0.0})
        day_data["cost"] += cost
        day_data["tokens"] += (prompt_tokens + completion_tokens)
        day_data["calls"] += 1
        day_data["avg_latency"] = ((day_data["avg_latency"] * (day_data["calls"] - 1)) + latency_ms) / day_data["calls"]
        
        try:
            os.makedirs(os.path.dirname(USAGE_LOG_PATH), exist_ok=True)
            with open(USAGE_LOG_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass


def get_usage_metrics() -> Dict[str, Any]:
    """Retrieve full AI usage logs."""
    if not os.path.exists(USAGE_LOG_PATH):
        return {
            "total_prompt_tokens": 0,
            "total_completion_tokens": 0,
            "total_cost_usd": 0.0,
            "total_calls": 0,
            "avg_latency_ms": 0.0,
            "daily": {}
        }
    try:
        with open(USAGE_LOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
