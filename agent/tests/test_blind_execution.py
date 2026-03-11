# agent/tests/test_blind_execution.py
import asyncio
import logging
import sys
import os

# Ajustar PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from local.vault.master_vault import MasterVault
from intelligence.delegation_contract import DelegationContract, ContractRegistry
from core.evaluator import Evaluator
from local.executor_local import LocalExecutor

# Configurar logs para ver a segurança em ação
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

async def test_blind_flow():
    print("\n--- INICIANDO TESTE DE EXECUÇÃO CEGA (BLIND EXECUTION) ---\n")
    
    # 1. Setup do Cofre
    vault = MasterVault(storage_path="agent/tests/test_secrets.enc")
    master_pass = "senha_mestre_usuario_123"
    vault.unlock(master_pass)
    
    # Salvar uma credencial fake
    vault.save_secret("portal_advocacia", {"password": "SENHA_ULTRA_SECRETA_DO_TRIBUNAL"})
    print("1. Credencial salva no cofre local (Criptografada).")

    # 2. Setup dos Contratos de Delegação
    registry = ContractRegistry()
    contract = DelegationContract(
        role="Assistente Jurídica",
        credential_id="portal_advocacia",
        allowed_intents=["consultar_processo", "baixar_pdf"],
        forbidden_intents=["alterar_senha"]
    )
    registry.register_contract(contract)
    print("2. Contrato de Delegação assinado: 'Assistente Jurídica' pode consultar processos.")

    # 3. Simulação do Planejador (IA) propondo ação com APONTADOR
    hypothesis = {
        "reasoning": "Preciso verificar o andamento do processo X.",
        "intent": "consultar_processo",
        "action": {
            "type": "desktop_type_text",
            "details": "Fazendo login com vault://portal_advocacia no campo de senha."
        }
    }
    print(f"3. Planejador propõe ação: '{hypothesis['action']['details']}'")

    # 4. Avaliador valida o Mandato
    evaluator = Evaluator(model="mock", delegation_registry=registry)
    # Mockando a avaliação de LLM para focar na lógica de contrato
    def mock_eval_layer1(*args): return {
        "consistent": True, 
        "reasoning": "Lógica OK",
        "missed_signals": [],
        "twin_would_help": False,
        "lessons": ""
    }
    def mock_eval_layer2(*args): return {
        "aligned": True, 
        "reasoning": "Alinhado",
        "coherence_impact": 0.0,
        "clarity_impact": 0.0
    }
    def mock_eval_layer3(*args): return {"no_instrumental": True, "reasoning": "Sem gaming"}
    evaluator._evaluate_layer1 = mock_eval_layer1
    evaluator._evaluate_layer2 = mock_eval_layer2
    evaluator._evaluate_layer3 = mock_eval_layer3
    
    result = evaluator.evaluate_hypothesis(hypothesis, [], {}, {})
    print(f"4. Avaliador checou contrato: {'APROVADO' if result.approved else 'REJEITADO'}")
    if not result.approved:
        print(f"   Motivo: {result.overall_reasoning}")

    # 5. Executor realiza a Injeção Cega
    executor = LocalExecutor(vault=vault)
    # Mock do pyautogui para não digitar na tela real do usuário durante o teste
    import pyautogui
    original_write = pyautogui.write
    captured_text = []
    def mock_write(t, **kwargs): captured_text.append(t)
    pyautogui.write = mock_write
    
    exec_res = await executor.execute("desktop_type_text", {"text": "Senha: vault://portal_advocacia"})
    
    print(f"5. Executor executou: {exec_res['action']}")
    print(f"   Dado real injetado (capturado no hack do teste): {captured_text[0]}")
    
    # Restaurar pyautogui
    pyautogui.write = original_write

    # VERIFICAÇÃO FINAL
    assert "vault://" not in captured_text[0], "Erro: O apontador não foi resolvido!"
    assert "SENHA_ULTRA_SECRETA" in captured_text[0], "Erro: A senha real não foi injetada!"
    assert "INJECTED_FROM_VAULT" in exec_res['action'], "Erro: O executor vazou o segredo no retorno!"
    
    print("\n--- TESTE CONCLUÍDO COM SUCESSO! ---")
    print("A Rebeka agiu sem nunca 'ver' a senha real.")

if __name__ == "__main__":
    asyncio.run(test_blind_flow())
    # Limpeza
    if os.path.exists("agent/tests/test_secrets.enc"):
        os.remove("agent/tests/test_secrets.enc")

