import os
import openai
import sys

def test_connection():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("CRITICAL: OPENAI_API_KEY is missing from environment.")
        sys.exit(1)

    client = openai.Client(api_key=api_key)

    primary_model = "gpt-5-mini"
    fallback_model = "gpt-4o-mini"

    print(f"--- Starting Isolation Test ---")
    print(f"Primary Model: {primary_model}")
    print(f"Fallback Model: {fallback_model}")

    try:
        print(f"\nAttempting connection to {primary_model}...")
        response = client.chat.completions.create(
            model=primary_model,
            messages=[{"role": "user", "content": "Hello, are you online?"}],
            max_tokens=50
        )
        print("SUCCESS: Primary model connected.")
        print(f"Response: {response.choices[0].message.content}")
        return

    except (openai.NotFoundError, openai.BadRequestError) as e:
        print(f"FAILURE: Primary model failed with error: {e}")
        print(f"--- Initiating Fail-Safe Protocol ---")
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        sys.exit(1)

    try:
        print(f"\nAttempting connection to {fallback_model}...")
        response = client.chat.completions.create(
            model=fallback_model,
            messages=[{"role": "user", "content": "Hello, are you online? (Fallback Test)"}],
            max_tokens=50
        )
        print("SUCCESS: Fallback model connected.")
        print(f"Response: {response.choices[0].message.content}")

    except Exception as e:
        print(f"CRITICAL FAILURE: Fallback model also failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_connection()
