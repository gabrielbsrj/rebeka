# agent/tests/direct_moonshot_test.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_direct():
    api_key = os.getenv("MOONSHOT_API_KEY")
    url = "https://api.moonshot.cn/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "moonshot-v1-8k",
        "messages": [
            {"role": "user", "content": "Olá, isso é um teste."}
        ],
        "temperature": 0.3
    }
    
    print(f"Enviando POST para {url}...")
    print(f"Header Authorization: Bearer {api_key[:5]}...{api_key[-5:]}")
    
    response = requests.post(url, headers=headers, json=data)
    
    print(f"STATUS CODE: {response.status_code}")
    print(f"RESPONSE: {response.text}")

if __name__ == "__main__":
    test_direct()
