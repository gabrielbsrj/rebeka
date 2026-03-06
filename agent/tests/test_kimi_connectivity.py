import os
import litellm
from dotenv import load_dotenv

load_dotenv()

def test_kimi_model():
    api_key = os.getenv("MOONSHOT_API_KEY")
    api_base = os.getenv("OPENAI_API_BASE")
    
    print(f"Testando Kimi 2.5 (kimi-k2.5) via {api_base}...")
    
    try:
        response = litellm.completion(
            model="openai/kimi-k2.5",
            messages=[{"role": "user", "content": "Olá, quem é você?"}],
            api_key=api_key,
            api_base=api_base,
            temperature=1.0
        )
        print("RESPOSTA SUCESSO:")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"FALHA NO TESTE: {str(e)}")

if __name__ == "__main__":
    test_kimi_model()
