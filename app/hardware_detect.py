"""Detect real local hardware once, so the HUD and the LLM prompt both
show what's actually on this machine instead of a config default."""
import platform
import psutil


def detect_hardware():
    ram_gb = round(psutil.virtual_memory().total / (1024 ** 3))
    cpu_name = platform.processor() or "Unknown CPU"

    gpu_name = "Integrated Graphics"
    try:
        if platform.system() == "Windows":
            import wmi  # add `wmi` to requirements.txt - Windows-only package
            w = wmi.WMI()
            controllers = [c.Name for c in w.Win32_VideoController() if c.Name]
            discrete = [n for n in controllers if any(
                k in n for k in ("NVIDIA", "GeForce", "RTX", "GTX", "Radeon", "AMD")
            )]
            gpu_name = discrete[0] if discrete else (controllers[0] if controllers else gpu_name)
    except Exception:
        pass  # keep the safe fallback rather than crash setup over a GPU name

    return {"gpu": gpu_name, "cpu": cpu_name, "ram_gb": ram_gb, "display": "unknown"}
