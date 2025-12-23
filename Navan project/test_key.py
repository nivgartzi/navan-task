import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPEN_AI_API_KEY")
if api_key:
    api_key = api_key.strip()
    print(f"Key loaded: {api_key[:15]}...{api_key[-10:]} (length: {len(api_key)})")
    print(f"Key starts with: {api_key[:7]}")
    
    # Test the key
    try:
        client = OpenAI(api_key=api_key)
        response = client.models.list()
        print("✓ API Key is VALID and working!")
    except Exception as e:
        error_str = str(e)
        print(f"\n✗ API Key rejected by OpenAI")
        print(f"Error: {error_str}")
        
        if "401" in error_str or "invalid_api_key" in error_str:
            print("\n The key is being read correctly, but OpenAI is rejecting it.")
            print("\nPossible reasons:")
            print("1. Key was revoked or expired - create a NEW key at:")
            print("   https://platform.openai.com/api-keys")
            print("2. No billing/payment method added - check:")
            print("   https://platform.openai.com/account/billing")
            print("3. Key belongs to different organization")
            print("4. Account suspended or restricted")
            print("\n Solution: Create a fresh API key and replace it in .env")
else:
    print("✗ API Key not found in .env file!")


