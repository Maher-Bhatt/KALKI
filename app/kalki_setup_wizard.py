import os
import sys
import json
import subprocess
import customtkinter as ctk
from tkinter import messagebox

BASE_DIR = os.path.dirname(os.path.abspath(
    sys.executable if getattr(sys, "frozen", False) else __file__
))
_USER_CONFIG_PATH = os.path.join(BASE_DIR, "user_config.json")

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class KalkiSetupWizard(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("KALKI Setup Wizard")
        self.geometry("500x650")
        self.resizable(False, False)
        
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
            "GITHUB_TOKEN": "",
            "SHODAN_API_KEY": ""
        }
        
        if os.path.exists(_USER_CONFIG_PATH):
            try:
                with open(_USER_CONFIG_PATH, "r", encoding="utf-8") as f:
                    self.config_data.update(json.load(f))
            except:
                pass
                
        self.setup_ui()

    def setup_ui(self):
        self.scrollable_frame = ctk.CTkScrollableFrame(self, width=450, height=550)
        self.scrollable_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        ctk.CTkLabel(self.scrollable_frame, text="KALKI Initial Setup", font=ctk.CTkFont(size=24, weight="bold")).pack(pady=10)
        
        # 1. Identity
        ctk.CTkLabel(self.scrollable_frame, text="1. Identity", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(10,0))
        self.name_entry = self.create_input("Your Name:", self.config_data.get("OWNER_NAME", ""))
        self.title_entry = self.create_input("Your Title (e.g., Sir, Boss):", self.config_data.get("OWNER_TITLE", "Sir"))
        
        # 2. Location
        ctk.CTkLabel(self.scrollable_frame, text="2. Location", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(15,0))
        self.city_entry = self.create_input("City:", self.config_data.get("OWNER_CITY", ""))
        self.state_entry = self.create_input("State:", self.config_data.get("OWNER_STATE", ""))
        self.country_entry = self.create_input("Country:", self.config_data.get("OWNER_COUNTRY", ""))
        
        # 3. Groq API
        ctk.CTkLabel(self.scrollable_frame, text="3. Groq API Key (Required for AI)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(15,0))
        self.groq_entry = self.create_input("Groq API Key:", self.config_data.get("GROQ_API_KEY", ""), is_password=True)
        link = ctk.CTkLabel(self.scrollable_frame, text="Get free key at console.groq.com", text_color="cyan", cursor="hand2")
        link.pack(anchor="w", padx=20)
        link.bind("<Button-1>", lambda e: os.startfile("https://console.groq.com"))
        
        # 4. Email
        ctk.CTkLabel(self.scrollable_frame, text="4. Email (Optional, Gmail App Password)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(15,0))
        self.email_entry = self.create_input("Gmail Address:", self.config_data.get("EMAIL_ADDRESS", ""))
        self.email_pass_entry = self.create_input("16-char App Password:", self.config_data.get("EMAIL_APP_PASSWORD", ""), is_password=True)
        
        # 5. Integrations
        ctk.CTkLabel(self.scrollable_frame, text="5. Integrations (Optional)", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", pady=(15,0))
        self.github_entry = self.create_input("GitHub Token:", self.config_data.get("GITHUB_TOKEN", ""), is_password=True)
        self.shodan_entry = self.create_input("Shodan API Key:", self.config_data.get("SHODAN_API_KEY", ""), is_password=True)
        
        # Oauth Integrations Buttons
        btn_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=10, padx=20)
        
        ctk.CTkButton(btn_frame, text="Setup Google Calendar OAuth", command=lambda: self.run_script("setup_google")).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Setup Spotify OAuth", command=lambda: self.run_script("setup_spotify")).pack(side="left", padx=5)
        
        # Save Button
        self.save_btn = ctk.CTkButton(self, text="SAVE CONFIGURATION", font=ctk.CTkFont(weight="bold"), 
                                      height=40, command=self.save_config)
        self.save_btn.pack(pady=10, fill="x", padx=20)
        
    def create_input(self, label_text, default_value, is_password=False):
        frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
        frame.pack(fill="x", pady=2, padx=20)
        lbl = ctk.CTkLabel(frame, text=label_text, width=150, anchor="w")
        lbl.pack(side="left")
        entry = ctk.CTkEntry(frame, width=250, show="*" if is_password else "")
        entry.insert(0, default_value)
        entry.pack(side="left", padx=10)
        return entry
        
    def run_script(self, script_name):
        # script_name is either 'setup_google' or 'setup_spotify'
        if getattr(sys, 'frozen', False):
            # Map script name to EXE name
            exe_map = {
                "setup_google": "KALKI_Setup_Google.exe",
                "setup_spotify": "KALKI_Setup_Spotify.exe"
            }
            exe_name = exe_map.get(script_name, f"{script_name}.exe")
            target = os.path.join(BASE_DIR, exe_name)
            if os.path.exists(target):
                subprocess.Popen([target])
        else:
            subprocess.Popen([sys.executable, os.path.join(BASE_DIR, f"{script_name}.py")])
            
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
            "SHODAN_API_KEY": self.shodan_entry.get()
        })
        
        with open(_USER_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=4)
            
        self.destroy()

if __name__ == "__main__":
    app = KalkiSetupWizard()
    app.mainloop()
