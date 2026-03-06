# agent/tests/test_live_market_research.py
import asyncio
import logging
import sys
import os

# Ajustar PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agent.local.executor_local import LocalExecutor

# Configurar logs
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

async def test_live_research():
    print("\n--- INICIANDO TESTE DE MERCADO REAL (PERPLEXITY PRO) ---\n")
    
    executor = LocalExecutor()
    
    # Query específica solicitada pelo usuário
    query = "Como está o mercado hoje? Resuma as principais movimentações em Ações, Cripto e Macro."
    
    print(f"Buscando no Perplexity: '{query}'...")
    print("Nota: Usando seu perfil logado do Chrome para garantir acesso Pro.")
    
    result = await executor.execute("perplexity_search", {"query": query})
    
    if result["status"] == "success":
        print("\n[OK] PESQUISA CONCLUIDA COM SUCESSO!")
        print(f"\n--- RESUMO DA RESPOSTA ({result['url']}) ---\n")
        print(result['full_answer'][:2000] + ("..." if len(result['full_answer']) > 2000 else ""))
        print("\n--- FIM DO RESUMO ---")
    elif result["status"] == "requires_login":
        print(f"\n[AVISO] ACAO REQUERIDA: {result['message']}")
    else:
        print(f"\n[ERRO] NO TESTE: {result.get('message')}")

if __name__ == "__main__":
    asyncio.run(test_live_research())
