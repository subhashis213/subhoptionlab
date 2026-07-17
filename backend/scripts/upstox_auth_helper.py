"""
Upstox OAuth 2.0 Token Generation Helper.

Exchanges an authorization code from Upstox for a daily Bearer Access Token
and saves it to backend/.env.

Usage:
1. Open the Upstox login URL in your browser:
   https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id=78e833c5-cb08-4ea5-97ea-45e4aff8252a&redirect_uri=YOUR_REDIRECT_URI

2. After logging in, Upstox will redirect your browser to your Redirect URI with `?code=XYZ...` in the address bar.

3. Run this script and paste the `code` when prompted:
   python scripts/upstox_auth_helper.py
"""

import os
import sys
import json
import urllib.request
import urllib.parse
from pathlib import Path

backend_dir = Path(__file__).parent.parent
env_file = backend_dir / ".env"

def get_env_var(key, default=""):
    if env_file.exists():
        with open(env_file, "r") as f:
            for line in f:
                if line.strip().startswith(f"{key}="):
                    return line.strip().split("=", 1)[1].strip()
    return os.environ.get(key, default)

API_KEY = get_env_var("UPSTOX_API_KEY", "78e833c5-cb08-4ea5-97ea-45e4aff8252a")
API_SECRET = get_env_var("UPSTOX_API_SECRET", "8l6572ardy")
DEFAULT_REDIRECT = get_env_var("UPSTOX_REDIRECT_URI", "https://127.0.0.1:5000/")

def main():
    print("=" * 60)
    print("UPSTOX API v2 — ACCESS TOKEN GENERATOR")
    print("=" * 60)
    print(f"API Key (Client ID): {API_KEY}")
    print(f"Default Redirect URI: {DEFAULT_REDIRECT}")
    print()
    
    redirect_uri = input(f"Enter your app's Redirect URI [{DEFAULT_REDIRECT}]: ").strip() or DEFAULT_REDIRECT
    
    login_url = (
        f"https://api.upstox.com/v2/login/authorization/dialog"
        f"?response_type=code&client_id={API_KEY}&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
    )
    
    print("\nSTEP 1: Open this URL in your browser to log into Upstox and authorize:")
    print("-" * 60)
    print(login_url)
    print("-" * 60)
    print("\nAfter logging in, Upstox will redirect to your Redirect URI.")
    print("Look at the URL address bar in your browser. Copy the `code=...` value.\n")
    
    auth_code = input("Enter the `code` from the redirect URL: ").strip()
    if not auth_code:
        print("Error: No code provided. Exiting.")
        return

    print("\nExchanging authorization code for Access Token...")
    
    token_url = "https://api.upstox.com/v2/login/authorization/token"
    payload = urllib.parse.urlencode({
        "code": auth_code,
        "client_id": API_KEY,
        "client_secret": API_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }).encode("utf-8")
    
    req = urllib.request.Request(
        token_url,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            access_token = data.get("access_token")
            if not access_token:
                print("Error: access_token not found in response:", data)
                return
            
            print("\n✅ SUCCESS! Access Token Generated successfully!")
            print(f"Token (first 20 chars): {access_token[:20]}...")
            
            # Save to .env
            lines = []
            if env_file.exists():
                with open(env_file, "r") as f:
                    lines = f.readlines()
            
            # Remove any existing UPSTOX_ACCESS_TOKEN
            lines = [l for l in lines if not l.strip().startswith("UPSTOX_ACCESS_TOKEN=")]
            lines.append(f"UPSTOX_ACCESS_TOKEN={access_token}\n")
            
            with open(env_file, "w") as f:
                f.writelines(lines)
            
            print(f"\nSaved UPSTOX_ACCESS_TOKEN to {env_file}")
            print("You can now run `python scripts/download_upstox_1min.py` to fetch your exact 1-minute historical data!")
            
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        print(f"\n❌ HTTP Error {e.code} during token exchange:\n{err_body}")
    except Exception as e:
        print(f"\n❌ Error during token exchange: {e}")

if __name__ == "__main__":
    main()
