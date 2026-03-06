import logging
import asyncio
from typing import Dict, Any, Optional
from shared.database.causal_bank import CausalBank
from shared.orchestration.idea_decomposer import IdeaDecomposer
from shared.orchestration.agent_router import AgentRouter
from shared.orchestration.execution_tracker import ExecutionTracker
from shared.communication.chat_manager import ChatManager

logger = logging.getLogger(__name__)

class OrchestrationEngine:
    """
    O Coração da Rebeka v5.0. 
    Coordena o ciclo de vida de uma intenção do usuário:
    1. Entende e Decompõe a ideia
    2. Avalia quais agentes/ferramentas são necessários
    3. Delega e acompanha

    INTENÇÃO: O humano é o diretor da orquestra, a Rebeka é o maestro.
    """

    def __init__(self, causal_bank: CausalBank, chat_manager: Optional[ChatManager] = None):
        self.db = causal_bank
        self.decomposer = IdeaDecomposer(chat_manager)
        self.router = AgentRouter()
        self.tracker = ExecutionTracker(self.db)
        logger.info("Orchestration Engine (v5.0) Inicializada.")

    async def process_user_idea(self, raw_idea: str) -> Dict[str, Any]:
        """
        Recebe uma ideia bruta do usuário, decompõe em plano estruturado,
        salva no banco e retorna o preview para aprovação prévia.
        """
        logger.info(f"== Iniciando ciclo de orquestração para nova ideia ==")
        
        # O ideal seria puxar user profile real do banco, mockado por enquanto:
        user_profile = "Usuário prefere código pragmático. Foco em estabilidade."
        
        try:
            # 1. Decomposição
            logger.info("Decompondo ideia no GPT...")
            plan_json = await self.decomposer.decompose(raw_idea, user_profile)
            
            # 2. Roteamento preemptivo
            for comp in plan_json.get("componentes", []):
                suggested_router = self.router.route_task(comp)
                comp["executor_alocado"] = suggested_router
                
            # 3. Registro no Tracker / Banco de Dados
            plan_data = {
                "original_idea": raw_idea,
                "central_objective": plan_json.get("objetivo_central", ""),
                "final_deliverable": plan_json.get("entregavel_final", ""),
                "components": plan_json.get("componentes", []),
                "sequence": plan_json.get("sequencia_sugerida", []),
                "status": "draft"
            }
            plan_id = self.tracker.initialize_plan(plan_data)
            logger.info(f"Plano de orquestração gerado e salvo. ID: {plan_id}")
            
            return {
                "plan_id": plan_id,
                "central_objective": plan_data["central_objective"],
                "components": plan_data["components"],
                "uncertainties": plan_json.get("incertezas", [])
            }
            
        except Exception as e:
            logger.error(f"Falha na orquestração inicial: {e}")
            raise

    async def approve_and_execute_plan(self, plan_id: str) -> None:
        """
        No momento que o humano diz "Vai em frente", esse método dispara 
        os agentes alocados (Cursor, Claude, N8N, etc).
        (Stub: execução assíncrona real de agentes será implementada nas sub-engines).
        """
        logger.info(f"Iniciando execução real do plano {plan_id}")
        self.tracker.start_execution(plan_id)
        # TODO: Loop assíncrono sobre componentes, aguardando dependências
        # Despachando via socket (para cursor local) ou API (Claude)
