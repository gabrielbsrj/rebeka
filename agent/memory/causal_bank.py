# shared/database/causal_bank.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-24
# CHANGELOG: v2 — Banco único PostgreSQL para ambos os gêmeos (removido dual SQLite/PG)
#
# AMBOS OS GÊMEOS: Usam o mesmo banco PostgreSQL via DATABASE_URL
# CAMPO origin: Identifica qual gêmeo escreveu cada registro

"""
Causal Bank — Interface única para o Banco de Causalidade.

INTENÇÃO: NENHUM módulo acessa o banco diretamente. Toda operação
passa por esta classe. Isso garante que:
1. Toda inserção calcula hash na Sparse Merkle Tree
2. Toda inserção atualiza a Merkle Root
3. Toda inserção registra timestamp e origem
4. UPDATE e DELETE não existem (append-only absoluto)

INVARIANTE: Nenhuma operação neste módulo modifica registros existentes.
INVARIANTE: Toda inserção retorna o ID canônico e atualiza a SMT.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session

from memory.models import (
    Base,
    Signal,
    CausalPattern,
    CorrelationCandidate,
    DeprecatedPattern,
    SecondOrderPattern,
    ThirdOrderPattern,
    UserDecision,
    UserCoherenceLog,
    UserRegretSignal,
    UserClarityDelta,
    IntentModel,
    Hypothesis,
    Execution,
    Evaluation,
    EnvironmentError as EnvError,
    CodeVersion,
    EvolutionLog,
    TranscendenceLog,
    MerkleTreeRecord,
    SynthesisLog,
    PrivacyAuditLog,
    MonitorLifecycle,
    GrowthTarget,
    GrowthProgressLog,
    GrowthRedefinition,
    ConversationSignal,
    BehavioralPattern,
    UserProfileDeclared,
    UserProfileObserved,
    FrictionLog,
    UserFeedback,
    UncertaintyAnnotation,
    InteractionQuality,
    OrchestrationPlan,
    AgentRegistry,
    TaskExecution,
    DelegationLog,
    create_all_tables,
)
from memory.sparse_merkle_tree import SparseMerkleTree
from memory.pattern_pruner import PatternPruner
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CausalBank:
    """
    Interface append-only para o Banco de Causalidade.

    INTENÇÃO: Esta é a ÚNICA porta de entrada para o banco de dados.
    Toda operação de escrita:
    1. Cria o registro com UUID
    2. Calcula o hash da folha na Sparse Merkle Tree
    3. Atualiza a Merkle Root
    4. Persiste registro + novo root
    5. Retorna o ID canônico

    Toda operação de leitura passa por aqui para garantir auditabilidade
    e possibilitar cache + otimizações futuras sem mudar a interface.

    NOTA v2: Ambos os gêmeos (VPS e Local) usam o mesmo banco PostgreSQL.
    O campo `origin` em cada registro identifica qual gêmeo escreveu.
    """

    def __init__(self, database_url: Optional[str] = None, origin: str = "vps"):
        """
        Inicializa o Banco de Causalidade.

        Args:
            database_url: URL do banco (PostgreSQL). Se None, busca no ambiente.
            origin: "vps" ou "local" — identifica qual gêmeo está escrevendo.
                    Ambos usam o mesmo banco. O campo origin separa os registros.
        """
        import os
        from dotenv import load_dotenv
        load_dotenv()

        if not database_url:
            database_url = os.getenv("DATABASE_URL")
            
        if not database_url:
            # Fallback para desenvolvimento/testes — em produção usar PostgreSQL
            database_url = "sqlite:///causal_bank_dev.db"
            logger.warning("DATABASE_URL não encontrada. Usando SQLite para desenvolvimento. Em produção, configure PostgreSQL.")

        self._engine = create_engine(database_url, echo=False)
        self._SessionFactory = sessionmaker(bind=self._engine)
        self._origin = origin
        self._smt = SparseMerkleTree()

        # Criar tabelas se não existirem
        create_all_tables(self._engine)
        
        # Inicializa o pruner on-read
        self._pruner = PatternPruner(decay_rate=0.01, min_weight=0.2)

        logger.info(
            "Banco de Causalidade inicializado",
            extra={"origin": origin, "database_url": database_url.split("@")[-1]},
        )

    @property
    def merkle_root(self) -> str:
        """Merkle Root atual da Sparse Merkle Tree."""
        return self._smt.root

    @property
    def leaf_count(self) -> int:
        """Número de folhas na SMT."""
        return self._smt.leaf_count

    # =========================================================================
    # INSERÇÕES — Padrões do Mundo
    # =========================================================================

    def insert_signal(self, signal_data: Dict[str, Any]) -> str:
        """
        Insere um sinal coletado por um monitor.

        INTENÇÃO: Sinais são dados brutos do mundo. Nunca interpretação.

        INVARIANTE: Toda inserção atualiza a SMT e registra a nova Merkle Root.

        Returns:
            ID canônico do sinal inserido.
        """
        with self._SessionFactory() as session:
            signal_id = str(uuid.uuid4())
            signal = Signal(
                id=signal_id,
                origin=self._origin,
                domain=signal_data["domain"],
                source=signal_data["source"],
                title=signal_data["title"],
                content=signal_data.get("content"),
                raw_data=signal_data.get("raw_data"),
                relevance_score=signal_data.get("relevance_score", 0.0),
                merkle_leaf_hash="",  # Calculado abaixo
                metadata_=signal_data.get("metadata"),
            )

            # SMT: calcular hash e inserir folha
            leaf = self._smt.insert_leaf(
                key=signal.id,
                data=signal_data,
                table="signals",
            )
            signal.merkle_leaf_hash = leaf.leaf_hash

            # Registrar nova Merkle Root
            merkle_record = MerkleTreeRecord(
                merkle_root=self._smt.root,
                leaf_count=self._smt.leaf_count,
                operation_type="insert",
                affected_table="signals",
                affected_record_id=signal.id,
            )

            session.add(signal)
            session.add(merkle_record)
            session.commit()

            logger.info(
                "Signal inserido no banco",
                extra={
                    "signal_id": signal.id,
                    "domain": signal.domain,
                    "relevance_score": signal.relevance_score,
                    "origin": self._origin,
                    "merkle_root": self._smt.root,
                },
            )

            return signal.id

    def insert_causal_pattern(self, pattern_data: Dict[str, Any]) -> str:
        """
        Insere um padrão validado causalmente.

        INTENÇÃO: Apenas padrões que passaram pelo causal_validator.py
        devem ser inseridos aqui. Correlações puras vão para
        insert_correlation_candidate().

        INVARIANTE: Todo padrão aqui tem causal_mechanism preenchido.
        """
        if "causal_mechanism" not in pattern_data or not pattern_data["causal_mechanism"]:
            raise ValueError(
                "Padrão causal DEVE ter causal_mechanism. "
                "Use insert_correlation_candidate() para correlações não validadas."
            )

        with self._SessionFactory() as session:
            pattern_id = str(uuid.uuid4())
            pattern = CausalPattern(
                id=pattern_id,
                domain=pattern_data["domain"],
                cause_description=pattern_data["cause_description"],
                effect_description=pattern_data["effect_description"],
                causal_mechanism=pattern_data["causal_mechanism"],
                confidence=pattern_data["confidence"],
                confirmation_count=pattern_data.get("confirmation_count", 1),
                out_of_sample_validated=pattern_data.get("out_of_sample_validated", False),
                signal_ids=pattern_data.get("signal_ids"),
                merkle_leaf_hash="",
                metadata_=pattern_data.get("metadata"),
            )

            leaf = self._smt.insert_leaf(
                key=pattern.id,
                data=pattern_data,
                table="causal_patterns",
            )
            pattern.merkle_leaf_hash = leaf.leaf_hash

            merkle_record = MerkleTreeRecord(
                merkle_root=self._smt.root,
                leaf_count=self._smt.leaf_count,
                operation_type="insert",
                affected_table="causal_patterns",
                affected_record_id=pattern.id,
            )

            session.add(pattern)
            session.add(merkle_record)
            session.commit()

            logger.info(
                "Padrão causal inserido",
                extra={
                    "pattern_id": pattern.id,
                    "domain": pattern.domain,
                    "confidence": pattern.confidence,
                    "merkle_root": self._smt.root,
                },
            )

            return pattern.id

    def insert_correlation_candidate(self, candidate_data: Dict[str, Any]) -> str:
        """
        Insere uma correlação ainda não validada causalmente.

        INTENÇÃO: Correlação não é causalidade. Padrões aqui têm peso
        menor no raciocínio até confirmação via causal_validator.
        """
        with self._SessionFactory() as session:
            candidate_id = str(uuid.uuid4())
            candidate = CorrelationCandidate(
                id=candidate_id,
                domain=candidate_data["domain"],
                variable_a=candidate_data["variable_a"],
                variable_b=candidate_data["variable_b"],
                correlation_strength=candidate_data["correlation_strength"],
                observation_count=candidate_data.get("observation_count", 1),
                merkle_leaf_hash="",
                metadata_=candidate_data.get("metadata"),
            )

            leaf = self._smt.insert_leaf(
                key=candidate.id,
                data=candidate_data,
                table="correlation_candidates",
            )
            candidate.merkle_leaf_hash = leaf.leaf_hash

            merkle_record = MerkleTreeRecord(
                merkle_root=self._smt.root,
                leaf_count=self._smt.leaf_count,
                operation_type="insert",
                affected_table="correlation_candidates",
                affected_record_id=candidate.id,
            )

            session.add(candidate)
            session.add(merkle_record)
            session.commit()

            return candidate.id

    # =========================================================================
    # INSERÇÕES — Padrões do Usuário
    # =========================================================================

    def insert_user_decision(self, decision_data: Dict[str, Any]) -> str:
        """
        Registra uma decisão do usuário com contexto completo.

        INTENÇÃO: Cada decisão é dado sobre valores reais do usuário.
        Com tempo suficiente, constrói o modelo de valores.
        """
        with self._SessionFactory() as session:
            decision_id = str(uuid.uuid4())
            decision = UserDecision(
                id=decision_id,
                decision_type=decision_data["decision_type"],
                context=decision_data["context"],
                decision_data=decision_data["decision_data"],
                reasoning_observed=decision_data.get("reasoning_observed"),
                emotional_context=decision_data.get("emotional_context"),
                merkle_leaf_hash="",
            )

            leaf = self._smt.insert_leaf(
                key=decision.id,
                data=decision_data,
                table="user_decisions",
            )
            decision.merkle_leaf_hash = leaf.leaf_hash

            merkle_record = MerkleTreeRecord(
                merkle_root=self._smt.root,
                leaf_count=self._smt.leaf_count,
                operation_type="insert",
                affected_table="user_decisions",
                affected_record_id=decision.id,
            )

            session.add(decision)
            session.add(merkle_record)
            session.commit()

            return decision.id

    # =========================================================================
    # INSERÇÕES — Sistema
    # =========================================================================

    def insert_hypothesis(self, hypothesis_data: Dict[str, Any]) -> str:
        """
        Registra uma hipótese do Planejador.

        INTENÇÃO: Toda hipótese inclui incertezas reconhecidas.
        O campo uncertainty_acknowledged é obrigatório.
        """
        if "uncertainty_acknowledged" not in hypothesis_data:
            raise ValueError(
                "Hipótese DEVE incluir uncertainty_acknowledged. "
                "O Planejador nunca omite o que pode estar errado."
            )

        with self._SessionFactory() as session:
            hypothesis_id = str(uuid.uuid4())
            hypothesis = Hypothesis(
                id=hypothesis_id,
                origin=hypothesis_data.get("origin", self._origin),
                reasoning=hypothesis_data["reasoning"],
                signals_used=hypothesis_data["signals_used"],
                predicted_movement=hypothesis_data["predicted_movement"],
                confidence_calibrated=hypothesis_data["confidence_calibrated"],
                uncertainty_acknowledged=hypothesis_data["uncertainty_acknowledged"],
                action=hypothesis_data["action"],
                merkle_leaf_hash="",
            )

            leaf = self._smt.insert_leaf(
                key=hypothesis.id,
                data=hypothesis_data,
                table="hypotheses",
            )
            hypothesis.merkle_leaf_hash = leaf.leaf_hash

            merkle_record = MerkleTreeRecord(
                merkle_root=self._smt.root,
                leaf_count=self._smt.leaf_count,
                operation_type="insert",
                affected_table="hypotheses",
                affected_record_id=hypothesis.id,
            )

            session.add(hypothesis)
            session.add(merkle_record)
            session.commit()

            return hypothesis.id

    def insert_execution(self, execution_data: Dict[str, Any]) -> str:
        """
        Registra uma execução (paper ou real).

        INVARIANTE: Se execution_type == "real", amount <= max configurado.
        """
        with self._SessionFactory() as session:
            execution_id = str(uuid.uuid4())
            execution = Execution(
                id=execution_id,
                hypothesis_id=execution_data["hypothesis_id"],
                execution_type=execution_data["execution_type"],
                market=execution_data["market"],
                asset=execution_data["asset"],
                direction=execution_data["direction"],
                amount=execution_data["amount"],
                entry_price=execution_data.get("entry_price"),
                merkle_leaf_hash="",
            )

            leaf = self._smt.insert_leaf(
                key=execution.id,
                data=execution_data,
                table="executions",
            )
            execution.merkle_leaf_hash = leaf.leaf_hash

            merkle_record = MerkleTreeRecord(
                merkle_root=self._smt.root,
                leaf_count=self._smt.leaf_count,
                operation_type="insert",
                affected_table="executions",
                affected_record_id=execution.id,
            )

            session.add(execution)
            session.add(merkle_record)
            session.commit()

            return execution.id

    def insert_evaluation(self, evaluation_data: Dict[str, Any]) -> str:
        """Registra uma avaliação do Avaliador."""
        with self._SessionFactory() as session:
            evaluation_id = str(uuid.uuid4())
            evaluation = Evaluation(
                id=evaluation_id,
                hypothesis_id=evaluation_data["hypothesis_id"],
                execution_id=evaluation_data.get("execution_id"),
                hypothesis_correct=evaluation_data.get("hypothesis_correct"),
                reasoning_analysis=evaluation_data["reasoning_analysis"],
                missed_signals=evaluation_data.get("missed_signals"),
                twin_perspective_would_help=evaluation_data.get("twin_perspective_would_help"),
                clarity_impact=evaluation_data.get("clarity_impact"),
                coherence_impact=evaluation_data.get("coherence_impact"),
                lessons_learned=evaluation_data["lessons_learned"],
                merkle_leaf_hash="",
            )

            leaf = self._smt.insert_leaf(
                key=evaluation.id,
                data=evaluation_data,
                table="evaluations",
            )
            evaluation.merkle_leaf_hash = leaf.leaf_hash

            merkle_record = MerkleTreeRecord(
                merkle_root=self._smt.root,
                leaf_count=self._smt.leaf_count,
                operation_type="insert",
                affected_table="evaluations",
                affected_record_id=evaluation.id,
            )

            session.add(evaluation)
            session.add(merkle_record)
            session.commit()

            return evaluation.id

    def insert_environment_error(self, error_data: Dict[str, Any]) -> str:
        """Registra uma falha de ambiente."""
        with self._SessionFactory() as session:
            error_id = str(uuid.uuid4())
            error = EnvError(
                id=error_id,
                error_type=error_data["error_type"],
                description=error_data["description"],
                context=error_data.get("context"),
                merkle_leaf_hash="",
            )

            leaf = self._smt.insert_leaf(
                key=error.id,
                data=error_data,
                table="environment_errors",
            )
            error.merkle_leaf_hash = leaf.leaf_hash

            merkle_record = MerkleTreeRecord(
                merkle_root=self._smt.root,
                leaf_count=self._smt.leaf_count,
                operation_type="insert",
                affected_table="environment_errors",
                affected_record_id=error.id,
            )

            session.add(error)
            session.add(merkle_record)
            session.commit()

            return error.id

    def insert_privacy_audit_log(self, audit_data: Dict[str, Any]) -> str:
        """Registra log de auditoria de privacidade (Local Only)."""
        with self._SessionFactory() as session:
            log_id = str(uuid.uuid4())
            log = PrivacyAuditLog(
                id=log_id,
                data_type=audit_data["data_type"],
                destination=audit_data.get("destination", "vps"),
                abstraction_sent=audit_data["abstraction_sent"],
                approved_by_filter=audit_data.get("approved_by_filter", True),
                transmission_confirmed=audit_data.get("transmission_confirmed", False),
                merkle_leaf_hash="",
            )

            leaf = self._smt.insert_leaf(
                key=log.id,
                data=audit_data,
                table="privacy_audit_log",
            )
            log.merkle_leaf_hash = leaf.leaf_hash

            merkle_record = MerkleTreeRecord(
                merkle_root=self._smt.root,
                leaf_count=self._smt.leaf_count,
                operation_type="insert",
                affected_table="privacy_audit_log",
                affected_record_id=log.id,
            )

            session.add(log)
            session.add(merkle_record)
            session.commit()

            return log.id

    def insert_monitor_lifecycle(self, lifecycle_data: Dict[str, Any]) -> str:
        """Registra ciclo de vida de um monitor."""
        with self._SessionFactory() as session:
            ml_id = str(uuid.uuid4())
            ml = MonitorLifecycle(
                id=ml_id,
                monitor_name=lifecycle_data["monitor_name"],
                domain=lifecycle_data["domain"],
                action=lifecycle_data["action"],
                reason=lifecycle_data["reason"],
                triggered_by=lifecycle_data["triggered_by"],
                merkle_leaf_hash="",
            )

            leaf = self._smt.insert_leaf(
                key=ml.id,
                data=lifecycle_data,
                table="monitor_lifecycle",
            )
            ml.merkle_leaf_hash = leaf.leaf_hash

            merkle_record = MerkleTreeRecord(
                merkle_root=self._smt.root,
                leaf_count=self._smt.leaf_count,
                operation_type="insert",
                affected_table="monitor_lifecycle",
                affected_record_id=ml.id,
            )

            session.add(ml)
            session.add(merkle_record)
            session.commit()

            return ml.id

    # =========================================================================
    # LEITURA — Queries (nunca modificam dados)
    # =========================================================================

    def insert_evolution_proposal(self, proposal_data: Dict[str, Any]) -> str:
        """
        Registra uma proposta de evolução do Developer.
        """
        with self._SessionFactory() as session:
            proposal_id = proposal_data.get("evolution_id", str(uuid.uuid4()))
            proposal = EvolutionLog(
                id=proposal_id,
                proposal=proposal_data["proposed_content"],
                reasoning=proposal_data["rationale"],
                sandbox_result=proposal_data.get("sandbox_result"),
                twin_evaluation=proposal_data.get("security_analysis"),
                invariants_passed=proposal_data.get("invariants_passed", False),
                status="proposed",
                merkle_leaf_hash="",
            )

            leaf = self._smt.insert_leaf(
                key=proposal.id,
                data=proposal_data,
                table="evolution_log",
            )
            proposal.merkle_leaf_hash = leaf.leaf_hash

            merkle_record = MerkleTreeRecord(
                merkle_root=self._smt.root,
                leaf_count=self._smt.leaf_count,
                operation_type="insert",
                affected_table="evolution_log",
                affected_record_id=proposal.id,
            )

            session.add(proposal)
            session.add(merkle_record)
            session.commit()

            return proposal.id

    def insert_system_event(self, event_data: Dict[str, Any]) -> str:
        """Registra um evento genérico do sistema."""
        return self.insert_environment_error({
            "error_type": event_data["event_type"],
            "description": f"EVENT: {event_data.get('description', '')}",
            "context": event_data
        })

    # =========================================================================
    # CRESCIMENTO E FRICÇÃO — Novos métodos da Fase 2
    # =========================================================================

    def insert_growth_target(self, target_data: Dict[str, Any]) -> str:
        """Insere um novo horizonte de crescimento."""
        record_id = str(uuid.uuid4())
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "domain": target_data.get("domain"),
                "current_state": target_data.get("current_state_declared"),
                "desired_state": target_data.get("desired_future_state"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "growth_targets")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            target = GrowthTarget(
                id=record_id,
                domain=target_data.get("domain"),
                current_state_declared=target_data.get("current_state_declared"),
                desired_future_state=target_data.get("desired_future_state"),
                progress_metrics=target_data.get("progress_metrics", {}),
                target_deadline=target_data.get("target_deadline"),
                active=target_data.get("active", True),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(target)
            session.commit()
            logger.info(f"Growth target inserido: {record_id}")
            return record_id

    def get_active_growth_targets(self, domain: Optional[str] = None) -> List[Dict]:
        """Busca horizontes de crescimento ativos."""
        with self._SessionFactory() as session:
            query = session.query(GrowthTarget).filter(GrowthTarget.active == True)
            if domain:
                query = query.filter(GrowthTarget.domain == domain)
            
            targets = query.order_by(GrowthTarget.created_at.desc()).all()
            return [
                {
                    "id": t.id,
                    "domain": t.domain,
                    "current_state": t.current_state_declared,
                    "desired_state": t.desired_future_state,
                    "metrics": t.progress_metrics,
                    "deadline": t.target_deadline.isoformat() if t.target_deadline else None,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                }
                for t in targets
            ]

    def insert_growth_progress(self, progress_data: Dict[str, Any]) -> str:
        """Insere snapshot semanal de progresso."""
        record_id = str(uuid.uuid4())
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "target_id": progress_data.get("target_id"),
                "week": progress_data.get("week_number"),
                "distance": progress_data.get("distance_from_goal"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "growth_progress_log")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            progress = GrowthProgressLog(
                id=record_id,
                target_id=progress_data.get("target_id"),
                week_number=progress_data.get("week_number"),
                metrics_snapshot=progress_data.get("metrics_snapshot", {}),
                distance_from_goal=progress_data.get("distance_from_goal", 1.0),
                trend=progress_data.get("trend", "stagnant"),
                system_notes=progress_data.get("system_notes"),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(progress)
            session.commit()
            return record_id

    def get_growth_progress_history(self, target_id: str) -> List[Dict]:
        """Busca histórico de progresso de um alvo."""
        with self._SessionFactory() as session:
            progress = (
                session.query(GrowthProgressLog)
                .filter(GrowthProgressLog.target_id == target_id)
                .order_by(GrowthProgressLog.week_number.desc())
                .all()
            )
            return [
                {
                    "week": p.week_number,
                    "metrics": p.metrics_snapshot,
                    "distance": p.distance_from_goal,
                    "trend": p.trend,
                    "notes": p.system_notes,
                }
                for p in progress
            ]

    def insert_growth_redefinition(self, redefinition_data: Dict[str, Any]) -> str:
        """Registra quando usuário redefine um horizonte."""
        record_id = str(uuid.uuid4())
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "previous": redefinition_data.get("previous_target_id"),
                "new": redefinition_data.get("new_target_id"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "growth_redefinitions")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            redefinition = GrowthRedefinition(
                id=record_id,
                previous_target_id=redefinition_data.get("previous_target_id"),
                new_target_id=redefinition_data.get("new_target_id"),
                reason_provided=redefinition_data.get("reason_provided"),
                context_detected=redefinition_data.get("context_detected"),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(redefinition)
            session.commit()
            return record_id

    def insert_conversation_signal(self, signal_data: Dict[str, Any]) -> str:
        """Insere sinais extraídos de conversas."""
        record_id = str(uuid.uuid4())
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "behavioral": signal_data.get("behavioral_patterns", {}),
                "emotional": signal_data.get("emotional_state_inferred"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "conversation_signals")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            signal = ConversationSignal(
                id=record_id,
                conversation_id=signal_data.get("conversation_id"),
                behavioral_patterns=signal_data.get("behavioral_patterns"),
                emotional_state_inferred=signal_data.get("emotional_state_inferred"),
                emotional_confidence=signal_data.get("emotional_confidence"),
                emotional_decay_date=signal_data.get("emotional_decay_date"),
                external_events=signal_data.get("external_events"),
                self_attribution=signal_data.get("self_attribution"),
                values_revealed=signal_data.get("values_revealed"),
                friction_potential=signal_data.get("friction_potential"),
                growth_horizon_implicit=signal_data.get("growth_horizon_implicit"),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(signal)
            session.commit()
            return record_id

    def get_recent_conversation_signals(self, days: int = 7, limit: int = 50) -> List[Dict]:
        """Busca sinais de conversas recentes."""
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        with self._SessionFactory() as session:
            signals = (
                session.query(ConversationSignal)
                .filter(ConversationSignal.created_at >= cutoff)
                .order_by(ConversationSignal.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": s.id,
                    "behavioral_patterns": s.behavioral_patterns,
                    "emotional_state_inferred": s.emotional_state_inferred,
                    "values_revealed": s.values_revealed,
                    "external_events": s.external_events,
                    "friction_potential": s.friction_potential,
                    # aliases legadas
                    "behavioral": s.behavioral_patterns,
                    "emotional": s.emotional_state_inferred,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in signals
            ]

    def insert_behavioral_pattern(self, pattern_data: Dict[str, Any]) -> str:
        """Insere ou atualiza padrão comportamental."""
        record_id = str(uuid.uuid4())
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "domain": pattern_data.get("domain"),
                "type": pattern_data.get("pattern_type"),
                "confidence": pattern_data.get("confidence"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "behavioral_patterns")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            pattern = BehavioralPattern(
                id=record_id,
                domain=pattern_data.get("domain"),
                pattern_type=pattern_data.get("pattern_type"),
                description=pattern_data.get("description"),
                first_detected_at=pattern_data.get("first_detected_at", datetime.now(timezone.utc)),
                last_detected_at=datetime.now(timezone.utc),
                confirmation_count=pattern_data.get("confirmation_count", 1),
                confidence=pattern_data.get("confidence", 0.5),
                potentially_limiting=pattern_data.get("potentially_limiting", False),
                evidence=pattern_data.get("evidence", []),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(pattern)
            session.commit()
            return record_id

    def append_behavioral_evidence(self, pattern_id: str, new_evidence: Dict) -> str:
        """
        Registra nova evidência como registro append-only.
        
        INTENÇÃO: Em vez de mutar o padrão existente, cria um novo registro
        com confidence incrementada e referência ao padrão anterior.
        Preserva o histórico completo de evolução do padrão.
        """
        with self._SessionFactory() as session:
            original = session.query(BehavioralPattern).filter(
                BehavioralPattern.id == pattern_id
            ).first()
            
            if not original:
                raise ValueError(f"Padrão {pattern_id} não encontrado")
            
            new_confidence = min(1.0, original.confidence + 0.05)
            new_count = original.confirmation_count + 1
            updated_evidence = (original.evidence or []) + [new_evidence]
            
            record_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc)
            
            leaf = self._smt.insert_leaf(
                key=record_id,
                data={
                    "pattern_type": original.pattern_type,
                    "parent_pattern_id": pattern_id,
                    "confirmation_count": new_count,
                    "confidence": new_confidence,
                },
                table="behavioral_patterns",
            )
            leaf_hash = leaf.leaf_hash
            
            new_pattern = BehavioralPattern(
                id=record_id,
                created_at=now,
                domain=original.domain,
                pattern_type=original.pattern_type,
                description=original.description,
                first_detected_at=original.first_detected_at,
                last_detected_at=now,
                confirmation_count=new_count,
                confidence=new_confidence,
                potentially_limiting=original.potentially_limiting,
                evidence=updated_evidence,
                parent_pattern_id=pattern_id,
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(new_pattern)
            session.commit()
            
            logger.info(
                f"Evidência adicionada (append-only): {record_id}, "
                f"pai: {pattern_id}, confiança: {new_confidence}"
            )
            return record_id

    # Alias para compatibilidade — redireciona para append-only
    def update_behavioral_pattern(self, pattern_id: str, new_evidence: Dict) -> str:
        """DEPRECATED: Use append_behavioral_evidence(). Mantido para compatibilidade."""
        logger.warning("update_behavioral_pattern() é deprecated. Use append_behavioral_evidence().")
        return self.append_behavioral_evidence(pattern_id, new_evidence)

    def get_behavioral_patterns(self, domain: Optional[str] = None, min_confidence: float = 0.5) -> List[Dict]:
        """Busca padrões comportamentais."""
        with self._SessionFactory() as session:
            query = session.query(BehavioralPattern).filter(
                BehavioralPattern.confidence >= min_confidence
            )
            if domain:
                query = query.filter(BehavioralPattern.domain == domain)
            
            patterns = query.order_by(BehavioralPattern.confidence.desc()).all()
            return [
                {
                    "id": p.id,
                    "domain": p.domain,
                    "type": p.pattern_type,
                    "description": p.description,
                    "confidence": p.confidence,
                    "confirmation_count": p.confirmation_count,
                    "potentially_limiting": p.potentially_limiting,
                    "last_detected": p.last_detected_at.isoformat() if p.last_detected_at else None,
                }
                for p in patterns
            ]

    def insert_user_profile_declared(self, profile_data: Dict[str, Any]) -> str:
        """Insere perfil declarado pelo usuário."""
        record_id = str(uuid.uuid4())
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "risk": profile_data.get("risk_profile"),
                "autonomy": profile_data.get("autonomy_preference"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "user_profile_declared")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            profile = UserProfileDeclared(
                id=record_id,
                risk_profile=profile_data.get("risk_profile"),
                autonomy_preference=profile_data.get("autonomy_preference"),
                horizon_temporal=profile_data.get("horizon_temporal"),
                biggest_pain_point=profile_data.get("biggest_pain_point"),
                regret_definition=profile_data.get("regret_definition"),
                relationship_with_risk=profile_data.get("relationship_with_risk"),
                additional_values=profile_data.get("additional_values"),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(profile)
            session.commit()
            return record_id

    def get_latest_declared_profile(self) -> Optional[Dict]:
        """Busca perfil declarado mais recente."""
        with self._SessionFactory() as session:
            profile = (
                session.query(UserProfileDeclared)
                .order_by(UserProfileDeclared.created_at.desc())
                .first()
            )
            if not profile:
                return None
            return {
                "risk_profile": profile.risk_profile,
                "autonomy_preference": profile.autonomy_preference,
                "horizon_temporal": profile.horizon_temporal,
                "biggest_pain_point": profile.biggest_pain_point,
                "regret_definition": profile.regret_definition,
                "relationship_with_risk": profile.relationship_with_risk,
                "additional_values": profile.additional_values,
            }

    def insert_user_profile_observed(self, profile_data: Dict[str, Any]) -> str:
        """Insere perfil observado pelo sistema."""
        record_id = str(uuid.uuid4())
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "domain": profile_data.get("domain"),
                "value": profile_data.get("observed_value"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "user_profile_observed")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            profile = UserProfileObserved(
                id=record_id,
                domain=profile_data.get("domain"),
                observed_value=profile_data.get("observed_value"),
                observation_count=profile_data.get("observation_count", 1),
                confidence=profile_data.get("confidence", 0.5),
                last_observed_at=datetime.now(timezone.utc),
                evidence=profile_data.get("evidence", []),
                diverges_from_declared=profile_data.get("diverges_from_declared", False),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(profile)
            session.commit()
            return record_id

    def get_observed_profiles(self, domain: Optional[str] = None) -> List[Dict]:
        """Busca perfis observados."""
        with self._SessionFactory() as session:
            query = session.query(UserProfileObserved)
            if domain:
                query = query.filter(UserProfileObserved.domain == domain)
            
            profiles = query.order_by(UserProfileObserved.last_observed_at.desc()).all()
            return [
                {
                    "id": p.id,
                    "domain": p.domain,
                    "value": p.observed_value,
                    "confidence": p.confidence,
                    "observation_count": p.observation_count,
                    "diverges": p.diverges_from_declared,
                }
                for p in profiles
            ]

    def insert_friction_log(self, friction_data: Dict[str, Any]) -> str:
        """Registra fricção aplicada."""
        record_id = str(uuid.uuid4())
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "category": friction_data.get("category"),
                "level": friction_data.get("friction_level"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "friction_log")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            friction = FrictionLog(
                id=record_id,
                category=friction_data.get("category"),
                pattern_triggered=friction_data.get("pattern_triggered"),
                friction_level=friction_data.get("friction_level"),
                message_sent=friction_data.get("message_sent"),
                user_response=friction_data.get("user_response"),
                response_timestamp=friction_data.get("response_timestamp"),
                outcome_7_days=friction_data.get("outcome_7_days"),
                confidence_delta=friction_data.get("confidence_delta"),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(friction)
            session.commit()
            return record_id

    def get_friction_history(self, category: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Busca histórico de fricções."""
        with self._SessionFactory() as session:
            query = session.query(FrictionLog).order_by(FrictionLog.created_at.desc())
            if category:
                query = query.filter(FrictionLog.category == category)
            
            frictions = query.limit(limit).all()
            return [
                {
                    "id": f.id,
                    "category": f.category,
                    "level": f.friction_level,
                    "user_response": f.user_response,
                    "confidence_delta": f.confidence_delta,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in frictions
            ]

    def get_similar_signals(self, domain: str, limit: int = 5) -> List[Dict]:
        """
        Busca sinais mais recentes de um domínio.

        INTENÇÃO: O Planejador injeta os Top N sinais similares
        antes de cada decisão para enriquecer o contexto.
        """
        with self._SessionFactory() as session:
            signals = (
                session.query(Signal)
                .filter(Signal.domain == domain)
                .order_by(desc(Signal.created_at))
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": s.id,
                    "domain": s.domain,
                    "title": s.title,
                    "content": s.content,
                    "relevance_score": s.relevance_score,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in signals
            ]

    def get_signals_in_window(self, start_time: datetime, end_time: datetime, domains: Optional[List[str]] = None) -> List[Dict]:
        """
        Busca sinais ocorridos dentro de uma janela temporal.
        
        INTENÇÃO: O Correlator usa isso para encontrar eventos próximos no tempo.
        """
        with self._SessionFactory() as session:
            query = session.query(Signal).filter(
                Signal.created_at >= start_time,
                Signal.created_at <= end_time
            )
            if domains:
                query = query.filter(Signal.domain.in_(domains))
            
            signals = query.order_by(Signal.created_at).all()
            return [
                {
                    "id": s.id,
                    "domain": s.domain,
                    "title": s.title,
                    "content": s.content,
                    "relevance_score": s.relevance_score,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in signals
            ]

    def get_active_patterns(self, domain: str, min_confidence: float = 0.5) -> List[Dict]:
        """
        Busca padrões causais ativos (não deprecated) de um domínio, aplicando
        decaimento temporal O(1) no momento da leitura para preservar invariante append-only.
        """
        with self._SessionFactory() as session:
            patterns = (
                session.query(CausalPattern)
                .filter(
                    CausalPattern.domain == domain,
                    CausalPattern.confidence >= min_confidence,
                )
                .all()
            )
            
            active_patterns = []
            now = datetime.now(timezone.utc)
            
            for p in patterns:
                # Decaimento: calcula dias desde a última confirmação (ou criação)
                last_time = p.last_confirmed_at if p.last_confirmed_at else p.created_at
                
                # Se last_time não tem timezone, assume UTC (o banco salva sem fuso em sqlite às vezes)
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)
                
                days_since = max(0, (now - last_time).days)
                
                # Aplica o pruner em tempo real
                current_weight = self._pruner.apply_decay(p.weight, days_since)
                
                # Só inclui se não deve ser truncado/deprecado
                if not self._pruner.should_deprecate(current_weight, p.confidence):
                    active_patterns.append({
                        "id": p.id,
                        "cause": p.cause_description,
                        "effect": p.effect_description,
                        "mechanism": p.causal_mechanism,
                        "confidence": p.confidence,
                        "weight": current_weight,  # Peso decaído
                        "confirmations": p.confirmation_count,
                    })
            
            # Ordena por peso post-decaimento
            return sorted(active_patterns, key=lambda x: x["weight"], reverse=True)

    def get_recent_hypotheses(self, status: str = "pending", limit: int = 10) -> List[Dict]:
        """Busca hipóteses recentes por status."""
        with self._SessionFactory() as session:
            hyps = (
                session.query(Hypothesis)
                .filter(Hypothesis.status == status)
                .order_by(desc(Hypothesis.created_at))
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": h.id,
                    "origin": h.origin,
                    "reasoning": h.reasoning,
                    "predicted_movement": h.predicted_movement,
                    "confidence": h.confidence_calibrated,
                    "uncertainty": h.uncertainty_acknowledged,
                    "created_at": h.created_at.isoformat() if h.created_at else None,
                }
                for h in hyps
            ]

    def get_performance_stats(self, execution_type: str = "paper") -> Dict:
        """
        Calcula estatísticas de performance.

        INTENÇÃO: O Avaliador e o sistema de transcendência usam estas
        métricas para avaliar se as condições de evolução foram atendidas.
        """
        with self._SessionFactory() as session:
            executions = (
                session.query(Execution)
                .filter(
                    Execution.execution_type == execution_type,
                    Execution.status == "closed",
                )
                .all()
            )

            if not executions:
                return {
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "win_rate": 0.0,
                    "total_pnl": 0.0,
                    "avg_pnl": 0.0,
                    "max_drawdown": 0.0,
                }

            wins = sum(1 for e in executions if e.result and e.result > 0)
            losses = sum(1 for e in executions if e.result and e.result <= 0)
            total_pnl = sum(e.result for e in executions if e.result)
            results = [e.result for e in executions if e.result]

            # Max drawdown simples
            max_dd = 0.0
            peak = 0.0
            cumulative = 0.0
            for r in results:
                cumulative += r
                if cumulative > peak:
                    peak = cumulative
                dd = peak - cumulative
                if dd > max_dd:
                    max_dd = dd

            return {
                "total_trades": len(executions),
                "wins": wins,
                "losses": losses,
                "win_rate": wins / len(executions) if executions else 0.0,
                "total_pnl": total_pnl,
                "avg_pnl": total_pnl / len(executions) if executions else 0.0,
                "max_drawdown": max_dd,
            }

    def get_user_decisions(
        self,
        user_id: str,
        since: Any = None,
        domain: str = None,
        limit: int = 50,
    ) -> List[Dict]:
        """
        Busca decisões do usuário para análise de coerência.

        INTENÇÃO: O CoherenceTracker usa isso para comparar decisões
        reais com valores declarados pelo usuário.

        Args:
            user_id: Identificador do usuário
            since: Data limite (datetime)
            domain: Filtrar por domínio (opcional)
            limit: Máximo de registros

        Returns:
            Lista de decisões com descrição, reasoning, outcome
        """
        with self._SessionFactory() as session:
            query = session.query(UserDecision)
            
            if since:
                query = query.filter(UserDecision.created_at >= since)
            
            if domain:
                query = query.filter(UserDecision.domain == domain)
            
            decisions = query.order_by(desc(UserDecision.created_at)).limit(limit).all()
            
            return [
                {
                    "id": d.id,
                    "description": d.decision_description,
                    "reasoning": d.reasoning,
                    "outcome": d.outcome,
                    "domain": d.domain,
                    "category": d.category,
                    "regret_flag": d.regret_flag,
                    "created_at": d.created_at.isoformat() if d.created_at else None,
                }
                for d in decisions
            ]

    # =========================================================================
    # ORQUESTRAÇÃO DE AGENTES — Fase 5.0
    # =========================================================================

    def insert_orchestration_plan(self, plan_data: Dict[str, Any]) -> str:
        """Registra um plano de orquestração gerado."""
        record_id = plan_data.get("id", str(uuid.uuid4()))
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "objective": plan_data.get("central_objective"),
                "status": plan_data.get("status", "draft"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "orchestration_plans")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            plan_obj = OrchestrationPlan(
                id=record_id,
                original_idea=plan_data.get("original_idea", ""),
                central_objective=plan_data.get("central_objective", ""),
                final_deliverable=plan_data.get("final_deliverable", ""),
                components=plan_data.get("components", []),
                sequence=plan_data.get("sequence", []),
                status=plan_data.get("status", "draft"),
                user_approved_at=plan_data.get("user_approved_at"),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(plan_obj)
            session.commit()
            return record_id

    def update_plan_status(self, plan_id: str, new_status: str, components: list = None) -> None:
        """Atualiza o status (e opcionalmente componentes mutados) de um plano de orquestração.
        
        NOTA: Para orquestração iterativa, o status do componente muta no JSON.
        Append-only rigoroso seria ideal, mas para workflow visual, update direto ajuda.
        """
        with self._SessionFactory() as session:
            plan = session.query(OrchestrationPlan).filter(OrchestrationPlan.id == plan_id).first()
            if plan:
                plan.status = new_status
                if components:
                    plan.components = components
                
                # SMT record - atualização mutável permitida aqui para workflow tracking (exceção SMT append-only strict)
                leaf_data = {"id": plan_id, "status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}
                leaf_obj = self._smt.insert_leaf(str(uuid.uuid4()), leaf_data, "orchestration_plan_updates")
                
                session.commit()

    def insert_agent_registry(self, agent_data: Dict[str, Any]) -> str:
        """Registra capacidades de um executor (agente)."""
        record_id = str(uuid.uuid4())
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "agent_id": agent_data.get("agent_id"),
                "agent_type": agent_data.get("agent_type"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "agent_registry")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            agent = AgentRegistry(
                id=record_id,
                agent_id=agent_data.get("agent_id"),
                name=agent_data.get("name"),
                agent_type=agent_data.get("agent_type"),
                capabilities=agent_data.get("capabilities", []),
                limitations=agent_data.get("limitations", []),
                success_history=agent_data.get("success_history", 0),
                failure_history=agent_data.get("failure_history", []),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(agent)
            session.commit()
            return record_id

    def get_agent_registry(self) -> List[Dict]:
        """Retorna todos os executores registrados."""
        with self._SessionFactory() as session:
            agents = session.query(AgentRegistry).all()
            return [
                {
                    "agent_id": a.agent_id,
                    "name": a.name,
                    "type": a.agent_type,
                    "capabilities": a.capabilities,
                    "limitations": a.limitations,
                }
                for a in agents
            ]

    def insert_task_execution(self, task_data: Dict[str, Any]) -> str:
        """Registra a delegação de uma tarefa para um agente."""
        record_id = task_data.get("id", str(uuid.uuid4()))
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "plan_id": task_data.get("plan_id"),
                "executor": task_data.get("executor_id"),
                "status": task_data.get("status", "pending"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "task_executions")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            task_obj = TaskExecution(
                id=record_id,
                plan_id=task_data.get("plan_id"),
                component_id=task_data.get("component_id"),
                executor_id=task_data.get("executor_id"),
                instruction_sent=task_data.get("instruction_sent", ""),
                status=task_data.get("status", "pending"),
                completed_at=task_data.get("completed_at"),
                received_output=task_data.get("received_output"),
                acceptance_criteria_met=task_data.get("acceptance_criteria_met"),
                quality_score=task_data.get("quality_score"),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(task_obj)
            session.commit()
            return record_id

    def update_task_execution(self, task_id: str, new_status: str, output: str = None, success: bool = None) -> None:
        """Atualiza a execução delegada (conclusão/falha)."""
        with self._SessionFactory() as session:
            task = session.query(TaskExecution).filter(TaskExecution.id == task_id).first()
            if task:
                task.status = new_status
                if new_status in ["completed", "failed"]:
                    task.completed_at = datetime.now(timezone.utc)
                if output is not None:
                    task.received_output = output
                if success is not None:
                    task.acceptance_criteria_met = success
                
                # SMT record
                leaf_data = {"id": task_id, "status": new_status}
                leaf_obj = self._smt.insert_leaf(str(uuid.uuid4()), leaf_data, "task_execution_updates")
                
                session.commit()

    def get_task_execution(self, task_id: str) -> Optional[Dict]:
        """Obtém estado atual de uma delegação."""
        with self._SessionFactory() as session:
            t = session.query(TaskExecution).filter(TaskExecution.id == task_id).first()
            if not t:
                return None
            return {
                "id": t.id,
                "plan_id": t.plan_id,
                "status": t.status,
                "executor": t.executor_id,
                "output": t.received_output,
                "success": t.acceptance_criteria_met,
            }

    def insert_delegation_log(self, log_data: Dict[str, Any]) -> str:
        """Registra o aprendizado final de uma delegação para o Router melhorar."""
        record_id = str(uuid.uuid4())
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "task_type": log_data.get("task_type"),
                "executor": log_data.get("chosen_executor"),
                "result": log_data.get("result"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "delegation_log")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            log = DelegationLog(
                id=record_id,
                task_type=log_data.get("task_type"),
                chosen_executor=log_data.get("chosen_executor"),
                task_id=log_data.get("task_id"),
                result=log_data.get("result"),
                reasoning_for_choice=log_data.get("reasoning_for_choice", ""),
                learned_lesson=log_data.get("learned_lesson"),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(log)
            session.commit()
            return record_id

    # =========================================================================
    # INTEGRIDADE
    # =========================================================================

    def get_evolution_approval(self, evolution_id: str) -> Dict[str, Any]:
        """
        Verifica se uma evolução foi aprovada manualmente.
        """
        with self._SessionFactory() as session:
            proposal = session.query(EvolutionLog).filter(EvolutionLog.id == evolution_id).first()
            if not proposal:
                return {"human_authorized": False}
            
            return {
                "id": proposal.id,
                "status": proposal.status,
                "human_authorized": proposal.status == "approved"
            }

    def verify_integrity(self, record_id: str) -> bool:
        """
        Verifica integridade de um registro via SMT.

        INTENÇÃO: Permite verificar a qualquer momento se um registro
        específico não foi adulterado.
        """
        return self._smt.verify_leaf(record_id)

    # =========================================================================
    # FEEDBACK — Infraestrutura para Fases 5 e 6
    # =========================================================================

    def insert_user_feedback(self, feedback_data: Dict[str, Any]) -> str:
        """Insere feedback do usuário sobre decisões/interações."""
        record_id = str(uuid.uuid4())
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "type": feedback_data.get("feedback_type"),
                "value": feedback_data.get("feedback_value"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "user_feedback")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            feedback = UserFeedback(
                id=record_id,
                feedback_type=feedback_data.get("feedback_type"),
                context_id=feedback_data.get("context_id"),
                context_type=feedback_data.get("context_type"),
                feedback_value=feedback_data.get("feedback_value"),
                user_comment=feedback_data.get("user_comment"),
                system_action_taken=feedback_data.get("system_action_taken"),
                system_reasoning=feedback_data.get("system_reasoning"),
                improvement_suggestion=feedback_data.get("improvement_suggestion"),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(feedback)
            session.commit()
            logger.info(f"Feedback do usuário registrado: {feedback_data.get('feedback_type')}")
            return record_id

    def get_user_feedback(self, feedback_type: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Busca feedbacks do usuário."""
        with self._SessionFactory() as session:
            query = session.query(UserFeedback).order_by(UserFeedback.created_at.desc())
            if feedback_type:
                query = query.filter(UserFeedback.feedback_type == feedback_type)
            
            feedbacks = query.limit(limit).all()
            return [
                {
                    "id": f.id,
                    "type": f.feedback_type,
                    "value": f.feedback_value,
                    "context_id": f.context_id,
                    "user_comment": f.user_comment,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
                for f in feedbacks
            ]

    def insert_uncertainty_annotation(self, annotation_data: Dict[str, Any]) -> str:
        """Insere anotação de incerteza."""
        record_id = str(uuid.uuid4())
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "question": annotation_data.get("question_asked"),
                "confidence_before": annotation_data.get("original_confidence"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "uncertainty_annotations")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            annotation = UncertaintyAnnotation(
                id=record_id,
                question_asked=annotation_data.get("question_asked"),
                user_answer=annotation_data.get("user_answer"),
                original_confidence=annotation_data.get("original_confidence"),
                confidence_after=annotation_data.get("confidence_after"),
                data_gap_identified=annotation_data.get("data_gap_identified"),
                data_gap_filled=annotation_data.get("data_gap_filled", False),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(annotation)
            session.commit()
            return record_id

    def get_uncertainty_annotations(self, limit: int = 50) -> List[Dict]:
        """Busca anotações de incerteza."""
        with self._SessionFactory() as session:
            annotations = (
                session.query(UncertaintyAnnotation)
                .order_by(UncertaintyAnnotation.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": a.id,
                    "question": a.question_asked,
                    "answer": a.user_answer,
                    "confidence_before": a.original_confidence,
                    "confidence_after": a.confidence_after,
                    "gap_filled": a.data_gap_filled,
                }
                for a in annotations
            ]

    def insert_interaction_quality(self, quality_data: Dict[str, Any]) -> str:
        """Insere avaliação de qualidade de interação."""
        record_id = str(uuid.uuid4())
        
        with self._SessionFactory() as session:
            leaf_data = {
                "id": record_id,
                "type": quality_data.get("interaction_type"),
                "rating": quality_data.get("user_rating"),
            }
            leaf_obj = self._smt.insert_leaf(record_id, leaf_data, "interaction_quality")
            leaf_hash = leaf_obj.data_hash if hasattr(leaf_obj, 'data_hash') else str(leaf_obj)
            
            quality = InteractionQuality(
                id=record_id,
                interaction_id=quality_data.get("interaction_id"),
                interaction_type=quality_data.get("interaction_type"),
                clarity_before=quality_data.get("clarity_before"),
                clarity_after=quality_data.get("clarity_after"),
                clarity_delta=quality_data.get("clarity_after", 0) - quality_data.get("clarity_before", 0),
                helpfulness=quality_data.get("helpfulness"),
                user_rating=quality_data.get("user_rating"),
                feedback_text=quality_data.get("feedback_text"),
                merkle_leaf_hash=leaf_hash,
            )
            
            session.add(quality)
            session.commit()
            return record_id

    def get_interaction_quality(self, interaction_type: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Busca avaliações de qualidade."""
        with self._SessionFactory() as session:
            query = session.query(InteractionQuality).order_by(InteractionQuality.created_at.desc())
            if interaction_type:
                query = query.filter(InteractionQuality.interaction_type == interaction_type)
            
            qualities = query.limit(limit).all()
            return [
                {
                    "id": q.id,
                    "type": q.interaction_type,
                    "clarity_delta": q.clarity_delta,
                    "helpfulness": q.helpfulness,
                    "rating": q.user_rating,
                }
                for q in qualities
            ]

    def get_merkle_root(self) -> str:
        """Retorna a Merkle Root atual."""
        return self._smt.root

    def get_smt_state(self) -> Dict:
        """Exporta estado da SMT para persistência."""
        return self._smt.export_state()
