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
            "description": "Controls the Windows operating system (lock screen, volume, open apps).",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action to perform: 'lock', 'volume_set', or 'open_app'."
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
    }
]
