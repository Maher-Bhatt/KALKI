import os
import re
import sys
import json
import shutil
import webbrowser
import subprocess
import customtkinter as ctk
from tkinter import messagebox

BASE_DIR = os.path.dirname(os.path.abspath(
    sys.executable if getattr(sys, "frozen", False) else __file__
))
USER_DATA_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "KALKI")
os.makedirs(USER_DATA_DIR, exist_ok=True)
_USER_CONFIG_PATH = os.path.join(USER_DATA_DIR, "user_config.json")

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
    if not os.path.exists(cfg_path):
        if os.path.exists(example_path):
            shutil.copy(example_path, cfg_path)
        else:
            return

    with open(cfg_path, "r", encoding="utf-8") as f:
        text = f.read()

    appended = []
    for key, value in updates.items():
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
        
        self.back_btn = ctk.CTkButton(self.nav_frame, text="Back", command=self.prev_step, state="disabled")
        self.back_btn.pack(side="left")
        
        self.next_btn = ctk.CTkButton(self.nav_frame, text="Next", command=self.next_step)
        self.next_btn.pack(side="right")
        
        self._build_steps()
        self.show_step(0)

    def _build_steps(self):
        # Step 0: Welcome
        f0 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        ctk.CTkLabel(f0, text="Welcome to KALKI", font=ctk.CTkFont(size=28, weight="bold")).pack(pady=40)
        ctk.CTkLabel(f0, text="Let's get your personal AI assistant configured.", font=ctk.CTkFont(size=14)).pack(pady=10)
        ctk.CTkButton(f0, text="📺  Watch Setup Tutorial", font=ctk.CTkFont(size=14, weight="bold"),
                      fg_color="#e03e3e", hover_color="#c93030", height=38,
                      command=lambda: webbrowser.open("https://youtu.be/vbUOy8oMqOM")).pack(pady=30)
        self.steps.append(f0)

        # Step 1: Identity
        f1 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._section_heading(f1, "1. Identity")
        self._help_text(f1, "Tell KALKI your name so it can address you properly.")
        self.name_entry = self._create_input(f1, "Your Name:", self.config_data.get("OWNER_NAME", ""))
        self.title_entry = self._create_input(f1, "Your Title (e.g., Sir, Boss):", self.config_data.get("OWNER_TITLE", "Sir"))
        self.steps.append(f1)

        # Step 2: Location
        f2 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._section_heading(f2, "2. Location")
        self._help_text(f2, "Used for weather, news, and location-aware answers.")
        self.city_entry = self._create_input(f2, "City:", self.config_data.get("OWNER_CITY", ""))
        self.state_entry = self._create_input(f2, "State:", self.config_data.get("OWNER_STATE", ""))
        self.country_entry = self._create_input(f2, "Country:", self.config_data.get("OWNER_COUNTRY", ""))
        self.steps.append(f2)

        # Step 3: Core AI
        f3 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._section_heading(f3, "3. Core AI")
        self._help_text(f3, "Provide a free Groq API key, or use Managed AI Mode.")
        self.managed_ai_var = ctk.BooleanVar(value=self.config_data.get("MANAGED_AI_ENABLED", False))
        self.managed_ai_cb = ctk.CTkCheckBox(f3, text="Use Managed AI (Zero API Key required, proxied through our server)", variable=self.managed_ai_var)
        self.managed_ai_cb.pack(fill="x", padx=20, pady=5)
        
        self.groq_entry = self._create_input(f3, "Or bring your own Groq API Key:", self.config_data.get("GROQ_API_KEY", ""), is_password=True)
        self._link(f3, "Get free key at console.groq.com", "https://console.groq.com")
        self.steps.append(f3)

        # Step 3.5: Voice & Personality (previously only editable by hand in config.py)
        fv = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._section_heading(fv, "4. Voice & Personality")
        self._help_text(fv, "How KALKI sounds and listens. These used to require editing config.py by hand.")

        voice_frame = ctk.CTkFrame(fv, fg_color="transparent")
        voice_frame.pack(fill="x", pady=5)
        ctk.CTkLabel(voice_frame, text="Voice:", width=170, anchor="w").pack(side="left")
        self.voice_options = {
            "Brian (US, natural male — default)": "en-US-BrianMultilingualNeural",
            "Andrew (US, natural male, newer)": "en-US-AndrewMultilingualNeural",
            "Ryan (British, JARVIS-style butler)": "en-GB-RyanNeural",
            "Thomas (British, formal butler)": "en-GB-ThomasNeural",
            "Guy (US, standard male)": "en-US-GuyNeural",
            "Tony (US, deep male)": "en-US-TonyNeural",
        }
        current_voice = self.config_data.get("TTS_VOICE", "en-US-BrianMultilingualNeural")
        current_voice_label = next(
            (label for label, val in self.voice_options.items() if val == current_voice),
            "Brian (US, natural male — default)",
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
        self.shodan_entry = self._create_input(f4, "Shodan API Key:", self.config_data.get("SHODAN_API_KEY", ""), is_password=True)
        
        self.spotify_id_entry = self._create_input(f4, "Spotify Client ID:", self.config_data.get("SPOTIFY_CLIENT_ID", ""))
        self.spotify_secret_entry = self._create_input(f4, "Spotify Secret:", self.config_data.get("SPOTIFY_CLIENT_SECRET", ""), is_password=True)
        self.spotify_redirect_entry = self._create_input(f4, "Redirect URI:", self.config_data.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8889/callback"))

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
        
        self.back_btn.configure(state="normal" if index > 0 else "disabled")
        
        if index == len(self.steps) - 1:
            self.next_btn.configure(text="Finish & Start KALKI", fg_color="#2da44e", hover_color="#2c974b")
        else:
            self.next_btn.configure(text="Next", fg_color=["#c4c9d1", "#5c6068"], hover_color=["#aab0b8", "#7b838c"])

    def next_step(self):
        if self.current_step == 3:
            groq_key = self.groq_entry.get().strip()
            if not groq_key and not self.managed_ai_var.get():
                messagebox.showerror("Validation Error", "Groq API Key is required (unless Managed AI is enabled).")
                return

        if self.current_step < len(self.steps) - 1:
            self.current_step += 1
            self.show_step(self.current_step)
        else:
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
                "setup_google": "KALKI_Setup_Google.exe",
                "setup_spotify": "KALKI_Setup_Spotify.exe"
            }
            exe_name = exe_map.get(script_name, f"{script_name}.exe")
            target = os.path.join(BASE_DIR, exe_name)
            if os.path.exists(target):
                subprocess.Popen([target], creationflags=cflags)
        else:
            subprocess.Popen([sys.executable, os.path.join(BASE_DIR, f"{script_name}.py")], creationflags=cflags)

    def save_config(self):
        self.config_data.update({
            "OWNER_NAME": self.name_entry.get(),
            "OWNER_TITLE": self.title_entry.get(),
            "OWNER_CITY": self.city_entry.get(),
            "OWNER_STATE": self.state_entry.get(),
            "OWNER_COUNTRY": self.country_entry.get(),
            "MANAGED_AI_ENABLED": self.managed_ai_var.get(),
            "GROQ_API_KEY": self.groq_entry.get().strip(),
            "TTS_VOICE": self.voice_options.get(self.voice_var.get(), "en-US-BrianMultilingualNeural"),
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
            "VISION_RETENTION_DAYS": int(self.vision_retention_entry.get() or 7),
            "CLOUD_SYNC_PASSPHRASE": self.cloud_sync_entry.get(),
        })

        with open(_USER_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=4)

        try:
            _apply_to_config_py(self.config_data)
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
            target = os.path.join(BASE_DIR, "KALKI.exe")
            if os.path.exists(target):
                subprocess.Popen([target])
        else:
            if os.path.exists(main_script):
                subprocess.Popen([sys.executable, main_script])


if __name__ == "__main__":
    app = KalkiSetupWizard()
    app.mainloop()
