# agent/tests/test_perplexity.py
import asyncio
import logging
import sys
import os

# Ajustar PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.local.executor_local import LocalExecutor

# Configurar logs
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

async def test_perplexity():
    print("\n--- TESTANDO INTEGRAÇÃO PERPLEXITY PRO ---\n")
    print("IMPORTANTE: Se o Chrome estiver aberto, a Rebeka pode falhar ao carregar o perfil.")
    
    executor = LocalExecutor()
    
    # Pergunta de teste para validar o modo Pro/Deep Research
    query = "Quais as 3 principais tendências macroeconômicas para o Brasil em 2026 segundo analistas recentes?"
    
    print(f"1. Iniciando pesquisa: '{query}'")
    result = await executor.execute("perplexity_search", {"query": query})
    
    if result["status"] == "success":
        print("\n   Sucesso! Resposta capturada:")
        print(f"   URL: {result['url']}")
        print(f"   Preview: {result['answer_preview']}")
        print("\n--- TESTE CONCLUÍDO COM SUCESSO ---")
    else:
        print(f"\n   Falha no teste: {result.get('message')}")
        print("\n--- TESTE FALHOU ---")

if __name__ == "__main__":
    asyncio.run(test_perplexity())
