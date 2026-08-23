import os
import re
import sys
import json
import shutil
import webbrowser
import subprocess
try:
    import customtkinter as ctk
    from tkinter import messagebox
    _GUI_AVAILABLE = True
except (ImportError, ModuleNotFoundError):
    _GUI_AVAILABLE = False
    messagebox = None
    class _HeadlessThemeManager:
        theme = {name: {} for name in ("CTk", "CTkToplevel", "CTkFrame", "CTkButton", "CTkLabel", "CTkEntry", "CTkCheckBox", "CTkOptionMenu", "CTkSegmentedButton", "CTkProgressBar", "CTkScrollableFrame")}
    class _HeadlessCTK:
        ThemeManager = _HeadlessThemeManager
        CTk = object
        @staticmethod
        def set_appearance_mode(_mode):
            pass
        @staticmethod
        def set_default_color_theme(_theme):
            pass
    ctk = _HeadlessCTK()
from runtime_paths import prepare_runtime

_runtime = prepare_runtime()
BASE_DIR = _runtime.app_root
ENTRY_DIR = _runtime.entry_dir
USER_DATA_DIR = _runtime.user_data_dir
os.makedirs(USER_DATA_DIR, exist_ok=True)
_USER_CONFIG_PATH = os.path.join(USER_DATA_DIR, "user_config.json")

# Credentials belong in the encrypted OS-backed vault, never in config.py or
# user_config.json.  Keeping this list aligned with server.py also makes the
# first-run wizard safe on read-only (Store) installs.
SECRET_SETTING_KEYS = {
    "GROQ_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
    "ELEVENLABS_API_KEY", "EMAIL_APP_PASSWORD", "GITHUB_TOKEN",
    "SHODAN_API_KEY", "SPOTIFY_CLIENT_SECRET", "CLOUD_SYNC_PASSPHRASE",
    "TELEGRAM_BOT_TOKEN",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Override the built-in "blue" theme's colors in place — this keeps every
# other already-correct property (corner radius, border widths, disabled
# states, etc.) from CTk's own theme and only swaps the colors, so nothing
# is left half-defined. Matches the platinum/graphite palette in index.html
# instead of CustomTkinter's default blue.
_T = ctk.ThemeManager.theme
_ACCENT_HOVER = "#7b838c"
_ACCENT_DIM = "#5c6068"
_BG = "#0c0c0d"
_BG_ELEV = "#17171a"
_BG_PANEL = "#1d1d21"
_TEXT = "#eaeaee"

_T["CTk"]["fg_color"] = ["#e8e8ea", _BG]
_T["CTkToplevel"]["fg_color"] = ["#e8e8ea", _BG]
_T["CTkFrame"]["fg_color"] = ["#dcdcdf", _BG_ELEV]
_T["CTkFrame"]["top_fg_color"] = ["#d0d0d3", _BG_PANEL]
_T["CTkFrame"]["border_color"] = ["#b0b0b5", "#2a2a2e"]
_T["CTkButton"]["fg_color"] = ["#c4c9d1", _ACCENT_DIM]
_T["CTkButton"]["hover_color"] = ["#aab0b8", _ACCENT_HOVER]
_T["CTkButton"]["text_color"] = ["#111113", _TEXT]
_T["CTkLabel"]["text_color"] = ["#111113", _TEXT]
_T["CTkEntry"]["fg_color"] = ["#f2f2f3", _BG_PANEL]
_T["CTkEntry"]["border_color"] = ["#b0b0b5", "#3a3a3f"]
_T["CTkEntry"]["text_color"] = ["#111113", _TEXT]
_T["CTkCheckBox"]["fg_color"] = ["#c4c9d1", _ACCENT_DIM]
_T["CTkCheckBox"]["hover_color"] = ["#aab0b8", _ACCENT_HOVER]
_T["CTkCheckBox"]["border_color"] = ["#8a8a90", "#5c6068"]
_T["CTkCheckBox"]["checkmark_color"] = ["#111113", _TEXT]
_T["CTkOptionMenu"]["fg_color"] = ["#c4c9d1", _ACCENT_DIM]
_T["CTkOptionMenu"]["button_color"] = ["#aab0b8", _ACCENT_HOVER]
_T["CTkOptionMenu"]["button_hover_color"] = ["#95999f", "#4a4d52"]
_T["CTkOptionMenu"]["text_color"] = ["#111113", _TEXT]
_T["CTkSegmentedButton"]["selected_color"] = ["#aab0b8", _ACCENT_DIM]
_T["CTkSegmentedButton"]["selected_hover_color"] = ["#95999f", _ACCENT_HOVER]
_T["CTkSegmentedButton"]["fg_color"] = ["#c4c4c8", "#2a2a2e"]
_T["CTkSegmentedButton"]["unselected_color"] = ["#c4c4c8", "#2a2a2e"]
_T["CTkSegmentedButton"]["text_color"] = ["#111113", _TEXT]
_T["CTkProgressBar"]["progress_color"] = ["#8a8a90", "#9aa3ad"]
_T["CTkScrollableFrame"]["label_fg_color"] = ["#d0d0d3", _BG_PANEL]


def _apply_to_config_py(updates: dict) -> None:
    """
    Write the wizard's collected values into config.py itself.

    Previously this wizard only wrote to user_config.json, which nothing else
    in the app ever reads — so finishing setup looked successful but silently
    left config.py (what server.py/main_app.py actually import) untouched.
    This patches config.py in place, line by line, so completing the wizard
    actually configures the running app.

    Blank string fields are skipped rather than written as "" so we don't
    clobber values like GROQ_API_KEY's os.environ.get(...) fallback with an
    empty literal when the user leaves that field blank on purpose.
    """
    cfg_path = os.path.join(BASE_DIR, "config.py")
    example_path = os.path.join(BASE_DIR, "config.example.py")
    user_cfg_path = os.path.join(USER_DATA_DIR, "config.py")

    # Try creating config.py in the install directory first
    if not os.path.exists(cfg_path):
        try:
            if os.path.exists(example_path):
                shutil.copy(example_path, cfg_path)
        except (PermissionError, OSError):
            if not os.path.exists(user_cfg_path) and os.path.exists(example_path):
                shutil.copy(example_path, user_cfg_path)

    # If BASE_DIR is read-only or cfg_path doesn't exist, patch USER_DATA_DIR/config.py instead
    if not os.path.exists(cfg_path) or not os.access(cfg_path, os.W_OK):
        if os.path.exists(user_cfg_path):
            cfg_path = user_cfg_path
        else:
            if os.path.exists(example_path):
                shutil.copy(example_path, user_cfg_path)
                cfg_path = user_cfg_path
            else:
                return

    with open(cfg_path, "r", encoding="utf-8") as f:
        text = f.read()

    appended = []
    for key, value in updates.items():
        if key in SECRET_SETTING_KEYS:
            continue
        if isinstance(value, str) and value == "":
            continue
        literal = repr(value)
        pattern = re.compile(rf"^{re.escape(key)}\s*=.*$", re.MULTILINE)
        if pattern.search(text):
            text = pattern.sub(f"{key} = {literal}", text, count=1)
        else:
            appended.append(f"{key} = {literal}")

    if appended:
        text = text.rstrip("\n") + "\n\n# --- Added by KALKI Setup Wizard ---\n" + "\n".join(appended) + "\n"

    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(text)


def run_headless_setup() -> int:
    """Create a safe quick configuration when no graphical display exists."""
    values = {
        "OWNER_NAME": os.environ.get("KALKI_OWNER_NAME", "User"),
        "OWNER_TITLE": os.environ.get("KALKI_OWNER_TITLE", "Sir"),
        "OWNER_CITY": os.environ.get("KALKI_OWNER_CITY", ""),
        "OWNER_STATE": os.environ.get("KALKI_OWNER_STATE", ""),
        "OWNER_COUNTRY": os.environ.get("KALKI_OWNER_COUNTRY", ""),
        "PERSONALITY_SPICE": "professional",
        "TTS_PROVIDER": "edge",
        "TTS_VOICE": "en-GB-RyanNeural",
        "TTS_RATE": "+0%",
        "TTS_PITCH": "+0Hz",
        "TTS_VOLUME": "+0%",
        # A headless install must never pretend a microphone is available.
        "LISTEN_MODE": os.environ.get("KALKI_LISTEN_MODE", "push").lower(),
        "VISION_RECALL_ENABLED": True,
        "VISION_RETENTION_DAYS": 30,
    }
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    persisted = dict(values)
    try:
        with open(_USER_CONFIG_PATH, "w", encoding="utf-8") as handle:
            json.dump(persisted, handle, indent=4)
        _apply_to_config_py(persisted)
    except (OSError, PermissionError) as exc:
        print(f"KALKI setup could not persist settings: {exc}", file=sys.stderr)
        return 1
    marker_path = os.path.join(USER_DATA_DIR, "setup_complete.marker")
    try:
        with open(marker_path, "w", encoding="utf-8") as handle:
            handle.write("Setup complete (headless)")
    except OSError as exc:
        print(f"KALKI setup could not create the completion marker: {exc}", file=sys.stderr)
        return 1
    print(f"KALKI headless setup complete. Settings: {_USER_CONFIG_PATH}")
    print("Microphone listening defaults to push-to-talk; add PyAudio and set LISTEN_MODE=always to enable continuous listening.")
    return 0


class KalkiSetupWizard(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("KALKI Setup Wizard")
        self.geometry("550x750")
        self.resizable(True, True)
        self.minsize(500, 600)

        self.config_data = {
            "OWNER_NAME": "",
            "OWNER_TITLE": "Sir",
            "OWNER_CITY": "",
            "OWNER_STATE": "",
            "OWNER_COUNTRY": "",
            "GROQ_API_KEY": "",
            "EMAIL_ADDRESS": "",
            "EMAIL_APP_PASSWORD": "",
            "SPOTIFY_CLIENT_ID": "",
            "SPOTIFY_CLIENT_SECRET": "",
            "SPOTIFY_REDIRECT_URI": "http://127.0.0.1:8889/callback",
            "GITHUB_TOKEN": "",
            "SHODAN_API_KEY": "",
            "OPENAI_API_KEY": "",
            "ANTHROPIC_API_KEY": "",
            "GEMINI_API_KEY": "",
            "ELEVENLABS_API_KEY": "",
        }

        if os.path.exists(_USER_CONFIG_PATH):
            try:
                with open(_USER_CONFIG_PATH, "r", encoding="utf-8") as f:
                    self.config_data.update(json.load(f))
            except:
                pass

        self.show_boot_sequence()

    def show_boot_sequence(self):
        self.boot_frame = ctk.CTkFrame(self, fg_color="#000000")
        self.boot_frame.pack(fill="both", expand=True)
        
        self.boot_text = ctk.CTkTextbox(self.boot_frame, font=("Courier", 14, "bold"), fg_color="#000000", text_color="#00ffaa", state="disabled", wrap="word")
        self.boot_text.pack(fill="both", expand=True, padx=10, pady=10)
        
        lines = [
            "KALKI SYSTEM CORE // AUTONOMOUS AI INIT",
            "---------------------------------------",
            "Loading Neural Core...",
            "[OK] Memory Allocation: 8192 MB",
            "[OK] Cryptographic Subsystems: AES-256",
            "Probing LLM modules...",
            "WARNING: API Uplink not detected.",
            "Redirecting to Emergency Configuration protocol..."
        ]
        
        def type_line(idx):
            if idx < len(lines):
                self.boot_text.configure(state="normal")
                self.boot_text.insert("end", lines[idx] + "\n")
                self.boot_text.see("end")
                self.boot_text.configure(state="disabled")
                self.after(500, type_line, idx + 1)
            else:
                self.after(1500, self.end_boot_sequence)
                
        self.after(500, type_line, 0)
        
    def end_boot_sequence(self):
        self.boot_frame.destroy()
        self.setup_ui()

    def setup_ui(self):
        self.current_step = 0
        self.steps = []
        
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.nav_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.nav_frame.pack(fill="x", side="bottom", padx=20, pady=20)
        
        self.progress = ctk.CTkProgressBar(self.nav_frame)
        self.progress.pack(fill="x", pady=(0, 15))
        self.progress.set(0)

        self.step_label = ctk.CTkLabel(self.nav_frame, text="Welcome", text_color="#aeb4bd")
        self.step_label.pack(side="left", padx=(16, 0))
        
        self.back_btn = ctk.CTkButton(self.nav_frame, text="Back", command=self.prev_step, state="disabled")
        self.back_btn.pack(side="left")
        
        self.next_btn = ctk.CTkButton(self.nav_frame, text="Next", command=self.next_step)
        self.next_btn.pack(side="right")

        self.skip_btn = ctk.CTkButton(
            self.nav_frame, text="Skip optional setup", command=self.skip_optional_setup,
            fg_color="transparent", border_width=1, border_color="#5c6068", text_color="#c8ccd2",
        )
        
        self._build_steps()
        self.show_step(0)

    def _build_steps(self):
        # Step 0: Welcome
        f0 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        ctk.CTkLabel(f0, text="Welcome to KALKI", font=ctk.CTkFont(size=30, weight="bold")).pack(pady=(28, 8))
        ctk.CTkLabel(f0, text="Your personal AI assistant for Windows, Linux, and macOS.", font=ctk.CTkFont(size=15)).pack(pady=(0, 8))
        ctk.CTkLabel(f0, text="Start in seconds with the included managed AI. You can connect your own providers and services later in Settings.", font=ctk.CTkFont(size=12), text_color="#aeb4bd", wraplength=440, justify="center").pack(pady=(0, 22))
        
        btn_quick = ctk.CTkButton(
            f0, text="Get started now  →", font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#2da44e", hover_color="#2c974b", height=45,
            command=self.quick_1click_setup
        )
        btn_quick.pack(pady=10, fill="x", padx=40)
        
        ctk.CTkLabel(f0, text="No account, API key, or technical setup required.", font=ctk.CTkFont(size=11), text_color="#aeb4bd").pack(pady=(0, 18))

        ctk.CTkButton(f0, text="Customise my setup", font=ctk.CTkFont(size=13),
                      fg_color="#3a3a3f", hover_color="#4a4a4f", height=36,
                      command=lambda: self.next_step()).pack(pady=5, fill="x", padx=40)

        ctk.CTkButton(f0, text="Watch the setup guide", font=ctk.CTkFont(size=12),
                      fg_color="transparent", border_width=1, border_color="#5c6068", height=34,
                      command=lambda: webbrowser.open("https://youtu.be/vbUOy8oMqOM")).pack(pady=15, fill="x", padx=40)
        self.steps.append(f0)

        # Step 1: Identity
        f1 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._section_heading(f1, "1. Who are you?")
        self._help_text(f1, "Tell KALKI what to call you.")
        self.name_entry = self._create_input(f1, "Your Name:", self.config_data.get("OWNER_NAME", ""))
        self.title_entry = self._create_input(f1, "What should KALKI call you? (e.g., Sir, Boss):", self.config_data.get("OWNER_TITLE", "Sir"))
        self.steps.append(f1)

        # Step 2: Location
        f2 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._section_heading(f2, "2. Where are you?")
        self._help_text(f2, "KALKI uses this for local weather and news.")
        self.city_entry = self._create_input(f2, "City:", self.config_data.get("OWNER_CITY", ""))
        self.state_entry = self._create_input(f2, "State:", self.config_data.get("OWNER_STATE", ""))
        self.country_entry = self._create_input(f2, "Country:", self.config_data.get("OWNER_COUNTRY", ""))
        
        ctk.CTkButton(f2, text="⚡ Auto-Detect Location via IP", font=ctk.CTkFont(size=12),
                      fg_color="#5c6068", hover_color="#7b838c",
                      command=self.auto_detect_location).pack(anchor="w", padx=20, pady=10)
        self.steps.append(f2)

        # Step 3: Core AI
        f3 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._section_heading(f3, "3. Choose your AI")
        self._help_text(f3, "Use KALKI Managed AI for the simplest experience, or connect your own Groq account.")
        self.managed_ai_var = ctk.BooleanVar(value=self.config_data.get("MANAGED_AI_ENABLED", True))
        ctk.CTkCheckBox(f3, text="Use KALKI Managed AI (recommended)", variable=self.managed_ai_var).pack(anchor="w", padx=20, pady=(4, 14))
        self.groq_entry = self._create_input(f3, "Groq API Key (optional when Managed AI is on):", self.config_data.get("GROQ_API_KEY", ""), is_password=True)
        self._link(f3, "Get a free Groq API key", "https://console.groq.com")
        self.steps.append(f3)

        # Step 3.5: Voice & Personality
        fv = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._section_heading(fv, "4. Voice & Personality")
        self._help_text(fv, "Choose how you want KALKI to sound and listen.")

        voice_frame = ctk.CTkFrame(fv, fg_color="transparent")
        voice_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(voice_frame, text="Voice:", width=170, anchor="w").pack(side="left")
        self.voice_options = {
            "Ryan (British, stable KALKI voice)": "en-GB-RyanNeural",
            "Brian (US, natural male)": "en-US-BrianMultilingualNeural",
            "Andrew (US, natural male)": "en-US-AndrewMultilingualNeural",
            "Thomas (British, formal)": "en-GB-ThomasNeural",
            "Guy (US, standard male)": "en-US-GuyNeural",
            "Tony (US, deep male)": "en-US-TonyNeural",
        }
        current_voice = self.config_data.get("TTS_VOICE", "en-GB-RyanNeural")
        current_voice_label = next(
            (label for label, val in self.voice_options.items() if val == current_voice),
            "Ryan (British, stable KALKI voice)",
        )
        self.voice_var = ctk.StringVar(value=current_voice_label)
        ctk.CTkOptionMenu(voice_frame, values=list(self.voice_options.keys()),
                          variable=self.voice_var, width=280).pack(side="left", padx=10)

        listen_frame = ctk.CTkFrame(fv, fg_color="transparent")
        listen_frame.pack(fill="x", pady=(15, 5))
        ctk.CTkLabel(listen_frame, text="Listen Mode:", width=170, anchor="w").pack(side="left")
        self.listen_mode_var = ctk.StringVar(value=self.config_data.get("LISTEN_MODE", "always"))
        ctk.CTkSegmentedButton(
            listen_frame, values=["always", "push"], variable=self.listen_mode_var, width=280
        ).pack(side="left", padx=10)
        self._help_text(fv, "\"always\" = hands-free wake word (mic stays on). \"push\" = tap the "
                             "mic button to talk — use this if you share a Bluetooth headset with "
                             "your phone, since an always-on mic forces low-quality call mode on it.")

        self.spice_var = ctk.BooleanVar(value=self.config_data.get("PERSONALITY_SPICE", True))
        ctk.CTkCheckBox(fv, text="Personality spice (occasional witty/sarcastic replies)",
                        variable=self.spice_var).pack(fill="x", padx=20, pady=(15, 5))
        self.steps.append(fv)

        # Step 4: Integrations
        f4 = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self._section_heading(f4, "5. Integrations (Optional)")
        self._help_text(f4, "Connect Email, Google Calendar, Spotify, GitHub, and Shodan.")
        
        self.email_entry = self._create_input(f4, "Gmail Address:", self.config_data.get("EMAIL_ADDRESS", ""))
        self.email_pass_entry = self._create_input(f4, "16-char App Password:", self.config_data.get("EMAIL_APP_PASSWORD", ""), is_password=True)
        self._link(f4, "How to get a Gmail App Password?", "https://support.google.com/accounts/answer/185833")

        self.telegram_bot_entry = self._create_input(f4, "Telegram Bot Token:", self.config_data.get("TELEGRAM_BOT_TOKEN", ""), is_password=True)
        self.telegram_user_entry = self._create_input(f4, "Telegram User ID:", self.config_data.get("TELEGRAM_USER_ID", ""))
        self._link(f4, "Get a bot token via @BotFather on Telegram", "https://core.telegram.org/bots#how-do-i-create-a-bot")

        self.github_entry = self._create_input(f4, "GitHub Token:", self.config_data.get("GITHUB_TOKEN", ""), is_password=True)
        self._link(f4, "Get a GitHub API Token", "https://github.com/settings/tokens/new")
        self.shodan_entry = self._create_input(f4, "Shodan API Key:", self.config_data.get("SHODAN_API_KEY", ""), is_password=True)
        self._link(f4, "Get a Shodan API Key", "https://account.shodan.io/")
        
        self.spotify_id_entry = self._create_input(f4, "Spotify Client ID:", self.config_data.get("SPOTIFY_CLIENT_ID", ""))
        self.spotify_secret_entry = self._create_input(f4, "Spotify Secret:", self.config_data.get("SPOTIFY_CLIENT_SECRET", ""), is_password=True)
        self.spotify_redirect_entry = self._create_input(f4, "Redirect URI:", self.config_data.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8889/callback"))
        self._link(f4, "How to get Spotify API keys", "https://developer.spotify.com/dashboard")

        btn_frame = ctk.CTkFrame(f4, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10, padx=20)
        ctk.CTkButton(btn_frame, text="Setup Google Calendar OAuth", command=lambda: self.run_script("setup_google")).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Setup Spotify OAuth", command=lambda: self.run_script("setup_spotify")).pack(side="left", padx=5)
        self.steps.append(f4)

        # Step 5: Optional API Keys
        f5 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._section_heading(f5, "6. Optional AI APIs")
        self._help_text(f5, "Additional AI providers & voice synthesis. All optional.")
        self.openai_entry = self._create_input(f5, "OpenAI API Key:", self.config_data.get("OPENAI_API_KEY", ""), is_password=True)
        self.anthropic_entry = self._create_input(f5, "Anthropic API Key:", self.config_data.get("ANTHROPIC_API_KEY", ""), is_password=True)
        self.gemini_entry = self._create_input(f5, "Gemini API Key:", self.config_data.get("GEMINI_API_KEY", ""), is_password=True)
        self.elevenlabs_entry = self._create_input(f5, "ElevenLabs API Key:", self.config_data.get("ELEVENLABS_API_KEY", ""), is_password=True)
        self.steps.append(f5)

        # Step 6: Vision Recall & Cloud Sync
        f6 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._section_heading(f6, "7. Privacy & Backup")
        self._help_text(f6, "Vision Memory: Periodically screenshots and OCRs your screen to make it searchable.\nData never leaves your PC.")
        self.vision_var = ctk.BooleanVar(value=self.config_data.get("VISION_RECALL_ENABLED", False))
        self.vision_cb = ctk.CTkCheckBox(f6, text="Enable Vision Recall (Local OCR)", variable=self.vision_var)
        self.vision_cb.pack(fill="x", padx=20, pady=5)
        self.vision_retention_entry = self._create_input(f6, "Retention Days (e.g., 7):", str(self.config_data.get("VISION_RETENTION_DAYS", 7)))
        
        self._help_text(f6, "Cloud Sync Passphrase: Set this once. You'll need to re-enter it on a new machine to restore your data.")
        self.cloud_sync_entry = self._create_input(f6, "Cloud Sync Passphrase:", self.config_data.get("CLOUD_SYNC_PASSPHRASE", ""), is_password=True)
        self.steps.append(f6)

    def show_step(self, index):
        for i, step in enumerate(self.steps):
            if i == index:
                step.pack(fill="both", expand=True)
            else:
                step.pack_forget()
                
        self.progress.set((index + 1) / len(self.steps))
        labels = ["Welcome", "About you", "Your location", "AI provider", "Voice & personality", "Optional services", "Optional AI providers", "Privacy & backup"]
        self.step_label.configure(text=f"Step {index + 1} of {len(self.steps)} · {labels[index]}")
        
        self.back_btn.configure(state="normal" if index > 0 else "disabled")
        
        if index == len(self.steps) - 1:
            self.next_btn.configure(text="Finish & Start KALKI", fg_color="#2da44e", hover_color="#2c974b")
        else:
            self.next_btn.configure(text="Next", fg_color=["#c4c9d1", "#5c6068"], hover_color=["#aab0b8", "#7b838c"])

        if index >= 4:
            self.skip_btn.pack(side="right", padx=(0, 12))
        else:
            self.skip_btn.pack_forget()

    def next_step(self):
        if self.current_step == 3:
            groq_key = self.groq_entry.get().strip()
            if not groq_key and not self.managed_ai_var.get():
                messagebox.showerror("Choose an AI provider", "Turn on KALKI Managed AI or add a Groq API key to continue.")
                return

        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.show_step(self.current_step)
        else:
            self.save_config()

    def auto_detect_location(self):
        try:
            import cybertools
            info = cybertools.ip_info()
            if "city" in info and info["city"]:
                self.city_entry.delete(0, "end")
                self.city_entry.insert(0, info.get("city", ""))
                self.state_entry.delete(0, "end")
                self.state_entry.insert(0, info.get("region", ""))
                self.country_entry.delete(0, "end")
                self.country_entry.insert(0, info.get("country_name", ""))
                messagebox.showinfo("Location Resolved", f"Location auto-detected: {info.get('city')}, {info.get('region')}, {info.get('country_name')}")
            else:
                messagebox.showwarning("Auto-Detect", "Could not resolve location automatically. Please enter it manually.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to auto-detect location: {e}")

    def quick_1click_setup(self):
        """Set safe defaults and start the assistant with managed AI."""
        try:
            import cybertools
            info = cybertools.ip_info()
            if isinstance(info, dict) and "city" in info:
                self.config_data["OWNER_CITY"] = info.get("city", "")
                self.config_data["OWNER_STATE"] = info.get("region", "")
                self.config_data["OWNER_COUNTRY"] = info.get("country_name", "")
        except Exception:
            pass

        self.config_data["MANAGED_AI_ENABLED"] = True
        self.managed_ai_var.set(True)
        self.save_config()

    def skip_optional_setup(self):
        """Finish safely once the required profile and AI choices are complete."""
        self.save_config()

    def prev_step(self):
        if self.current_step > 0:
            self.current_step -= 1
            self.show_step(self.current_step)

    # ── helpers ────────────────────────────────────────────────────────

    def _section_heading(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(15, 5))

    def _help_text(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(size=12), text_color="gray").pack(anchor="w", pady=(0, 10))

    def _link(self, parent, text, url):
        lbl = ctk.CTkLabel(parent, text=text, text_color="cyan", cursor="hand2")
        lbl.pack(anchor="w", pady=(0, 10))
        lbl.bind("<Button-1>", lambda e: webbrowser.open(url))

    def _create_input(self, parent, label_text, default_value, is_password=False):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        ctk.CTkLabel(frame, text=label_text, width=170, anchor="w").pack(side="left")
        entry = ctk.CTkEntry(frame, width=280, show="*" if is_password else "")
        entry.insert(0, default_value)
        entry.pack(side="left", padx=10)
        return entry

    def run_script(self, script_name):
        cflags = subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        if getattr(sys, 'frozen', False):
            exe_map = {
                "setup_google": f"KALKI_Setup_Google{'.exe' if os.name == 'nt' else ''}",
                "setup_spotify": f"KALKI_Setup_Spotify{'.exe' if os.name == 'nt' else ''}"
            }
            exe_name = exe_map.get(script_name, f"{script_name}{'.exe' if os.name == 'nt' else ''}")
            tool_dirs = {
                "setup_google": "setup_google",
                "setup_spotify": "setup_spotify",
            }
            target = os.path.join(BASE_DIR, "services", tool_dirs[script_name], exe_name)
            if os.path.exists(target):
                subprocess.Popen([target], creationflags=cflags)
        else:
            subprocess.Popen([sys.executable, os.path.join(BASE_DIR, f"{script_name}.py")], creationflags=cflags)

    def save_config(self):
        try:
            retention_days = int(self.vision_retention_entry.get() or 7)
        except (ValueError, TypeError):
            retention_days = 7

        self.config_data.update({
            "OWNER_NAME": self.name_entry.get(),
            "OWNER_TITLE": self.title_entry.get(),
            "OWNER_CITY": self.city_entry.get(),
            "OWNER_STATE": self.state_entry.get(),
            "OWNER_COUNTRY": self.country_entry.get(),
            "MANAGED_AI_ENABLED": self.managed_ai_var.get(),
            "GROQ_API_KEY": self.groq_entry.get().strip(),
            "TTS_VOICE": self.voice_options.get(self.voice_var.get(), "en-GB-RyanNeural"),
            "LISTEN_MODE": self.listen_mode_var.get(),
            "PERSONALITY_SPICE": self.spice_var.get(),
            "EMAIL_ADDRESS": self.email_entry.get(),
            "EMAIL_APP_PASSWORD": self.email_pass_entry.get(),
            "GITHUB_TOKEN": self.github_entry.get(),
            "SHODAN_API_KEY": self.shodan_entry.get(),
            "SPOTIFY_CLIENT_ID": self.spotify_id_entry.get(),
            "SPOTIFY_CLIENT_SECRET": self.spotify_secret_entry.get(),
            "SPOTIFY_REDIRECT_URI": self.spotify_redirect_entry.get(),
            "OPENAI_API_KEY": self.openai_entry.get(),
            "ANTHROPIC_API_KEY": self.anthropic_entry.get(),
            "GEMINI_API_KEY": self.gemini_entry.get(),
            "ELEVENLABS_API_KEY": self.elevenlabs_entry.get(),
            "TELEGRAM_BOT_TOKEN": self.telegram_bot_entry.get(),
            "TELEGRAM_USER_ID": self.telegram_user_entry.get(),
            "VISION_RECALL_ENABLED": self.vision_var.get(),
            "VISION_RETENTION_DAYS": retention_days,
            "CLOUD_SYNC_PASSPHRASE": self.cloud_sync_entry.get(),
        })

        # Save secrets to the encrypted vault and persist only regular
        # preferences in the user-readable settings file.
        persisted_config = dict(self.config_data)
        try:
            from core import api_vault
            for key in SECRET_SETTING_KEYS:
                value = str(persisted_config.pop(key, "") or "").strip()
                if value:
                    api_vault.set_secret(key, value)
        except Exception as e:
            messagebox.showerror(
                "Secure save failed",
                f"KALKI could not securely store your credentials: {e}\n\n"
                "Your settings were not saved. Please try again."
            )
            return

        with open(_USER_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(persisted_config, f, indent=4)

        try:
            _apply_to_config_py(persisted_config)
        except Exception as e:
            messagebox.showwarning(
                "Partial save",
                f"Your settings were saved, but config.py couldn't be updated automatically:\n{e}\n\n"
                "You may need to paste your Groq key into config.py by hand."
            )

        marker_path = os.path.join(USER_DATA_DIR, "setup_complete.marker")
        with open(marker_path, "w", encoding="utf-8") as f:
            f.write("Setup complete")

        self.destroy()
        
        main_script = os.path.join(BASE_DIR, "main_app.py")
        if getattr(sys, 'frozen', False):
            target = os.path.join(BASE_DIR, "KALKI.exe" if os.name == "nt" else "KALKI")
            if os.path.exists(target):
                subprocess.Popen([target])
        else:
            if os.path.exists(main_script):
                subprocess.Popen([sys.executable, main_script])


if __name__ == "__main__":
    force_headless = "--headless" in sys.argv
    display_available = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    if force_headless or not _GUI_AVAILABLE or (os.name != "nt" and not display_available):
        raise SystemExit(run_headless_setup())
    app = KalkiSetupWizard()
    app.mainloop()
