import requests
import config

def is_configured():
    return bool(getattr(config, "GITHUB_TOKEN", None) and config.GITHUB_TOKEN != "your_personal_access_token")

def check_notifications(limit=5):
    """Fetch unread GitHub notifications."""
    if not is_configured():
        return "GitHub is not configured. Please add your GITHUB_TOKEN to config.py."
    
    headers = {
        "Authorization": f"token {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        r = requests.get("https://api.github.com/notifications", headers=headers, timeout=10)
        if r.status_code == 200:
            notes = r.json()
            if not notes:
                return "No new GitHub notifications, Sir."
            
            summary_parts = []
            for n in notes[:limit]:
                repo = n["repository"]["name"]
                subject = n["subject"]["title"]
                summary_parts.append(f"In {repo}: {subject}")
            
            count = len(notes)
            text = f"You have {count} unread GitHub notification{'s' if count != 1 else ''}. " + ". ".join(summary_parts)
            return text[:600]
        elif r.status_code == 401:
            return "GitHub token is invalid or expired."
        else:
            return f"GitHub returned an error: {r.status_code}"
    except Exception as e:
        return f"Could not reach GitHub: {e}"

def get_repo_stats(username):
    """Fetch basic stats for a user's repositories (stars, forks)."""
    if not is_configured():
        return "GitHub is not configured."
        
    headers = {
        "Authorization": f"token {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    try:
        r = requests.get(f"https://api.github.com/users/{username}/repos?per_page=100", headers=headers, timeout=10)
        if r.status_code == 200:
            repos = r.json()
            total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
            return f"User {username} has {total_stars} total stars across {len(repos)} public repositories."
        else:
            return f"Could not fetch stats for {username}."
    except Exception as e:
        return f"Error connecting to GitHub: {e}"
