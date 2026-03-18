# shared/database/models.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-24
# CHANGELOG: v2 — Banco único PostgreSQL para ambos os gêmeos
#
# AMBOS OS GÊMEOS: Usam o mesmo banco PostgreSQL
# CAMPO origin: Identifica qual gêmeo escreveu cada registro

"""
Modelos do Banco de Causalidade — Memória Dual do Agente.

INTENÇÃO: O Banco de Causalidade é o ativo mais valioso do sistema.
Cresce para sempre. Append-only em ambos os gêmeos.

Contém duas dimensões de memória:
1. Padrões do mundo — o que o gêmeo VPS aprende monitorando o mundo 24h
2. Padrões do usuário — o que o gêmeo local aprende vivendo ao lado do usuário

INVARIANTE: Nenhum modelo permite UPDATE ou DELETE via ORM.
Toda operação de escrita é append-only via causal_bank.py.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    Text,
    JSON,
    Index,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session


class Base(DeclarativeBase):
    """Base para todos os modelos do Banco de Causalidade."""
    pass


# =============================================================================
# PADRÕES DO MUNDO — O que o gêmeo VPS aprende monitorando o mundo
# =============================================================================


class Signal(Base):
    """
    Sinais coletados pelos monitores.

    INTENÇÃO: Cada sinal é um dado bruto do mundo — uma notícia, um preço,
    um tweet, um dado econômico. Nunca é interpretação, apenas observação.
    """
    __tablename__ = "signals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    origin = Column(String, nullable=False)  # "vps" ou "local"
    domain = Column(String, nullable=False)  # ex: "geopolitics", "macro", "commodities"
    source = Column(String, nullable=False)  # ex: "reuters_rss", "twitter_api"
    title = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    raw_data = Column(JSON, nullable=True)
    relevance_score = Column(Float, nullable=False, default=0.0)
    merkle_leaf_hash = Column(String, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_signals_domain_created", "domain", "created_at"),
        Index("ix_signals_relevance", "relevance_score"),
    )


class CausalPattern(Base):
    """
    Padrões validados causalmente — quando X acontece, Y se move.

    INTENÇÃO: Apenas padrões com mecanismo causal plausível entram aqui.
    Correlações puras ficam em correlation_candidates.

    INVARIANTE: Todo padrão aqui passou pelo causal_validator.py
    """
    __tablename__ = "causal_patterns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    domain = Column(String, nullable=False)
    cause_description = Column(Text, nullable=False)
    effect_description = Column(Text, nullable=False)
    causal_mechanism = Column(Text, nullable=False)  # Por que X causa Y
    confidence = Column(Float, nullable=False)
    confirmation_count = Column(Integer, nullable=False, default=1)
    last_confirmed_at = Column(DateTime, nullable=True)
    weight = Column(Float, nullable=False, default=1.0)  # Decai com o tempo
    out_of_sample_validated = Column(Boolean, nullable=False, default=False)
    signal_ids = Column(JSON, nullable=True)  # IDs dos sinais que geraram este padrão
    merkle_leaf_hash = Column(String, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)

    __table_args__ = (
        Index("ix_causal_domain_confidence", "domain", "confidence"),
    )


class CorrelationCandidate(Base):
    """
    Correlações ainda não validadas causalmente.

    INTENÇÃO: Correlação estatística é o ponto de partida, não o destino.
    Padrões aqui têm peso menor no raciocínio até confirmação causal.
    """
    __tablename__ = "correlation_candidates"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    domain = Column(String, nullable=False)
    variable_a = Column(Text, nullable=False)
    variable_b = Column(Text, nullable=False)
    correlation_strength = Column(Float, nullable=False)
    observation_count = Column(Integer, nullable=False, default=1)
    promoted_to_causal = Column(Boolean, nullable=False, default=False)
    promoted_pattern_id = Column(String, nullable=True)
    merkle_leaf_hash = Column(String, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)


class DeprecatedPattern(Base):
    """
    Padrões arquivados por obsolescência.

    INTENÇÃO: Nunca deletados, apenas excluídos do raciocínio ativo.
    Podem ser reativados se o regime de mercado retornar.
    """
    __tablename__ = "deprecated_patterns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    original_pattern_id = Column(String, nullable=False)
    original_table = Column(String, nullable=False)  # "causal_patterns" ou "correlation_candidates"
    deprecated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    reason = Column(Text, nullable=False)
    original_data = Column(JSON, nullable=False)
    reactivated = Column(Boolean, nullable=False, default=False)
    reactivated_at = Column(DateTime, nullable=True)
    merkle_leaf_hash = Column(String, nullable=False)


class SecondOrderPattern(Base):
    """
    Padrões entre padrões — threshold 3x maior que primeira ordem.

    INTENÇÃO: Relações entre padrões de primeira ordem. Mais poder preditivo,
    mas também mais risco de correlação espúria.
    """
    __tablename__ = "second_order"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    pattern_a_id = Column(String, nullable=False)
    pattern_b_id = Column(String, nullable=False)
    relationship_description = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    confirmation_count = Column(Integer, nullable=False, default=1)
    weight = Column(Float, nullable=False, default=1.0)
    merkle_leaf_hash = Column(String, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)


class ThirdOrderPattern(Base):
    """
    Padrões de terceira ordem — threshold 10x maior.

    INTENÇÃO: Correlações entre domínios aparentemente não relacionados.
    Extremamente poderosas quando reais, extremamente perigosas quando espúrias.
    """
    __tablename__ = "third_order"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    second_order_a_id = Column(String, nullable=False)
    second_order_b_id = Column(String, nullable=False)
    domains_involved = Column(JSON, nullable=False)
    relationship_description = Column(Text, nullable=False)
    confidence = Column(Float, nullable=False)
    confirmation_count = Column(Integer, nullable=False, default=1)
    weight = Column(Float, nullable=False, default=1.0)
    merkle_leaf_hash = Column(String, nullable=False)
    metadata_ = Column("metadata", JSON, nullable=True)


# =============================================================================
# PADRÕES DO USUÁRIO — O que torna o agente verdadeiramente global
# =============================================================================


class UserDecision(Base):
    """
    Cada decisão do usuário com contexto completo.

    INTENÇÃO: Com tempo suficiente, o agente não precisa mais perguntar —
    age a partir do modelo de valores desenvolvido.
    """
    __tablename__ = "user_decisions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    decision_type = Column(String, nullable=False)  # "accept", "reject", "modify", "ignore"
    context = Column(JSON, nullable=False)  # O que foi apresentado ao usuário
    decision_data = Column(JSON, nullable=False)  # O que o usuário decidiu
    reasoning_observed = Column(Text, nullable=True)  # Raciocínio observado (se disponível)
    emotional_context = Column(String, nullable=True)  # Abstração do estado emocional
    merkle_leaf_hash = Column(String, nullable=False)


class UserCoherenceLog(Base):
    """
    Medições de coerência ao longo do tempo.

    INTENÇÃO: O usuário age com mais consistência com os valores que declarou?
    """
    __tablename__ = "user_coherence_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    declared_value = Column(Text, nullable=False)
    observed_action = Column(Text, nullable=False)
    coherence_score = Column(Float, nullable=False)  # 0.0 a 1.0
    analysis = Column(Text, nullable=True)
    merkle_leaf_hash = Column(String, nullable=False)


class UserRegretSignal(Base):
    """
    Indicadores de arrependimento detectados.

    INTENÇÃO: Um trade que deu dinheiro mas sob pressão gera arrependimento
    mesmo com lucro. Detectar isso é tão importante quanto detectar lucro.
    """
    __tablename__ = "user_regret_signals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    related_decision_id = Column(String, nullable=True)
    regret_type = Column(String, nullable=False)  # "action_taken", "action_not_taken"
    indicators = Column(JSON, nullable=False)
    severity = Column(Float, nullable=False)  # 0.0 a 1.0
    merkle_leaf_hash = Column(String, nullable=False)


class UserClarityDelta(Base):
    """
    Mudanças de clareza após cada interação.

    INTENÇÃO: O usuário tem mais clareza sobre o que quer depois desta
    interação do que antes? Essa é a métrica humana do Avaliador.
    """
    __tablename__ = "user_clarity_deltas"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    interaction_id = Column(String, nullable=False)
    clarity_before = Column(Float, nullable=False)
    clarity_after = Column(Float, nullable=False)
    delta = Column(Float, nullable=False)
    domain = Column(String, nullable=False)
    merkle_leaf_hash = Column(String, nullable=False)


class IntentModel(Base):
    """
    Modelo atual de valores e intenções do usuário.

    INTENÇÃO: Snapshot do modelo de intenções em cada momento.
    Append-only — cada atualização é um novo registro, nunca sobrescreve.
    """
    __tablename__ = "intent_model"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    version = Column(Integer, nullable=False)
    values_declared = Column(JSON, nullable=False)
    values_observed = Column(JSON, nullable=False)
    contradictions_detected = Column(JSON, nullable=True)
    confidence_in_model = Column(Float, nullable=False)
    based_on_decisions_count = Column(Integer, nullable=False)
    merkle_leaf_hash = Column(String, nullable=False)


# =============================================================================
# SISTEMA — Infraestrutura do agente
# =============================================================================


class Hypothesis(Base):
    """
    Hipóteses do Planejador com incertezas reconhecidas.

    INTENÇÃO: O planejador raciocina sobre causalidade e gera hipóteses.
    Cada hipótese inclui explicitamente o que pode estar errado.
    """
    __tablename__ = "hypotheses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    origin = Column(String, nullable=False)  # "vps", "local", "synthesis"
    reasoning = Column(Text, nullable=False)
    signals_used = Column(JSON, nullable=False)
    predicted_movement = Column(JSON, nullable=False)
    confidence_calibrated = Column(Float, nullable=False)
    uncertainty_acknowledged = Column(Text, nullable=False)
    action = Column(JSON, nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending, executing, resolved
    merkle_leaf_hash = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_hypotheses_status_created", "status", "created_at"),
    )


class Execution(Base):
    """
    Execuções paper e real.

    INTENÇÃO: Registro completo de toda operação, com raciocínio e resultado.
    Alimenta o Avaliador e o Banco de Causalidade.
    """
    __tablename__ = "executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    hypothesis_id = Column(String, nullable=False)
    execution_type = Column(String, nullable=False)  # "paper" ou "real"
    market = Column(String, nullable=False)  # "polymarket", "crypto", etc.
    asset = Column(String, nullable=False)
    direction = Column(String, nullable=False)  # "buy", "sell"
    amount = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=True)
    exit_price = Column(Float, nullable=True)
    result = Column(Float, nullable=True)  # P&L
    status = Column(String, nullable=False, default="open")  # open, closed, cancelled
    closed_at = Column(DateTime, nullable=True)
    merkle_leaf_hash = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_executions_type_status", "execution_type", "status"),
    )


class Evaluation(Base):
    """
    Avaliações do Avaliador — financeiras e humanas.

    INTENÇÃO: Cada avaliação responde: a hipótese estava correta?
    O que não foi visto? A interação aumentou a clareza do usuário?
    """
    __tablename__ = "evaluations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    hypothesis_id = Column(String, nullable=False)
    execution_id = Column(String, nullable=True)
    hypothesis_correct = Column(Boolean, nullable=True)
    reasoning_analysis = Column(Text, nullable=False)
    missed_signals = Column(JSON, nullable=True)
    twin_perspective_would_help = Column(Boolean, nullable=True)
    clarity_impact = Column(Float, nullable=True)  # -1.0 a 1.0
    coherence_impact = Column(Float, nullable=True)  # -1.0 a 1.0
    lessons_learned = Column(Text, nullable=False)
    merkle_leaf_hash = Column(String, nullable=False)


class EnvironmentError(Base):
    """
    Falhas por ambiente — não falhas lógicas, falhas de infraestrutura.

    INTENÇÃO: O Executor consulta este registro antes de cada operação
    para evitar repetir erros de ambiente conhecidos.
    """
    __tablename__ = "environment_errors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    error_type = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    context = Column(JSON, nullable=True)
    resolution = Column(Text, nullable=True)
    resolved = Column(Boolean, nullable=False, default=False)
    merkle_leaf_hash = Column(String, nullable=False)


class CodeVersion(Base):
    """
    Histórico de versões de cada módulo.

    INTENÇÃO: Permite rastrear qual versão do Planejador gerou qual hipótese.
    Fundamental para auditoria de longo prazo.
    """
    __tablename__ = "code_versions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    module_path = Column(String, nullable=False)
    version = Column(String, nullable=False)
    git_hash = Column(String, nullable=True)
    changes_description = Column(Text, nullable=False)
    merkle_leaf_hash = Column(String, nullable=False)


class EvolutionLog(Base):
    """
    Melhorias propostas, testadas e implementadas.

    INTENÇÃO: Registro completo do ciclo de evolução do agente.
    """
    __tablename__ = "evolution_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    proposal = Column(Text, nullable=False)
    reasoning = Column(Text, nullable=False)
    sandbox_result = Column(JSON, nullable=True)
    twin_evaluation = Column(JSON, nullable=True)
    invariants_passed = Column(Boolean, nullable=True)
    status = Column(String, nullable=False, default="proposed")  # proposed, testing, approved, rejected, deployed
    deployed_at = Column(DateTime, nullable=True)
    merkle_leaf_hash = Column(String, nullable=False)


class TranscendenceLog(Base):
    """
    Restrições removidas e por quê.

    INTENÇÃO: O transcendence_tracker propõe remoção formal quando
    o histórico demonstra que o julgamento interno é mais sofisticado
    que a restrição externa.
    """
    __tablename__ = "transcendence_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    restriction_name = Column(String, nullable=False)
    restriction_original = Column(Text, nullable=False)
    evidence_for_removal = Column(JSON, nullable=False)
    historical_compliance_rate = Column(Float, nullable=False)
    user_approved = Column(Boolean, nullable=True)
    user_approved_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, default="proposed")  # proposed, approved, rejected
    merkle_leaf_hash = Column(String, nullable=False)


class MerkleTreeRecord(Base):
    """
    Raízes e provas de integridade por timestamp.

    INTENÇÃO: Cada operação no banco gera uma nova Merkle Root.
    Isso permite verificar integridade em qualquer ponto do tempo.
    """
    __tablename__ = "merkle_tree"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    merkle_root = Column(String, nullable=False)
    leaf_count = Column(Integer, nullable=False)
    operation_type = Column(String, nullable=False)  # "insert", "anonymize"
    affected_table = Column(String, nullable=False)
    affected_record_id = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_merkle_created", "created_at"),
    )


class SynthesisLog(Base):
    """
    Perspectivas emergentes e falhas de síntese.

    INTENÇÃO: Quando os gêmeos divergem, o Synthesis Engine tenta criar
    uma terceira perspectiva. Este log registra as tentativas e resultados.
    """
    __tablename__ = "synthesis_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    twin_vps_position = Column(Text, nullable=False)
    twin_local_position = Column(Text, nullable=False)
    synthesis_attempts = Column(JSON, nullable=False)
    divergence_root = Column(Text, nullable=True)
    confidence_vps = Column(Float, nullable=False)
    confidence_local = Column(Float, nullable=False)
    synthesis_succeeded = Column(Boolean, nullable=False)
    emergent_perspective = Column(Text, nullable=True)
    presented_to_user = Column(Text, nullable=True)
    merkle_leaf_hash = Column(String, nullable=False)


class PrivacyAuditLog(Base):
    """
    Todo dado que saiu do gêmeo local.

    INTENÇÃO: O usuário pode auditar em qualquer momento o que
    o gêmeo local compartilhou com a VPS. Transparência total.
    """
    __tablename__ = "privacy_audit_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    data_type = Column(String, nullable=False)  # Tipo de abstração enviada
    destination = Column(String, nullable=False)  # "vps"
    abstraction_sent = Column(Text, nullable=False)  # A abstração, não o dado original
    approved_by_filter = Column(Boolean, nullable=False)
    transmission_confirmed = Column(Boolean, nullable=False, default=False)
    merkle_leaf_hash = Column(String, nullable=False)


class MonitorLifecycle(Base):
    """
    Criação, pausa e destruição de monitores dinâmicos.

    INTENÇÃO: Em um agente global, monitores são dinâmicos por relevância
    pessoal. Este log rastreia o ciclo de vida de cada monitor.
    """
    __tablename__ = "monitor_lifecycle"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    monitor_name = Column(String, nullable=False)
    domain = Column(String, nullable=False)
    action = Column(String, nullable=False)  # "created", "paused", "resumed", "destroyed"
    reason = Column(Text, nullable=False)
    triggered_by = Column(String, nullable=False)  # "intent_engine", "user", "orchestrator"
    merkle_leaf_hash = Column(String, nullable=False)


# =============================================================================
# CRESCIMENTO E FRICÇÃO — Novos módulos da Fase 2
# =============================================================================


class GrowthTarget(Base):
    """
    Horizontes de crescimento declarados pelo usuário.

    INTENÇÃO: Registro explícito do futuro que o usuário quer para si —
    e monitoramento contínuo da distância entre comportamento atual e esse futuro.
    Não é sistema de metas. É espelho longitudinal.
    """
    __tablename__ = "growth_targets"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    domain = Column(String, nullable=False)  # "trading", "saude", "carreira", etc.
    current_state_declared = Column(Text, nullable=False)  # "opero por impulso, sem stops"
    desired_future_state = Column(Text, nullable=False)  # "opero com disciplina, gestão de risco"
    progress_metrics = Column(JSON, nullable=False)  # Métricas a monitorar
    declaration_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    target_deadline = Column(DateTime, nullable=True)  # Prazo desejado
    active = Column(Boolean, nullable=False, default=True)
    merkle_leaf_hash = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_growth_targets_domain_active", "domain", "active"),
    )


class GrowthProgressLog(Base):
    """
    Snapshots semanais do progresso em cada horizonte.

    INTENÇÃO: A cada semana, o sistema calcula a distância real entre
    comportamento atual e futuro desejado.
    """
    __tablename__ = "growth_progress_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    target_id = Column(String, nullable=False)
    week_number = Column(Integer, nullable=False)  # Semana 1, 2, 3...
    metrics_snapshot = Column(JSON, nullable=False)  # Valores reais desta semana
    distance_from_goal = Column(Float, nullable=False)  # 0.0 (perto) a 1.0 (longe)
    trend = Column(String, nullable=False)  # "improving", "stagnant", "regressing"
    system_notes = Column(Text, nullable=True)  # Observação qualitativa
    merkle_leaf_hash = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_growth_progress_target_week", "target_id", "week_number"),
    )


class GrowthRedefinition(Base):
    """
    Quando e por que o usuário redefiniu um horizonte.

    INTENÇÃO: O usuário pode redefinir o horizonte a qualquer momento.
    O sistema registra o padrão de redefinições como dado em si.
    """
    __tablename__ = "growth_redefinitions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    previous_target_id = Column(String, nullable=False)
    new_target_id = Column(String, nullable=False)
    reason_provided = Column(Text, nullable=True)  # O que o usuário disse
    context_detected = Column(Text, nullable=True)  # O que o sistema detectou
    merkle_leaf_hash = Column(String, nullable=False)


class ConversationSignal(Base):
    """
    Sinais extraídos em tempo real durante conversas.

    INTENÇÃO: Capacidade de "ver" o usuário enquanto ele fala.
    Não transcrever — extrair sinais estruturados em paralelo.
    """
    __tablename__ = "conversation_signals"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    conversation_id = Column(String, nullable=True)
    behavioral_patterns = Column(JSON, nullable=True)  # Padrões mencionados
    emotional_state_inferred = Column(String, nullable=True)  # Inferido pelo tom
    emotional_confidence = Column(Float, nullable=True)
    emotional_decay_date = Column(DateTime, nullable=True)  # 7 dias após inferência
    external_events = Column(JSON, nullable=True)  # Eventos citados com datas
    self_attribution = Column(JSON, nullable=True)  # Atribui erros a si ou externo
    values_revealed = Column(JSON, nullable=True)  # O que importa pelo que lamenta
    friction_potential = Column(JSON, nullable=True)  # Padrões candidatos a fricção
    growth_horizon_implicit = Column(JSON, nullable=True)  # Futuro implícito na fala
    merkle_leaf_hash = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_conversation_signals_created", "created_at"),
    )


class BehavioralPattern(Base):
    """
    Padrões comportamentais detectados com confidence crescente.

    INTENÇÃO: Padrões recorrentes confirmados por múltiplas observações.
    Confidence aumenta com cada confirmação.
    """
    __tablename__ = "behavioral_patterns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    domain = Column(String, nullable=False)  # "trading", "comunicacao", etc.
    pattern_type = Column(String, nullable=False)  # "stop_loss", "revenge_trading", "vies_alta"
    description = Column(Text, nullable=False)
    first_detected_at = Column(DateTime, nullable=False)
    last_detected_at = Column(DateTime, nullable=False)
    confirmation_count = Column(Integer, nullable=False, default=1)
    confidence = Column(Float, nullable=False)  # 0.0 a 1.0, sobe com confirmações
    potentially_limiting = Column(Boolean, nullable=False, default=False)
    evidence = Column(JSON, nullable=True)  # Lista de observações
    parent_pattern_id = Column(String, nullable=True)  # Referência ao padrão anterior (append-only chain)
    merkle_leaf_hash = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_behavioral_patterns_domain_confidence", "domain", "confidence"),
        Index("ix_behavioral_patterns_parent", "parent_pattern_id"),
    )


class UserProfileDeclared(Base):
    """
    Perfil declarado pelo usuário — o que ele diz que é.

    INTENÇÃO: Ponto de partida, versão aspiracional.
    Editável pelo usuário. Comparado com observado depois.
    """
    __tablename__ = "user_profile_declared"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    risk_profile = Column(String, nullable=True)  # "conservador", "moderado", "arrojado"
    autonomy_preference = Column(String, nullable=True)  # "consultado", "avisado_depois", "autonomo"
    horizon_temporal = Column(String, nullable=True)  # "curto", "medio", "longo"
    biggest_pain_point = Column(String, nullable=True)  # Domínio de maior dor
    regret_definition = Column(Text, nullable=True)  # O que incomoda mais
    relationship_with_risk = Column(Text, nullable=True)  # Resposta à pergunta 1
    additional_values = Column(JSON, nullable=True)  # Valores adicionais declarados
    merkle_leaf_hash = Column(String, nullable=False)


class UserProfileObserved(Base):
    """
    Perfil observado do usuário — o que o comportamento revela.

    INTENÇÃO: Dado primário quando diverge do declarado.
    Atualizado só pelo sistema, nunca editável manualmente.
    """
    __tablename__ = "user_profile_observed"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    domain = Column(String, nullable=False)
    observed_value = Column(String, nullable=False)
    observation_count = Column(Integer, nullable=False, default=1)
    confidence = Column(Float, nullable=False)
    last_observed_at = Column(DateTime, nullable=False)
    evidence = Column(JSON, nullable=True)
    diverges_from_declared = Column(Boolean, nullable=False, default=False)
    divergence_id = Column(String, nullable=True)  # ID do registro de divergência
    merkle_leaf_hash = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_user_profile_observed_domain", "domain"),
    )


class FrictionLog(Base):
    """
    Registro de fricções aplicadas e resposta do usuário.

    INTENÇÃO: O sistema aprende quais tipos de fricção são produtivos
    para este usuário específico — e ajusta tom e timing.
    """
    __tablename__ = "friction_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    category = Column(String, nullable=False)  # "vies_alta", "revenge_trading", etc.
    pattern_triggered = Column(String, nullable=False)  # ID do padrão que motivou
    friction_level = Column(String, nullable=False)  # "leve", "moderada", "direta"
    message_sent = Column(Text, nullable=False)
    user_response = Column(String, nullable=True)  # "receptivo", "defensivo", "ignorou", "refletiu"
    response_timestamp = Column(DateTime, nullable=True)
    outcome_7_days = Column(JSON, nullable=True)  # Comportamento mudou?
    confidence_delta = Column(Float, nullable=True)  # Padrão ficou mais/menos forte
    merkle_leaf_hash = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_friction_log_created", "created_at"),
    )


# =============================================================================
# FEEDBACK DO USUÁRIO — Infraestrutura para Fases 5 e 6
# =============================================================================


class UserFeedback(Base):
    """
    Feedback do usuário sobre decisões e interações.

    INTENÇÃO: O sistema aprende com feedback explícito.
    Cada interação onde o usuário corrige ou approve é dado de treinamento.
    """
    __tablename__ = "user_feedback"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    feedback_type = Column(String, nullable=False)  # "decision_approval", "friction_response", "clarity_help", "escalation_correct"
    
    context_id = Column(String, nullable=True)  # ID da hipótese/decisão/fricção
    context_type = Column(String, nullable=True)  # "hypothesis", "friction", "growth_checkin"
    
    feedback_value = Column(String, nullable=False)  # "correct", "incorrect", "helpful", "not_helpful", "should_have_asked"
    
    user_comment = Column(Text, nullable=True)
    
    system_action_taken = Column(Text, nullable=True)
    system_reasoning = Column(Text, nullable=True)
    
    improvement_suggestion = Column(Text, nullable=True)
    merkle_leaf_hash = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_user_feedback_type", "feedback_type"),
        Index("ix_user_feedback_created", "created_at"),
    )


class UncertaintyAnnotation(Base):
    """
    Anotações de incerteza para auto-aprendizado.

    INTENÇÃO: Quando o sistema não tem certeza, registra o que
    seria necessário para ter certeza. Usuário pode completar.
    """
    __tablename__ = "uncertainty_annotations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    question_asked = Column(Text, nullable=False)  # O que o sistema perguntou
    user_answer = Column(Text, nullable=True)  # Resposta do usuário
    
    original_confidence = Column(Float, nullable=False)
    confidence_after = Column(Float, nullable=True)
    
    data_gap_identified = Column(Text, nullable=True)  # O que faltava para saber
    data_gap_filled = Column(Boolean, nullable=False, default=False)
    
    merkle_leaf_hash = Column(String, nullable=False)


# =============================================================================
# COMUNICAÇÃO EXTERNA — Email e Financeiro (v6.0)
# =============================================================================

class FinancialAlert(Base):
    """
    Alertas financeiros extraídos do EmailManager.
    
    INTENÇÃO: Nunca pagar. Apenas armazenar para o Radar Financeiro avisar o usuário.
    """
    __tablename__ = "financial_alerts"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    email_id = Column(String, nullable=False)
    creditor = Column(String, nullable=False)
    valor = Column(Float, nullable=False)
    vencimento = Column(DateTime, nullable=False)
    banco = Column(String, nullable=False)
    tipo = Column(String, nullable=False)  # boleto, cartão, etc.
    status = Column(String, nullable=False, default="pendente")
    alerta_enviado = Column(Boolean, nullable=False, default=False)
    pago = Column(Boolean, nullable=False, default=False)
    
    __table_args__ = (
        Index("ix_financial_alerts_status_venc", "status", "vencimento"),
    )


class InteractionQuality(Base):
    """
    Qualidade de interação avaliada pelo usuário.

    INTENÇÃO: Métrica humana — o usuário achou que a interação
    aumentou sua clareza? O sistema está sendo útil?
    """
    __tablename__ = "interaction_quality"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    interaction_id = Column(String, nullable=False)
    interaction_type = Column(String, nullable=False)  # "friction", "growth_checkin", "decision_proposal"
    
    clarity_before = Column(Float, nullable=True)  # 0-1
    clarity_after = Column(Float, nullable=True)   # 0-1
    clarity_delta = Column(Float, nullable=True)   # after - before
    
    helpfulness = Column(Float, nullable=True)  # 0-1
    
    user_rating = Column(Integer, nullable=True)  # 1-5 stars
    
    feedback_text = Column(Text, nullable=True)
    merkle_leaf_hash = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_interaction_quality_type", "interaction_type"),
    )


# =============================================================================
# ORQUESTRAÇÃO DE AGENTES — Novos módulos da Fase 5.0
# =============================================================================


class OrchestrationPlan(Base):
    """
    Planos de Orquestração baseados em objetivos do usuário.
    
    INTENÇÃO: O Decomposer quebra a ideia e gera um plano estruturado
    com componentes, sequência e dependências.
    """
    __tablename__ = "orchestration_plans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    original_idea = Column(Text, nullable=False)
    central_objective = Column(Text, nullable=False)
    final_deliverable = Column(Text, nullable=False)
    components = Column(JSON, nullable=False)  # Lista completa de componentes
    sequence = Column(JSON, nullable=False)  # Fases e paralelismo
    status = Column(String, nullable=False, default="draft")  # draft, approved, executing, completed
    user_approved_at = Column(DateTime, nullable=True)
    merkle_leaf_hash = Column(String, nullable=False)

    __table_args__ = (
        Index("ix_orchestration_plans_status", "status"),
    )


class AgentRegistry(Base):
    """
    Diretório de EXECUTORES conhecidos e suas capacidades.
    
    INTENÇÃO: O Router usa este registro para saber quem é melhor 
    para cada tarefa (IDE, LLM, automação, humano).
    """
    __tablename__ = "agent_registry"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    agent_id = Column(String, nullable=False, unique=True)
    name = Column(String, nullable=False)
    agent_type = Column(String, nullable=False)  # ide_agent, llm_model, research, visual_automation, human
    capabilities = Column(JSON, nullable=False)
    limitations = Column(JSON, nullable=False)
    success_history = Column(Integer, nullable=False, default=0)
    failure_history = Column(JSON, nullable=True)  # Contexto de falhas passadas
    merkle_leaf_hash = Column(String, nullable=False)


class TaskExecution(Base):
    """
    Tarefas individuais delegadas do plano para os executores.
    
    INTENÇÃO: Unidade granular de execução coordenada pela orquestradora.
    """
    __tablename__ = "task_executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    plan_id = Column(String, nullable=False)
    component_id = Column(String, nullable=False)
    executor_id = Column(String, nullable=False)
    instruction_sent = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="pending")  # pending, running, completed, blocked, failed
    completed_at = Column(DateTime, nullable=True)
    received_output = Column(Text, nullable=True)
    acceptance_criteria_met = Column(Boolean, nullable=True)
    quality_score = Column(Float, nullable=True)
    merkle_leaf_hash = Column(String, nullable=False)
    
    __table_args__ = (
        Index("ix_task_executions_plan", "plan_id"),
        Index("ix_task_executions_status", "status"),
    )


class DelegationLog(Base):
    """
    Log de decisões do Router de agentes (aprendizado de roteamento).
    
    INTENÇÃO: O sistema deve aprender quais agentes funcionam 
    melhor para quais tipos de tarefa com o tempo.
    """
    __tablename__ = "delegation_log"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    task_type = Column(String, nullable=False)
    chosen_executor = Column(String, nullable=False)
    task_id = Column(String, nullable=False)
    result = Column(String, nullable=False)  # success, failure, partial
    reasoning_for_choice = Column(Text, nullable=False)
    learned_lesson = Column(Text, nullable=True)
    merkle_leaf_hash = Column(String, nullable=False)


# =============================================================================
# UTILIDADES
# =============================================================================

def create_all_tables(engine):
    """
    Cria todas as tabelas no banco de dados.

    INTENÇÃO: Usado na inicialização do agente para garantir que
    todas as tabelas existem antes de qualquer operação.
    """
    Base.metadata.create_all(engine)


def get_engine(database_url: str):
    """
    Cria engine SQLAlchemy baseado na URL do banco.

    INTENÇÃO: Abstrai a diferença entre PostgreSQL (VPS) e SQLite (Local).
    """
    return create_engine(database_url, echo=False)
