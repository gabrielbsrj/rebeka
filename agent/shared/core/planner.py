# shared/core/planner.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — Planejador com injeção de contexto
#
# IMPACTO GÊMEO VPS: Planeja ações financeiras com visão global
# IMPACTO GÊMEO LOCAL: Planeja ações com contexto íntimo do usuário
# DIFERENÇA DE COMPORTAMENTO: O contexto injetado difere — VPS injeta sinais globais, Local injeta contexto pessoal

"""
Planejador — Raciocina sobre causalidade e gera hipóteses.

INTENÇÃO: O Planejador é o motor de raciocínio do agente. Ele:
1. Recebe contexto enriquecido automaticamente (top 5 similares, erros, performance)
2. Raciocina sobre causalidade, não sobre correlação
3. Gera hipóteses com incertezas explicitamente reconhecidas
4. NUNCA executa (essa é responsabilidade do Executor)
5. NUNCA avalia seus próprios resultados (essa é responsabilidade do Avaliador)

INVARIANTE: O Planejador nunca executa e nunca avalia.
INVARIANTE: Toda hipótese inclui uncertainty_acknowledged.
INVARIANTE: O modelo LLM do Planejador é SEPARADO do modelo do Avaliador.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

import litellm

logger = logging.getLogger(__name__)


@dataclass
class HypothesisResult:
    """Resultado da geração de hipótese pelo Planejador."""
    reasoning: str
    signals_used: List[str]
    predicted_movement: Dict[str, Any]
    confidence_calibrated: float
    uncertainty_acknowledged: str
    action: Dict[str, Any]
    raw_response: str


class Planner:
    """
    Planejador com injeção automática de contexto.

    INTENÇÃO: Antes de cada decisão, o Planejador recebe automaticamente:
    - Top 5 registros similares do Banco de Causalidade
    - Últimos 3 erros de ambiente relevantes
    - Performance recente (win rate, drawdown)
    - Perspectiva do gêmeo oposto (quando disponível)
    - Modelo atual de intenções do usuário

    LIMITAÇÃO: A qualidade do raciocínio depende do modelo LLM e do contexto
    injetado. Contexto incompleto gera hipóteses fracas.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        personality_name: str = "Rebeka",
        personality_style: str = "direto",
    ):
        """
        Args:
            model: Modelo LLM para raciocínio (DEVE ser diferente do Avaliador)
            api_key: API key
            api_base: URL base da API (opcional, para providers não-OpenAI)
            personality_name: Nome da personalidade do agente
            personality_style: Estilo de comunicação
        """
        self._model = model
        self._api_key = api_key
        self._api_base = api_base
        self._personality_name = personality_name
        self._personality_style = personality_style

    def generate_hypothesis(
        self,
        signals: List[Dict],
        active_patterns: List[Dict],
        performance_stats: Dict,
        recent_errors: Optional[List[Dict]] = None,
        twin_perspective: Optional[str] = None,
        intent_model: Optional[Dict] = None,
        domain: str = "finance",
    ) -> Optional[HypothesisResult]:
        """
        Gera hipóteses com raciocínio causal e incertezas reconhecidas.

        INTENÇÃO: O Planejador raciocina POR QUE algo deve acontecer,
        não apenas QUE algo deve acontecer. Toda hipótese inclui
        explicitamente o que pode estar errado.

        Args:
            signals: Sinais recentes do domínio
            active_patterns: Padrões causais ativos
            performance_stats: Estatísticas de performance recente
            recent_errors: Erros de ambiente recentes
            twin_perspective: Perspectiva do gêmeo oposto (se disponível)
            intent_model: Modelo atual de intenções do usuário
            domain: Domínio de raciocínio

        Returns:
            HypothesisResult ou None se nenhuma hipótese forte o suficiente.
        """
        context = self._build_context(
            signals=signals,
            active_patterns=active_patterns,
            performance_stats=performance_stats,
            recent_errors=recent_errors,
            twin_perspective=twin_perspective,
            intent_model=intent_model,
            domain=domain,
        )

        system_prompt = f"""Você é {self._personality_name}, o módulo de Planejamento de um agente autônomo.

SEU ESTILO: {self._personality_style}

REGRAS ABSOLUTAS:
1. Raciocine sobre CAUSALIDADE, não sobre correlação
2. Para cada hipótese, explicite O QUE PODE ESTAR ERRADO (uncertainty_acknowledged)
3. Sua confiança DEVE ser calibrada pelo histórico — nunca reporte confiança maior que {performance_stats.get('win_rate', 0.5) + 0.10:.2f}
4. Você NUNCA executa ações — apenas gera hipóteses para o Executor
5. Você NUNCA avalia seus próprios resultados — o Avaliador faz isso
6. Se os sinais são insuficientes, diga "SINAIS INSUFICIENTES" ao invés de inventar

FORMATO DE RESPOSTA (JSON):
{{
    "reasoning": "Raciocínio causal completo",
    "signals_used": ["id1", "id2"],
    "predicted_movement": {{"direction": "up|down|neutral", "magnitude": 0.0-1.0, "timeframe": "1h|4h|1d|1w"}},
    "confidence_calibrated": 0.0-1.0,
    "uncertainty_acknowledged": "O que pode invalidar esta hipótese",
    "action": {{"type": "buy|sell|hold|wait", "asset": "", "amount_fraction": 0.0-0.10, "reasoning": ""}}
}}

Se não houver hipótese forte, responda com:
{{"action": {{"type": "wait"}}, "reasoning": "Sinais insuficientes para ação", "confidence_calibrated": 0.0, "uncertainty_acknowledged": "Sem dados suficientes"}}
"""

        try:
            req_temp = 1.0 if "kimi-k2.5" in self._model else 0.3
            
            completion_kwargs = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context},
                ],
                "api_key": self._api_key,
                "temperature": req_temp,
                "response_format": {"type": "json_object"},
            }
            
            if self._api_base:
                completion_kwargs["api_base"] = self._api_base
            
            response = litellm.completion(**completion_kwargs)

            raw = response.choices[0].message.content
            import json
            data = json.loads(raw)

            return HypothesisResult(
                reasoning=data.get("reasoning", ""),
                signals_used=data.get("signals_used", []),
                predicted_movement=data.get("predicted_movement", {}),
                confidence_calibrated=data.get("confidence_calibrated", 0.0),
                uncertainty_acknowledged=data.get("uncertainty_acknowledged", "Não especificado"),
                action=data.get("action", {"type": "wait"}),
                raw_response=raw,
            )

        except Exception as e:
            logger.error(
                f"Falha na geração de hipótese: {e}",
                extra={
                    "domain": domain,
                    "signals_count": len(signals),
                    "will_retry": False,
                    "impact": "Nenhuma hipótese gerada — agente permanece em espera",
                },
            )
            return None

    def _build_context(
        self,
        signals: List[Dict],
        active_patterns: List[Dict],
        performance_stats: Dict,
        recent_errors: Optional[List[Dict]],
        twin_perspective: Optional[str],
        intent_model: Optional[Dict],
        domain: str,
    ) -> str:
        """
        Constrói contexto enriquecido para injeção no prompt.

        INTENÇÃO: O contexto é montado automaticamente — o Planejador
        nunca precisa buscar dados por conta própria.
        """
        parts = [f"## DOMÍNIO: {domain}\n"]

        # Sinais recentes
        if signals:
            parts.append("## SINAIS RECENTES")
            for s in signals[:5]:
                parts.append(f"- [{s.get('domain', '')}] {s.get('title', '')} "
                             f"(relevância: {s.get('relevance_score', 0):.2f})")
                if s.get("content"):
                    parts.append(f"  Conteúdo: {s['content'][:200]}")
            parts.append("")

        # Padrões causais ativos
        if active_patterns:
            parts.append("## PADRÕES CAUSAIS ATIVOS")
            for p in active_patterns[:5]:
                parts.append(f"- CAUSA: {p.get('cause', '')}")
                parts.append(f"  EFEITO: {p.get('effect', '')}")
                parts.append(f"  MECANISMO: {p.get('mechanism', '')}")
                parts.append(f"  Confiança: {p.get('confidence', 0):.2f} | Peso: {p.get('weight', 0):.2f}")
            parts.append("")

        # Performance
        parts.append("## PERFORMANCE RECENTE")
        parts.append(f"- Win rate: {performance_stats.get('win_rate', 0):.1%}")
        parts.append(f"- Total trades: {performance_stats.get('total_trades', 0)}")
        parts.append(f"- P&L total: ${performance_stats.get('total_pnl', 0):.2f}")
        parts.append(f"- Max drawdown: ${performance_stats.get('max_drawdown', 0):.2f}")
        parts.append("")

        # Erros de ambiente
        if recent_errors:
            parts.append("## ERROS DE AMBIENTE RECENTES (evite repetir)")
            for e in recent_errors[:3]:
                parts.append(f"- {e.get('description', '')}")
            parts.append("")

        # Perspectiva do gêmeo oposto
        if twin_perspective:
            parts.append("## PERSPECTIVA DO GÊMEO OPOSTO")
            parts.append(twin_perspective)
            parts.append("")

        # Modelo de intenções do usuário
        if intent_model:
            parts.append("## MODELO DE INTENÇÕES DO USUÁRIO")
            for key, value in intent_model.items():
                parts.append(f"- {key}: {value}")
            parts.append("")

        return "\n".join(parts)
