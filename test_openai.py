import openai
import os

def test_openai_connection():
    try:
        # Initialize with API key
        openai.api_key = os.getenv('OPENAI_API_KEY')
        
        # Test API connection with a simple completion
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'Hello, testing 1-2-3!'"}],
            max_tokens=10
        )
        
        print("[SUCCESS] OpenAI connection successful!")
        print(f"Response: {response.choices[0].message.content}")
        return True
        
    except Exception as e:
        print("[ERROR] OpenAI connection failed!")
        print(f"Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing OpenAI connection...")
    print(f"Using API key ending in: ...{os.getenv('OPENAI_API_KEY')[-4:]}")
    test_openai_connection()
