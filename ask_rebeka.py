import asyncio
import os
import sys

# Garante que as importações a partir de agent/ funcionem
sys.path.append(os.path.join(os.path.dirname(__file__), "agent"))

from shared.communication.chat_manager import ChatManager
from shared.core.tool_registry import registry
from agent.local.executor_local import LocalExecutor
import json

async def run_rebeka_analysis():
    print("🤖 Iniciando Rebeka Local para análise...")
    chat = ChatManager()
    tools = registry.get_tool_definitions()
    executor = LocalExecutor()
    
    prompt = "Analise e entenda a arquitetura deste sistema: C:\\Users\\Aridelson\\Documents\\sistematrader. Olhe os arquivos principais para que possamos trabalhar nele em seguida."
    
    print(f"👤 Você: {prompt}")
    print("Rebeka está pensando / usando ferramentas...\n")
    
    response = await chat.get_response(prompt, tools=tools)
    
    while response.get("tool_calls"):
        for tool_call in response["tool_calls"]:
            name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            print(f"🛠️ Rebeka está executando: {name}({args})")
            
            try:
                result = await executor.execute(name, args)
                chat.add_tool_result(tool_call.id, name, json.dumps(result))
            except Exception as e:
                print(f"❌ Erro na ferramenta {name}: {e}")
                chat.add_tool_result(tool_call.id, name, json.dumps({"status": "error", "message": str(e)}))
        
        # Pede a próxima iteração
        response = await chat.get_response(user_message=None, tools=tools)
    
    print("\n✨ Rebeka Finalizou a Análise:\n")
    print(response.get("content", ""))

if __name__ == "__main__":
    asyncio.run(run_rebeka_analysis())
