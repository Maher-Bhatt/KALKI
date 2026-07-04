def get_schema():
    return {
        "type": "function",
        "function": {
            "name": "tell_joke_plugin",
            "description": "Tells a funny programmer joke. Use this when the user asks for a joke about coding.",
            "parameters": {
                "type": "object",
                "properties": {},
            }
        }
    }

def execute(kwargs):
    import random
    jokes = [
        "Why do programmers prefer dark mode? Because light attracts bugs.",
        "There are 10 types of people in the world: those who understand binary, and those who don't.",
        "A SQL query goes into a bar, walks up to two tables and asks... 'Can I join you?'"
    ]
    return random.choice(jokes)
