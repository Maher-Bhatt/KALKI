TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Searches the web using DuckDuckGo for live information (weather, news, facts).",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to run on the web."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_emails",
            "description": "Fetches a summary of the user's latest important/unread emails from their inbox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of emails to fetch (default 5)."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_calendar_events",
            "description": "Fetches the user's Google Calendar events for today or upcoming days.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days_ahead": {
                        "type": "integer",
                        "description": "0 for today, 1 for tomorrow, etc. Default 0."
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Sends an email to a specific address using SMTP.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_address": {
                        "type": "string",
                        "description": "The recipient's email address."
                    },
                    "subject": {
                        "type": "string",
                        "description": "The subject of the email."
                    },
                    "body": {
                        "type": "string",
                        "description": "The body content of the email."
                    }
                },
                "required": ["to_address", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Creates a new event in the user's primary Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "The title or summary of the event."
                    },
                    "start_time_iso": {
                        "type": "string",
                        "description": "The start time in ISO 8601 format (e.g., 2026-07-05T14:30:00Z)."
                    },
                    "duration_mins": {
                        "type": "integer",
                        "description": "The duration of the event in minutes. Defaults to 60."
                    }
                },
                "required": ["summary", "start_time_iso"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_calendar_event",
            "description": "Deletes an event from the user's primary Google Calendar by event ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "The Google Calendar event ID to delete."
                    }
                },
                "required": ["event_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "scan_network",
            "description": "Scans a target domain or IP for open ports, vulnerabilities, and attack surface.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "The domain name (e.g., example.com) or IP address to scan."
                    }
                },
                "required": ["target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "play_music",
            "description": "Plays music on Spotify.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The song, artist, or playlist name to play."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_briefing",
            "description": "Fetches a comprehensive morning briefing including weather, news, first calendar event, and urgent emails.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "system_control",
            "description": "Controls the Windows operating system (lock screen, sleep, restart, shutdown, volume, open apps). For sleep/restart/shutdown this only queues the action — it still requires the user to say 'confirm' before anything actually happens.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action to perform: 'lock', 'sleep', 'restart', 'shutdown', 'volume_set', or 'open_app'."
                    },
                    "target": {
                        "type": "string",
                        "description": "The target app name to open (e.g., 'notepad', 'vscode'), or the volume level (0-100)."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_local_document",
            "description": "Reads the text of a local document or file from the user's computer for context.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "The name of the file to read (e.g., 'contract.pdf', 'notes.txt')."
                    }
                },
                "required": ["filename"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "manage_tasks",
            "description": "Manage the user's task list (TODO list). Use this to add, list, complete, delete, or clear tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action to perform: 'list', 'add', 'complete', 'delete', 'clear_all'."
                    },
                    "text": {
                        "type": "string",
                        "description": "The task text or ID (used for add, complete, delete)."
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_url",
            "description": "Fetches the raw text content of any website URL (for answering questions about a webpage or summarizing).",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL to read (e.g., 'https://en.wikipedia.org/wiki/Main_Page')."
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_routine",
            "description": "Creates a new custom voice routine/mode for KALKI. Parses user instructions into a list of actions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the routine (e.g., 'workout mode', 'reading time')."
                    },
                    "actions": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "description": "List of actions. Each action is a tuple/list: [action_name, arg1, arg2]. Valid actions: open_app (arg: app_name), open_url (arg: url), set_volume (arg: 0-100), kill_app (arg: app_name), run_cmd (arg: cmd), lock_pc, speak (arg: text)."
                    },
                    "aliases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "A list of spoken phrases that should trigger this routine."
                    }
                },
                "required": ["name", "actions"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_emails_as_read",
            "description": "Marks all unread emails in the user's inbox as read.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "store_user_memory",
            "description": "Save a personal fact, preference, or detail about Sir to his persistent memory bank so it is remembered in future sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fact": {
                        "type": "string",
                        "description": "The personal fact or preference to remember (e.g. 'Sir's favorite programming language is Python')."
                    },
                    "importance": {
                        "type": "integer",
                        "description": "How important this fact is on a scale of 1 to 10 (default 5)."
                    }
                },
                "required": ["fact"]
            }
        }
    }
]

