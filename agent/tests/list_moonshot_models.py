# agent/tests/list_moonshot_models.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def list_models():
    api_key = os.getenv("MOONSHOT_API_KEY")
    url = "https://api.moonshot.cn/v1/models"
    
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    print(f"Listando modelos de {url}...")
    try:
        response = requests.get(url, headers=headers)
        print(f"STATUS CODE: {response.status_code}")
        print(f"RESPONSE: {response.text}")
    except Exception as e:
        print(f"ERRO: {str(e)}")

if __name__ == "__main__":
    list_models()
