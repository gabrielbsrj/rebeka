# shared/intent/decision_learner.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Implementação de aprendizado via LLM + padrões contextuais
#
# IMPACTO GÊMEO VPS: Aprende com decisões financeiras
# IMPACTO GÊMEO LOCAL: Aprende com decisões pessoais
# DIFERENÇA DE COMPORTAMENTO: Mesmo algoritmo, diferentes domínios

"""
Decision Learner — Aprende valores do usuário por decisões observadas.

INTENÇÃO: Com tempo suficiente, o agente não precisa mais perguntar.
Age a partir do modelo de valores desenvolvido observando
como o usuário decide quando os dados são ambíguos.

IMPLEMENTAÇÃO:
- Usa LLM para extrair valores implícitos das decisões
- Detecta padrões contextuais (quando aceita X, quando rejeita Y)
- Integra com Banco de Causalidade para persistência
- Predição sofisticada baseada em contexto similar

LIMITAÇÃO: O modelo requer volume de decisões para ser confiável.
No início, o agente deve perguntar mais e assumir menos.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple

import litellm

logger = logging.getLogger(__name__)


class DecisionLearner:
    """
    Aprende padrões nos valores do usuário via suas decisões.

    INTENÇÃO: O agente não impõe valores. Ele observa e reflete.
    Se o usuário sempre escolhe segurança sobre retorno, isso é um valor.
    Se o usuário aceita mais risco quando está confiante, isso é um padrão.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        causal_bank=None,
        min_decisions_for_prediction: int = 10,
    ):
        """
        Args:
            model: Modelo LLM para análise de decisões
            api_key: API key do provedor
            causal_bank: Referência ao Banco de Causalidade
            min_decisions_for_prediction: Mínimo de decisões para prever
        """
        self._model = model
        self._api_key = api_key
        self._causal_bank = causal_bank
        self._min_decisions = min_decisions_for_prediction
        
        self._decisions: List[Dict] = []
        self._value_patterns: Dict[str, Any] = {}
        self._contextual_patterns: Dict[str, List[Dict]] = {}
        self._inferred_values: List[Dict] = []

    def record_decision(
        self,
        decision: Dict[str, Any],
        extract_values: bool = True,
    ) -> Dict[str, Any]:
        """
        Registra uma decisão observada.

        INTENÇÃO: Cada decisão é um ponto de dado sobre valores reais.
        O contexto é tão importante quanto a decisão em si.

        Args:
            decision: Dict com decision_type, context, outcome, domain
            extract_values: Se True, usa LLM para extrair valores implícitos

        Returns:
            Dict com registered=True e valores extraídos (se aplicável)
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "decision_type": decision.get("decision_type", "unknown"),
            "context": decision.get("context", {}),
            "domain": decision.get("domain", "general"),
            "chosen_option": decision.get("chosen_option"),
            "rejected_options": decision.get("rejected_options", []),
            "reasoning": decision.get("reasoning"),
            "outcome": decision.get("outcome"),
            "confidence": decision.get("confidence", 0.5),
        }
        
        self._decisions.append(entry)
        self._update_patterns(entry)
        
        # Extrair valores implícitos via LLM
        extracted = None
        if extract_values:
            extracted = self._extract_values_from_decision(entry)
            if extracted:
                self._inferred_values.extend(extracted.get("values", []))
        
        # Persistir no banco se disponível
        if self._causal_bank:
            self._persist_decision(entry)
        
        logger.info(
            f"Decisão registrada: {entry['decision_type']} em {entry['domain']}",
            extra={"total_decisions": len(self._decisions)},
        )
        
        return {
            "registered": True,
            "total_decisions": len(self._decisions),
            "can_predict": self.can_predict(),
            "extracted_values": extracted,
        }

    def _update_patterns(self, decision: Dict):
        """Atualiza padrões de valor com base na nova decisão."""
        decision_type = decision.get("decision_type", "unknown")
        domain = decision.get("domain", "general")
        
        # Padrão por tipo
        key_type = f"tendency_{decision_type}"
        self._value_patterns[key_type] = self._value_patterns.get(key_type, 0) + 1
        
        # Padrão por domínio
        key_domain = f"domain_{domain}"
        self._value_patterns[key_domain] = self._value_patterns.get(key_domain, 0) + 1
        
        # Padrão contextual
        context_key = self._get_context_key(decision)
        if context_key not in self._contextual_patterns:
            self._contextual_patterns[context_key] = []
        self._contextual_patterns[context_key].append({
            "decision_type": decision_type,
            "chosen": decision.get("chosen_option"),
            "timestamp": decision.get("timestamp"),
        })

    def _get_context_key(self, decision: Dict) -> str:
        """Gera chave de contexto para agrupar decisões similares."""
        domain = decision.get("domain", "general")
        context = decision.get("context", {})
        
        # Fatores contextuais relevantes
        risk_level = context.get("risk_level", "unknown")
        urgency = context.get("urgency", "unknown")
        
        return f"{domain}_{risk_level}_{urgency}"

    def _extract_values_from_decision(self, decision: Dict) -> Optional[Dict]:
        """Usa LLM para extrair valores implícitos de uma decisão."""
        
        system_prompt = """Você é um analista de valores humanos.

Dada uma decisão que uma pessoa tomou, identifique que valores implícitos
essa decisão revela sobre a pessoa.

Responda em JSON:
{
    "values": [
        {
            "value": "descrição do valor",
            "confidence": 0.0-1.0,
            "evidence": "evidência na decisão",
            "category": "risk|growth|security|autonomy|relationship|..."
        }
    ],
    "decision_style": "conservative|moderate|aggressive|situational",
    "context_sensitivity": "high|medium|low"
}"""

        user_prompt = f"""## DECISÃO
Tipo: {decision.get('decision_type')}
Domínio: {decision.get('domain')}
Opção escolhida: {decision.get('chosen_option')}
Opções rejeitadas: {decision.get('rejected_options', [])}
Raciocínio: {decision.get('reasoning', 'Não informado')}
Resultado: {decision.get('outcome', 'Pendente')}
Contexto: {decision.get('context', {})}

Que valores essa decisão revela sobre a pessoa?"""

        try:
            response = litellm.completion(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                api_key=self._api_key,
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            result = json.loads(raw)
            
            return result

        except Exception as e:
            logger.warning(f"Erro ao extrair valores: {e}")
            return None

    def _persist_decision(self, decision: Dict):
        """Persiste decisão no Banco de Causalidade."""
        try:
            self._causal_bank.insert_user_decision(decision)
        except Exception as e:
            logger.warning(f"Erro ao persistir decisão: {e}")

    def can_predict(self) -> bool:
        """
        Verifica se temos dados suficientes para prever.

        INTENÇÃO: Nunca assumir valores antes de ter evidência suficiente.
        """
        return len(self._decisions) >= self._min_decisions

    def get_value_profile(self) -> Dict[str, Any]:
        """
        Retorna o perfil de valores observado.

        INTENÇÃO: Este perfil é o que o Motor de Intenção usa para
        informar o Planejador sobre o que o usuário realmente valoriza.
        """
        total = len(self._decisions) or 1
        
        # Taxas básicas
        accept_rate = self._value_patterns.get("tendency_accept", 0) / total
        reject_rate = self._value_patterns.get("tendency_reject", 0) / total
        modify_rate = self._value_patterns.get("tendency_modify", 0) / total
        
        # Dominância por domínio
        domain_distribution = {}
        for key, count in self._value_patterns.items():
            if key.startswith("domain_"):
                domain_distribution[key.replace("domain_", "")] = count / total
        
        # Valores inferidos mais confiáveis
        top_inferred = sorted(
            self._inferred_values,
            key=lambda v: v.get("confidence", 0),
            reverse=True
        )[:5]
        
        return {
            "total_decisions_observed": len(self._decisions),
            "can_predict": self.can_predict(),
            "accept_rate": accept_rate,
            "reject_rate": reject_rate,
            "modify_rate": modify_rate,
            "domain_distribution": domain_distribution,
            "inferred_values": top_inferred,
            "patterns": self._value_patterns,
        }

    def predict_decision(self, context: Dict[str, Any]) -> Optional[Dict]:
        """
        Prevê a decisão do usuário com base no modelo.

        INTENÇÃO: Quando o modelo é confiável, o agente pode agir
        sem perguntar — respeitando os valores observados.

        Args:
            context: Dict com domain, risk_level, urgency, options

        Returns:
            None se dados insuficientes para previsão.
            Dict com predicted_action, confidence, reasoning
        """
        if not self.can_predict():
            return None
        
        # Buscar decisões em contexto similar
        context_key = self._get_context_key({"domain": context.get("domain"), "context": context})
        similar_decisions = self._contextual_patterns.get(context_key, [])
        
        if len(similar_decisions) >= 3:
            # Predição baseada em contexto similar
            return self._predict_from_context(similar_decisions, context)
        
        # Fallback: predição baseada em perfil geral
        return self._predict_from_profile(context)

    def _predict_from_context(
        self,
        similar_decisions: List[Dict],
        context: Dict,
    ) -> Dict:
        """Prevê baseado em decisões em contexto similar."""
        
        # Contar escolhas
        choices = {}
        for d in similar_decisions:
            chosen = d.get("chosen")
            if chosen:
                choices[chosen] = choices.get(chosen, 0) + 1
        
        if not choices:
            return {"predicted_action": "ask_user", "confidence": 0.0}
        
        # Escolha mais comum
        most_common = max(choices, key=choices.get)
        confidence = choices[most_common] / len(similar_decisions)
        
        return {
            "predicted_action": most_common,
            "confidence": confidence,
            "reasoning": f"Baseado em {len(similar_decisions)} decisões similares",
            "source": "context_pattern",
        }

    def _predict_from_profile(self, context: Dict) -> Dict:
        """Prevê baseado no perfil geral de valores."""
        profile = self.get_value_profile()
        
        # Se clara tendência de aceitação
        if profile["accept_rate"] > 0.7:
            return {
                "predicted_action": "accept",
                "confidence": profile["accept_rate"],
                "reasoning": "Usuário tende a aceitar propostas",
                "source": "profile_tendency",
            }
        
        # Se clara tendência de rejeição
        if profile["reject_rate"] > 0.7:
            return {
                "predicted_action": "reject",
                "confidence": profile["reject_rate"],
                "reasoning": "Usuário tende a rejeitar propostas",
                "source": "profile_tendency",
            }
        
        # Análise LLM para contexto específico
        return self._predict_with_llm(context, profile)

    def _predict_with_llm(self, context: Dict, profile: Dict) -> Dict:
        """Usa LLM para prever decisão baseado em perfil e contexto."""
        
        system_prompt = """Você é um modelo preditor de decisões humanas.

Dado o perfil de valores de uma pessoa e um contexto de decisão,
preveja o que ela provavelmente faria.

Responda em JSON:
{
    "predicted_action": "accept|reject|modify|ask_user",
    "confidence": 0.0-1.0,
    "reasoning": "explicação baseada no perfil",
    "alternative": "ação alternativa se não tiver certeza"
}"""

        profile_text = f"""
Taxa de aceitação: {profile['accept_rate']:.1%}
Taxa de rejeição: {profile['reject_rate']:.1%}
Total de decisões observadas: {profile['total_decisions_observed']}
Valores inferidos: {[v['value'] for v in profile.get('inferred_values', [])]}
"""

        user_prompt = f"""## PERFIL DO USUÁRIO
{profile_text}

## CONTEXTO DA DECISÃO
Domínio: {context.get('domain', 'general')}
Risco: {context.get('risk_level', 'unknown')}
Urgência: {context.get('urgency', 'unknown')}
Opções: {context.get('options', [])}

O que o usuário provavelmente faria?"""

        try:
            response = litellm.completion(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                api_key=self._api_key,
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            result = json.loads(raw)
            
            return {
                "predicted_action": result.get("predicted_action", "ask_user"),
                "confidence": float(result.get("confidence", 0.3)),
                "reasoning": result.get("reasoning", ""),
                "alternative": result.get("alternative"),
                "source": "llm_prediction",
            }

        except Exception as e:
            logger.warning(f"Erro na predição LLM: {e}")
            return {
                "predicted_action": "ask_user",
                "confidence": 0.0,
                "reasoning": f"Erro na análise: {e}",
                "source": "fallback",
            }

    def get_decisions_by_domain(self, domain: str) -> List[Dict]:
        """Retorna todas as decisões de um domínio."""
        return [d for d in self._decisions if d.get("domain") == domain]

    def get_recent_decisions(self, days: int = 30) -> List[Dict]:
        """Retorna decisões dos últimos N dias."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        recent = []
        for d in self._decisions:
            try:
                ts = datetime.fromisoformat(d["timestamp"])
                if ts >= cutoff:
                    recent.append(d)
            except:
                pass
        
        return recent

    def get_decision_style(self) -> Dict[str, Any]:
        """
        Analisa o estilo de decisão do usuário.

        Returns:
            Dict com style, risk_tolerance, consistency
        """
        if len(self._decisions) < 5:
            return {"style": "unknown", "confidence": 0.0}
        
        profile = self.get_value_profile()
        
        # Determinar estilo
        if profile["accept_rate"] > 0.6:
            style = "trusting"
        elif profile["reject_rate"] > 0.6:
            style = "conservative"
        elif profile["modify_rate"] > 0.3:
            style = "deliberative"
        else:
            style = "situational"
        
        # Calcular consistência
        domain_concentration = max(profile["domain_distribution"].values()) if profile["domain_distribution"] else 0
        consistency = domain_concentration if domain_concentration > 0.5 else 0.5
        
        return {
            "style": style,
            "consistency": consistency,
            "accept_rate": profile["accept_rate"],
            "reject_rate": profile["reject_rate"],
            "modify_rate": profile["modify_rate"],
        }

    def clear_old_decisions(self, days: int = 365):
        """
        Remove decisões muito antigas.

        INTENÇÃO: Padrões mudam com o tempo. Decisões de 2 anos atrás
        podem não refletir valores atuais.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        
        original_count = len(self._decisions)
        self._decisions = [
            d for d in self._decisions
            if datetime.fromisoformat(d["timestamp"]) >= cutoff
        ]
        
        removed = original_count - len(self._decisions)
        if removed > 0:
            logger.info(f"Removidas {removed} decisões antigas")
        
        return removed
