import sys
import os
import logging
from datetime import datetime, timezone

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.database.causal_bank import CausalBank
from shared.evolution.observer import Observer
from shared.evolution.developer import Developer
from shared.evolution.sandbox import Sandbox
from shared.evolution.property_tester import PropertyTester
from shared.evolution.security_analyzer import SecurityAnalyzer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_full_evolution_loop():
    print("=== INICIANDO CICLO DE EVOLUÇÃO REBEKA ===")
    
    from shared.evolution.deployer import Deployer
    
    bank = CausalBank(origin="vps")
    observer = Observer(bank)
    developer = Developer()
    sandbox = Sandbox()
    tester = PropertyTester()
    analyzer = SecurityAnalyzer()
    deployer = Deployer(causal_bank=bank)

    # 1. Observer analisa performance (Simulação)
    print("\n[1] Observer analisando...")
    # Forçamos métricas simuladas para o teste
    metrics = {
        "domain": "finance",
        "win_rate": 0.45,  # Alerta! Abaixo de 50%
        "avg_reported_confidence": 0.70,
        "confidence_calibration_error": 0.25, # Alerta! Violação (max 0.10)
        "total_trades": 15
    }
    
    question = observer.question_reasoning(metrics)
    print(f"    Observer Question: {question}")

    # 2. Developer propõe melhoria
    print("\n[2] Developer propondo melhoria...")
    target_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "../shared/core/planner.py"))
    
    # Simulação de proposta (para não gastar LLM em excesso no teste, mas a classe está pronta)
    proposal = developer.propose_improvement(
        target_file=target_file,
        issue_description="A confiança está muito alta comparada ao win rate real. Precisamos de um redutor de otimismo.",
        metrics=metrics
    )
    
    if "error" in proposal:
        print(f"    Erro no Developer: {proposal['error']}")
        return

    print(f"    ID Evolução: {proposal['evolution_id']}")
    print(f"    Rationale: {proposal['rationale']}")

    # 3. Sandbox valida execução
    print("\n[3] Sandbox Validando Execução...")
    sandbox_result = sandbox.run_validation(target_file, proposal["proposed_content"])
    
    if not sandbox_result["success"]:
        print(f"    FALHA NA SANDBOX: {sandbox_result['error']}")
        return
    print(f"    SUCESSO: {sandbox_result['message']}")

    # 4. Security Analyzer projeta riscos
    print("\n[4] Security Analyzer analisando...")
    security_result = analyzer.analyze_proposed_code(target_file, proposal["proposed_content"])
    
    if security_result["decision"] == "REJECTED":
        print(f"    FALHA DE SEGURANÇA: {security_result['threats_detected']}")
        return
    print(f"    SEGURANÇA APROVADA (Risk: {security_result['risk_score']})")

    # 5. Property Tester valida Invariantes
    print("\n[5] Property Tester checando Invariantes...")
    temp_file = sandbox_result["sandbox_path"]
    property_result = tester.run_property_tests(temp_file)
    
    if not property_result["success"]:
        print(f"    VIOLAÇÃO DE INVARIANTE: {property_result['details']}")
        return
    print(f"    INVARIANTES OK.")

    # 6. REGISTRO NO BANCO (Shadow Mode)
    proposal.update({
        "sandbox_result": sandbox_result,
        "security_analysis": security_result, # Use security_result from step 4
        "invariants_passed": property_result["success"] # Use property_result from step 5
    })
    bank.insert_evolution_proposal(proposal)
    print(f"\n[6] Proposta {proposal['evolution_id']} salva no Banco de Causalidade.")

    # 7. Tentativa de Deploy (Deve ser bloqueada no Shadow Mode)
    deploy_result = deployer.deploy(
        proposal["evolution_id"], 
        proposal["target_file"], 
        proposal["proposed_content"]
    )
    
    print("\n[7] RESULTADO DO DEPLOY (Shadow Mode):")
    print(f"Status: {deploy_result['status']}")
    print(f"Motivo: {deploy_result.get('reason', 'N/A')}")
    
    if deploy_result['status'] == "PENDING_USER_APPROVAL":
        print("\n✅ SUCESSO DO TESTE: A Rebeka agiu no 'Modo Sombra'. Nenhuma modificação foi feita sem autorização.")
    else:
        print("\n❌ FALHA DO TESTE: A modificação foi aplicada ou o erro não foi capturado.")

    print("\n=== CICLO COMPLETO: EVOLUÇÃO PRONTA PARA DEPLOY ===")
    print(f"Resumo: O código modificado para {os.path.basename(target_file)} passou em todas as camadas de defesa.")

if __name__ == "__main__":
    test_full_evolution_loop()
