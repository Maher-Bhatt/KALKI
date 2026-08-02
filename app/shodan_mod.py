import requests
import config

def is_configured():
    return bool(getattr(config, "SHODAN_API_KEY", None) and config.SHODAN_API_KEY != "your_shodan_api_key")

def scan_ip(ip):
    """Query Shodan API for details about a specific IP."""
    if not is_configured():
        return "Shodan API key is not configured. Please add it to config.py."
        
    try:
        url = f"https://api.shodan.io/shodan/host/{ip}?key={config.SHODAN_API_KEY}"
        r = requests.get(url, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            org = data.get("org", "Unknown Org")
            os_name = data.get("os", "Unknown OS")
            ports = data.get("ports", [])
            vulns = data.get("vulns", [])
            
            port_str = ", ".join(map(str, ports[:5]))
            if len(ports) > 5:
                port_str += f" and {len(ports)-5} more"
                
            vuln_str = f"It has {len(vulns)} known vulnerabilities." if vulns else "No known vulnerabilities listed."
            
            return f"Shodan report for {ip}: Organization is {org}. OS is {os_name}. Open ports: {port_str}. {vuln_str}"
        elif r.status_code == 404:
            return f"No information found for IP {ip} on Shodan."
        elif r.status_code == 401:
            return "Shodan API key is invalid or expired."
        else:
            return f"Shodan returned an error: {r.status_code}"
    except Exception as e:
        return f"Could not reach Shodan: {e}"
