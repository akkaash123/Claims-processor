import os
import urllib.request
import json
from dotenv import load_dotenv

# Load the API key from your .env file
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("ERROR: No GOOGLE_API_KEY found in .env file.")
    exit(1)

print("Authenticating with Google API...")

# The exact endpoint the error message told us to check
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
        
        print("\n--- AVAILABLE MODELS FOR YOUR KEY ---")
        for model in data.get("models", []):
            # We only care about models that support text/content generation
            if "generateContent" in model.get("supportedGenerationMethods", []):
                print(f"- {model['name']}")
                
        print("\n-------------------------------------")
        
except urllib.error.HTTPError as e:
    error_body = e.read().decode()
    print(f"\nAPI Error {e.code}: {e.reason}")
    print(f"Details: {error_body}")
except Exception as e:
    print(f"\nConnection Error: {str(e)}")