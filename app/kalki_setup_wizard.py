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
        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=500, height=650)
        self.scrollable_frame.pack(pady=10, padx=10, fill="both", expand=True)

        ctk.CTkLabel(self.scrollable_frame, text="KALKI Initial Setup",
                     font=ctk.CTkFont(size=24, weight="bold")).pack(pady=10)

        # Tutorial button
        ctk.CTkButton(
            self.scrollable_frame, text="📺  Watch Setup Tutorial",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#e03e3e", hover_color="#c93030", height=38,
            command=lambda: webbrowser.open("https://youtu.be/vbUOy8oMqOM")
        ).pack(fill="x", padx=20, pady=(0, 10))

        # ── 1. Identity ──────────────────────────────────────────────
        self._section_heading("1. Identity")
        self._help_text("Tell KALKI your name so it can address you properly.")
        self.name_entry = self._create_input("Your Name:", self.config_data.get("OWNER_NAME", ""))
        self.title_entry = self._create_input("Your Title (e.g., Sir, Boss):", self.config_data.get("OWNER_TITLE", "Sir"))

        # ── 2. Location ──────────────────────────────────────────────
        self._section_heading("2. Location")
        self._help_text("Used for weather, news, and location-aware answers.")
        self.city_entry = self._create_input("City:", self.config_data.get("OWNER_CITY", ""))
        self.state_entry = self._create_input("State:", self.config_data.get("OWNER_STATE", ""))
        self.country_entry = self._create_input("Country:", self.config_data.get("OWNER_COUNTRY", ""))

        # ── 3. Groq API ──────────────────────────────────────────────
        self._section_heading("3. Groq API Key (Required for AI)")
        self._help_text("Required. Powers KALKI's brain. Free tier available.")
        self.groq_entry = self._create_input("Groq API Key:", self.config_data.get("GROQ_API_KEY", ""), is_password=True)
        self._link("Get free key at console.groq.com", "https://console.groq.com")

        # ── 4. API Keys ──────────────────────────────────────────────
        self._section_heading("4. API Keys (Optional)")
        self._help_text("Additional AI providers & voice synthesis. All optional.")

        self.openai_entry = self._create_input("OpenAI API Key:", self.config_data.get("OPENAI_API_KEY", ""), is_password=True)
        self._link("Get Key → platform.openai.com", "https://platform.openai.com/api-keys")

        self.anthropic_entry = self._create_input("Anthropic API Key:", self.config_data.get("ANTHROPIC_API_KEY", ""), is_password=True)
        self._link("Get Key → console.anthropic.com", "https://console.anthropic.com/")

        self.gemini_entry = self._create_input("Gemini API Key:", self.config_data.get("GEMINI_API_KEY", ""), is_password=True)
        self._link("Get Key → aistudio.google.com", "https://aistudio.google.com/apikey")

        self.elevenlabs_entry = self._create_input("ElevenLabs API Key:", self.config_data.get("ELEVENLABS_API_KEY", ""), is_password=True)
        self._link("Get Key → elevenlabs.io", "https://elevenlabs.io/")

        # ── 5. Email ──────────────────────────────────────────────────
        self._section_heading("5. Email (Optional, Gmail App Password)")
        self._help_text("Lets KALKI send emails on your behalf via Gmail.")
        self.email_entry = self._create_input("Gmail Address:", self.config_data.get("EMAIL_ADDRESS", ""))
        self.email_pass_entry = self._create_input("16-char App Password:", self.config_data.get("EMAIL_APP_PASSWORD", ""), is_password=True)

        email_help = ctk.CTkLabel(self.scrollable_frame, text="How to get an App Password?", text_color="cyan", cursor="hand2")
        email_help.pack(anchor="w", padx=20)
        email_help.bind("<Button-1>", lambda e: messagebox.showinfo(
            "Gmail App Password",
            "1. Turn on 2-Step Verification in Google Account.\n"
            "2. Go to Security > App passwords.\n"
            "3. Create app 'KALKI' and generate 16-digit code."
        ))

        # ── 6. Integrations ──────────────────────────────────────────
        self._section_heading("6. Integrations (Optional)")
        self._help_text("Connect GitHub and Shodan for code & network features.")

        self.github_entry = self._create_input("GitHub Token:", self.config_data.get("GITHUB_TOKEN", ""), is_password=True)
        gh_help = ctk.CTkLabel(self.scrollable_frame, text="How to get GitHub Token?", text_color="cyan", cursor="hand2")
        gh_help.pack(anchor="w", padx=20)
        gh_help.bind("<Button-1>", lambda e: messagebox.showinfo(
            "GitHub Token",
            "1. GitHub Settings > Developer settings.\n"
            "2. Personal access tokens > Generate new token.\n"
            "3. Select 'repo' scope and generate."
        ))

        self.shodan_entry = self._create_input("Shodan API Key:", self.config_data.get("SHODAN_API_KEY", ""), is_password=True)
        sh_help = ctk.CTkLabel(self.scrollable_frame, text="How to get Shodan Key?", text_color="cyan", cursor="hand2")
        sh_help.pack(anchor="w", padx=20)
        sh_help.bind("<Button-1>", lambda e: messagebox.showinfo(
            "Shodan API Key",
            "1. Create free account at shodan.io\n"
            "2. View your Account page to copy the API Key."
        ))

        # ── 7. Spotify Integration ───────────────────────────────────
        self._section_heading("7. Spotify Integration (Optional)")
        self._help_text("Play and control music through Spotify. Needs a Spotify Developer app.")

        self.spotify_id_entry = self._create_input("Spotify Client ID:", self.config_data.get("SPOTIFY_CLIENT_ID", ""))
        self.spotify_secret_entry = self._create_input("Spotify Client Secret:", self.config_data.get("SPOTIFY_CLIENT_SECRET", ""), is_password=True)
        self.spotify_redirect_entry = self._create_input("Redirect URI:", self.config_data.get("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8889/callback"))
        self._link("Get Spotify credentials at developer.spotify.com/dashboard", "https://developer.spotify.com/dashboard")

        # ── 8. Google Calendar ────────────────────────────────────────
        self._section_heading("8. Google Calendar (Optional)")
        self._help_text("Let KALKI read and create events on your Google Calendar.")
        self._link("Setup Google Calendar at console.cloud.google.com", "https://console.cloud.google.com")

        # OAuth Buttons
        btn_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10, padx=20)

        ctk.CTkButton(btn_frame, text="Setup Google Calendar OAuth",
                       command=lambda: self.run_script("setup_google")).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Setup Spotify OAuth",
                       command=lambda: self.run_script("setup_spotify")).pack(side="left", padx=5)

        # Save Button
        self.save_btn = ctk.CTkButton(
            self, text="SAVE CONFIGURATION",
            font=ctk.CTkFont(weight="bold"), height=40,
            command=self.save_config
        )
        self.save_btn.pack(pady=10, fill="x", padx=20)

    # ── helpers ────────────────────────────────────────────────────────

    def _section_heading(self, text):
        ctk.CTkLabel(self.scrollable_frame, text=text,
                     font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(15, 0))

    def _help_text(self, text):
        ctk.CTkLabel(self.scrollable_frame, text=text,
                     font=ctk.CTkFont(size=11), text_color="gray").pack(anchor="w", padx=20, pady=(0, 4))

    def _link(self, text, url):
        lbl = ctk.CTkLabel(self.scrollable_frame, text=text, text_color="cyan", cursor="hand2")
        lbl.pack(anchor="w", padx=20)
        lbl.bind("<Button-1>", lambda e: webbrowser.open(url))

    def _create_input(self, label_text, default_value, is_password=False):
        frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        frame.pack(fill="x", pady=2, padx=20)
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
        groq_key = self.groq_entry.get().strip()

        if not groq_key:
            messagebox.showerror("Validation Error", "Groq API Key is required to run KALKI. Please enter it.")
            return

        self.config_data.update({
            "OWNER_NAME": self.name_entry.get(),
            "OWNER_TITLE": self.title_entry.get(),
            "OWNER_CITY": self.city_entry.get(),
            "OWNER_STATE": self.state_entry.get(),
            "OWNER_COUNTRY": self.country_entry.get(),
            "GROQ_API_KEY": groq_key,
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
        })

        with open(_USER_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=4)

        self.destroy()


if __name__ == "__main__":
    app = KalkiSetupWizard()
    app.mainloop()
