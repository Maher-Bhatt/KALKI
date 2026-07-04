import os
import sys
import json
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

        # Step 4: Integrations
        f4 = ctk.CTkScrollableFrame(self.main_container, fg_color="transparent")
        self._section_heading(f4, "4. Integrations (Optional)")
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
        self._section_heading(f5, "5. Optional AI APIs")
        self._help_text(f5, "Additional AI providers & voice synthesis. All optional.")
        self.openai_entry = self._create_input(f5, "OpenAI API Key:", self.config_data.get("OPENAI_API_KEY", ""), is_password=True)
        self.anthropic_entry = self._create_input(f5, "Anthropic API Key:", self.config_data.get("ANTHROPIC_API_KEY", ""), is_password=True)
        self.gemini_entry = self._create_input(f5, "Gemini API Key:", self.config_data.get("GEMINI_API_KEY", ""), is_password=True)
        self.elevenlabs_entry = self._create_input(f5, "ElevenLabs API Key:", self.config_data.get("ELEVENLABS_API_KEY", ""), is_password=True)
        self.steps.append(f5)

        # Step 6: Vision Recall & Cloud Sync
        f6 = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self._section_heading(f6, "6. Privacy & Backup")
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
            self.next_btn.configure(text="Next", fg_color=["#3a7ebf", "#1f538d"], hover_color=["#325882", "#14375e"])

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
