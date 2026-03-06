# shared/intent/coherence_tracker.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Implementação do cálculo real de coerência via LLM
#
# IMPACTO GÊMEO VPS: Usa para avaliar decisões financeiras do usuário
# IMPACTO GÊMEO LOCAL: Usa para avaliar coerência em contexto íntimo
# DIFERENÇA DE COMPORTAMENTO: Mesmo cálculo, diferentes fontes de dados

"""
Coherence Tracker — Monitora coerência entre valores e ações.

INTENÇÃO: Se o usuário diz "quero segurança" mas sempre aceita trades
de alto risco, o agente detecta essa dissonância e oferece clareza.
Não para criticar — para ajudar o usuário a se conhecer melhor.

IMPLEMENTAÇÃO: Usa LLM para analisar padrão de decisões no banco:
- decisões tomadas vs valores no intent_model
- taxa de arrependimento por categoria
- consistência entre o que aprova na prática vs o que declara querer

INVARIANTE: Retorna sempre valor entre 0.0 e 1.0
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

import litellm

logger = logging.getLogger(__name__)


class CoherenceTracker:
    """
    Monitora coerência do usuário entre valores declarados e ações reais.

    INTENÇÃO: O agente de coerência pessoal não otimiza o usuário.
    Ele reflete. Se há dissonância, apresenta com clareza e sem julgamento.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        causal_bank=None,
    ):
        """
        Args:
            model: Modelo LLM para análise de coerência
            api_key: API key do provedor
            causal_bank: Referência ao Banco de Causalidade para buscar decisões
        """
        self._model = model
        self._api_key = api_key
        self._causal_bank = causal_bank
        self._coherence_history: List[Dict] = []
        self._cached_intentions: Dict[str, str] = {}

    def calculate_coherence(
        self,
        user_id: str,
        intent_model: Dict[str, Any],
        timeframe_days: int = 30,
        domain: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calcula coerência do usuário via análise LLM.

        INTENÇÃO: Mede se o usuário está agindo consistentemente com os valores
        que declarou ao longo do tempo. Usado pelo Avaliador como dimensão humana.

        Args:
            user_id: Identificador do usuário
            intent_model: Modelo de intenções/valores declarados
            timeframe_days: Período de análise em dias
            domain: Domínio específico (opcional, ex: "finance")

        Returns:
            Dict com coherence_score (0.0-1.0), analysis, contradictions, trends
        """
        # 1. Coletar decisões do período
        decisions = self._fetch_user_decisions(user_id, timeframe_days, domain)

        if len(decisions) < 3:
            logger.info(f"Dados insuficientes para cálculo de coerência: {len(decisions)} decisões")
            return {
                "coherence_score": 0.5,
                "analysis": "Dados insuficientes para análise. Mínimo 3 decisões necessárias.",
                "confidence": 0.0,
                "decisions_analyzed": len(decisions),
                "contradictions": [],
                "consistent_patterns": [],
            }

        # 2. Extrair valores declarados
        declared_values = self._extract_declared_values(intent_model)

        if not declared_values:
            logger.info("Nenhum valor declarado encontrado no intent_model")
            return {
                "coherence_score": 0.5,
                "analysis": "Nenhum valor declarado para comparação.",
                "confidence": 0.0,
                "decisions_analyzed": len(decisions),
                "contradictions": [],
                "consistent_patterns": [],
            }

        # 3. Analisar via LLM
        analysis = self._analyze_coherence_with_llm(decisions, declared_values, domain)

        # 4. Registrar no histórico
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_id": user_id,
            "coherence_score": analysis.get("coherence_score", 0.5),
            "decisions_analyzed": len(decisions),
            "timeframe_days": timeframe_days,
            "domain": domain,
        }
        self._coherence_history.append(entry)

        return analysis

    def _fetch_user_decisions(
        self,
        user_id: str,
        timeframe_days: int,
        domain: Optional[str],
    ) -> List[Dict]:
        """Busca decisões do usuário no Banco de Causalidade."""
        if self._causal_bank is None:
            logger.warning("CausalBank não configurado — retornando lista vazia")
            return []

        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=timeframe_days)

            decisions = self._causal_bank.get_user_decisions(
                user_id=user_id,
                since=cutoff,
                domain=domain,
                limit=50,
            )
            return decisions
        except Exception as e:
            logger.error(f"Erro ao buscar decisões do usuário: {e}")
            return []

    def _extract_declared_values(self, intent_model: Dict[str, Any]) -> List[Dict]:
        """Extrai valores declarados do modelo de intenções."""
        values = []

        if not intent_model:
            return values

        # Valores explícitos
        if "declared_values" in intent_model:
            for v in intent_model["declared_values"]:
                values.append({
                    "type": "declared",
                    "value": v.get("value", ""),
                    "category": v.get("category", "general"),
                    "priority": v.get("priority", "medium"),
                })

        # Intenções extraídas de regras
        if "intentions" in intent_model:
            for path, intent in intent_model["intentions"].items():
                values.append({
                    "type": "from_rule",
                    "value": intent.get("intention", ""),
                    "rule_path": path,
                    "category": self._categorize_rule_path(path),
                })

        # Valores inferidos de comportamento
        if "inferred_values" in intent_model:
            for v in intent_model["inferred_values"]:
                values.append({
                    "type": "inferred",
                    "value": v.get("value", ""),
                    "confidence": v.get("confidence", 0.5),
                    "category": v.get("category", "general"),
                })

        return values

    def _categorize_rule_path(self, path: str) -> str:
        """Categoriza um caminho de regra."""
        if "finance" in path:
            return "finance"
        elif "privacy" in path:
            return "privacy"
        elif "autonomy" in path:
            return "autonomy"
        elif "vault" in path:
            return "security"
        return "general"

    def _analyze_coherence_with_llm(
        self,
        decisions: List[Dict],
        declared_values: List[Dict],
        domain: Optional[str],
    ) -> Dict[str, Any]:
        """Usa LLM para analisar coerência entre decisões e valores."""

        system_prompt = """Você é um analista de coerência pessoal. Sua tarefa é avaliar se as ações de uma pessoa estão alinhadas com os valores que ela declarou.

Analise com empatia e sem julgamento. O objetivo não é criticar, mas oferecer clareza.

Responda em JSON com esta estrutura:
{
    "coherence_score": 0.0-1.0,
    "analysis": "Análise narrativa da coerência observada",
    "contradictions": [
        {
            "declared_value": "valor que foi declarado",
            "observed_action": "ação que contradiz",
            "severity": "low|medium|high",
            "context": "explicação da contradição"
        }
    ],
    "consistent_patterns": [
        {
            "declared_value": "valor que foi declarado",
            "supporting_actions": ["ações que demonstram"],
            "strength": "weak|moderate|strong"
        }
    ],
    "recommendations": ["sugestões para aumentar clareza"],
    "confidence_in_analysis": 0.0-1.0
}

Critérios para coherence_score:
- 0.9-1.0: Ações altamente consistentes com valores
- 0.7-0.89: Maioria consistente, algumas divergências menores
- 0.5-0.69: Mistura de consistência e contradições
- 0.3-0.49: Várias contradições significativas
- 0.0-0.29: Ações frequentemente contradizem valores declarados"""

        # Preparar contexto
        context_parts = ["## VALORES DECLARADOS PELO USUÁRIO\n"]
        for v in declared_values[:10]:
            context_parts.append(f"- [{v.get('type', 'unknown')}] {v.get('value', '')}")
            if v.get("category"):
                context_parts[-1] += f" (categoria: {v['category']})"

        context_parts.append("\n## DECISÕES TOMADAS PELO USUÁRIO\n")
        for i, d in enumerate(decisions[:20], 1):
            context_parts.append(f"{i}. {d.get('description', d.get('action', 'Decisão sem descrição'))}")
            if d.get("reasoning"):
                context_parts.append(f"   Razão: {d['reasoning'][:100]}")
            if d.get("outcome"):
                context_parts.append(f"   Resultado: {d['outcome']}")

        if domain:
            context_parts.insert(0, f"## DOMÍNIO DE ANÁLISE: {domain}\n")

        context = "\n".join(context_parts)

        try:
            response = litellm.completion(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context},
                ],
                api_key=self._api_key,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            result = json.loads(raw)

            # Validar e normalizar
            coherence_score = float(result.get("coherence_score", 0.5))
            coherence_score = max(0.0, min(1.0, coherence_score))

            return {
                "coherence_score": coherence_score,
                "analysis": result.get("analysis", ""),
                "contradictions": result.get("contradictions", []),
                "consistent_patterns": result.get("consistent_patterns", []),
                "recommendations": result.get("recommendations", []),
                "confidence": float(result.get("confidence_in_analysis", 0.5)),
                "decisions_analyzed": len(decisions),
                "values_analyzed": len(declared_values),
            }

        except Exception as e:
            logger.error(f"Erro na análise LLM de coerência: {e}")
            return {
                "coherence_score": 0.5,
                "analysis": f"Erro na análise: {str(e)}",
                "contradictions": [],
                "consistent_patterns": [],
                "confidence": 0.0,
                "decisions_analyzed": len(decisions),
                "error": str(e),
            }

    def track(
        self,
        declared_value: str,
        observed_action: str,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Registra e analisa coerência entre valor declarado e ação observada.

        Este método é mantido para compatibilidade com código existente.
        Para análise completa, use calculate_coherence().

        Returns:
            Dict com coherence_score (0-1), analysis, e trend.
        """
        # Análise rápida via LLM
        analysis = self._quick_coherence_check(declared_value, observed_action)

        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "declared_value": declared_value,
            "observed_action": observed_action,
            "coherence_score": analysis.get("coherence_score", 0.5),
            "context": context,
        }
        self._coherence_history.append(entry)

        return {
            "coherence_score": analysis.get("coherence_score", 0.5),
            "analysis": analysis.get("analysis", ""),
            "trend": self._calculate_trend(),
            "total_observations": len(self._coherence_history),
        }

    def _quick_coherence_check(
        self,
        declared_value: str,
        observed_action: str,
    ) -> Dict[str, Any]:
        """Verificação rápida de coerência entre valor e ação."""
        prompt = f"""Analise se esta ação é coerente com o valor declarado.

Valor declarado: "{declared_value}"
Ação observada: "{observed_action}"

Responda em JSON:
{{
    "coherence_score": 0.0-1.0,
    "analysis": "breve explicação"
}}"""

        try:
            response = litellm.completion(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self._api_key,
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            result = json.loads(raw)

            score = float(result.get("coherence_score", 0.5))
            return {
                "coherence_score": max(0.0, min(1.0, score)),
                "analysis": result.get("analysis", ""),
            }

        except Exception as e:
            logger.warning(f"Erro na verificação rápida de coerência: {e}")
            return {"coherence_score": 0.5, "analysis": "Análise indisponível"}

    def _calculate_trend(self) -> str:
        """Calcula tendência de coerência."""
        if len(self._coherence_history) < 5:
            return "insufficient_data"

        recent = [h["coherence_score"] for h in self._coherence_history[-5:]]
        older = [h["coherence_score"] for h in self._coherence_history[-10:-5]]

        if not older:
            return "insufficient_data"

        avg_recent = sum(recent) / len(recent)
        avg_older = sum(older) / len(older)

        if avg_recent > avg_older + 0.05:
            return "improving"
        elif avg_recent < avg_older - 0.05:
            return "declining"
        return "stable"

    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo da coerência observada."""
        if not self._coherence_history:
            return {"observations": 0, "avg_coherence": 0.0, "trend": "no_data"}

        scores = [h["coherence_score"] for h in self._coherence_history]
        return {
            "observations": len(self._coherence_history),
            "avg_coherence": sum(scores) / len(scores),
            "trend": self._calculate_trend(),
            "last_coherence_score": scores[-1] if scores else 0.0,
        }

    def get_coherence_for_evaluator(
        self,
        user_id: str,
        intent_model: Dict[str, Any],
        domain: Optional[str] = None,
    ) -> float:
        """
        Método de conveniência para o Avaliador.

        Retorna apenas o score de coerência para injeção na avaliação.

        Returns:
            float: coherence_score entre 0.0 e 1.0
        """
        result = self.calculate_coherence(
            user_id=user_id,
            intent_model=intent_model,
            timeframe_days=30,
            domain=domain,
        )
        return result.get("coherence_score", 0.5)
