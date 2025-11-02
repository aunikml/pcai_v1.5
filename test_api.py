# test_api.py
import os
import google.generativeai as genai
from dotenv import load_dotenv

def test_gemini_api():
    """
    A simple script to test the Gemini API key from the .env file.
    """
    print("--- Starting Gemini API Key Test ---")

    # 1. Load environment variables from .env file
    try:
        load_dotenv()
        print("[OK] .env file loaded.")
    except Exception as e:
        print(f"[FAIL] Could not load the .env file. Error: {e}")
        return

    # 2. Get the API key from the environment
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("\n[FAILURE] ❌ API Key not found!")
        print("-------------------------------------------------")
        print("Troubleshooting steps:")
        print("1. Make sure you have a file named '.env' in the same folder as this script.")
        print("2. Make sure the .env file contains a line exactly like this:")
        print('   GOOGLE_API_KEY="AIzaSy...your...key...here"')
        print("3. Make sure the variable name is exactly 'GOOGLE_API_KEY'.")
        print("-------------------------------------------------")
        return

    print("[OK] Found API key in environment variables.")

    # 3. Configure the generative AI client
    try:
        genai.configure(api_key=api_key)
        print("[OK] GenAI client configured.")
    except Exception as e:
        print(f"\n[FAILURE] ❌ Error configuring the GenAI client. Error: {e}")
        return

    # 4. Attempt to make a simple API call
    try:
        print("Attempting to connect to the Gemini API...")
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = "In one sentence in Bengali, what is the capital of Bangladesh?"
        response = model.generate_content(prompt)

        print("\n[SUCCESS] ✅ API Key is valid and connection is successful!")
        print("-------------------------------------------------")
        print(f"Prompt: {prompt}")
        print(f"Gemini Response: {response.text.strip()}")
        print("-------------------------------------------------")

    except Exception as e:
        print("\n[FAILURE] ❌ An error occurred during the API call.")
        print("-------------------------------------------------")
        print("This usually means your API key is invalid or has restrictions.")
        print("Detailed Error Message:")
        print(e)
        print("\nTroubleshooting steps:")
        print("1. Go to Google AI Studio and generate a NEW API key.")
        print("2. Copy the new key very carefully.")
        print("3. Paste it into your .env file, replacing the old one.")
        print("4. Save the .env file and run this test again.")
        print("-------------------------------------------------")

if __name__ == "__main__":
    test_gemini_api()