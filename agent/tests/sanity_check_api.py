# agent/tests/sanity_check_api.py
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_kimi_25():
    print("Iniciando teste de conectividade com Kimi K2.5 (Moonshot AI)...")
    api_key = os.getenv("MOONSHOT_API_KEY")
    url = "https://api.moonshot.ai/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "kimi-k2.5",
        "messages": [
            {"role": "user", "content": "Olá, responda com OK se estiver funcionando."}
        ],
        "temperature": 1.0
    }
    
    print(f"Enviando POST para {url}...")
    try:
        response = requests.post(url, headers=headers, json=data)
        print(f"STATUS CODE: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print("RESPOSTA DO MODELO:", result["choices"][0]["message"]["content"])
            print("Teste concluído com SUCESSO! ✅")
        else:
            print(f"ERRO: {response.text}")
    except Exception as e:
        print(f"FALHA TÉCNICA: {str(e)}")

if __name__ == "__main__":
    test_kimi_25()
