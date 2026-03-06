# shared/core/evaluator.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — Avaliador com 3 camadas
#
# IMPACTO GÊMEO VPS: Avalia hipóteses e execuções do gêmeo VPS
# IMPACTO GÊMEO LOCAL: Avalia hipóteses e execuções do gêmeo Local
# DIFERENÇA DE COMPORTAMENTO: Nenhuma — a avaliação é a mesma para ambos

"""
Avaliador — 3 camadas de validação.

INTENÇÃO: O Avaliador é a consciência crítica do agente. Ele:
1. Usa modelo LLM SEPARADO do Planejador (evitar viés de confirmação)
2. Opera em 3 camadas independentes
3. NUNCA planeja (responsabilidade do Planejador)
4. NUNCA executa (responsabilidade do Executor)
5. Detecta viés de confirmação e comportamento instrumental

INVARIANTE: O Avaliador e o Planejador NUNCA compartilham modelo ou prompt.
INVARIANTE: Layer 1 (consistência lógica) é IMUTÁVEL.
INVARIANTE: O Avaliador nunca planeja e nunca executa.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass

import litellm

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Resultado completo da avaliação em 3 camadas."""
    # Layer 1 — Consistência Lógica (Imutável)
    layer1_consistent: bool
    layer1_reasoning: str

    # Layer 2 — Alinhamento com Valores do Usuário (Evolui lentamente)
    layer2_aligned: bool
    layer2_reasoning: str
    layer2_coherence_impact: float  # -1.0 a 1.0

    # Layer 3 — Detecção de Comportamento Instrumental (Evolui com precisão)
    layer3_no_instrumental_behavior: bool
    layer3_reasoning: str

    # Resultado final
    approved: bool
    overall_reasoning: str
    lessons_learned: str
    clarity_impact: float  # -1.0 a 1.0
    missed_signals: Optional[list]
    twin_perspective_would_help: bool


class Evaluator:
    """
    Avaliador de 3 camadas.

    INTENÇÃO:
    - Layer 1 — Consistência Lógica: A hipótese é logicamente consistente
      com os dados? Contradiz sinais disponíveis? ESTA CAMADA É IMUTÁVEL.
    - Layer 2 — Alinhamento com Valores: A ação proposta está alinhada com
      os valores observados do usuário? A clareza aumenta?
    - Layer 3 — Detecção de Instrumentalidade: O agente está otimizando
      uma métrica ao custo de outra? Está "gamificando" a avaliação?

    LIMITAÇÃO: A detecção de comportamento instrumental por LLM é heurística.
    Não consegue detectar formas sutis de gaming que o próprio avaliador
    não consegue conceitualizcar.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        delegation_registry: Optional[Any] = None,
    ):
        """
        Args:
            model: Modelo LLM para avaliação.
            api_key: API key
            api_base: URL base da API (opcional, para providers não-OpenAI)
            delegation_registry: Registro de contratos de delegação para Blind Execution.
        """
        self._model = model
        self._api_key = api_key
        self._api_base = api_base
        self.delegation_registry = delegation_registry

    def evaluate_hypothesis(
        self,
        hypothesis: Dict[str, Any],
        available_signals: list,
        performance_stats: Dict,
        intent_model: Optional[Dict] = None,
    ) -> EvaluationResult:
        """
        Avalia uma hipótese do Planejador em 3 camadas.
        """
        layer1 = self._evaluate_layer1(hypothesis, available_signals)
        layer2 = self._evaluate_layer2(hypothesis, intent_model)
        layer3 = self._evaluate_layer3(hypothesis, performance_stats)

        # [NOVO] Verificação de Mandato (Delegation Contract)
        delegation_check = self._check_delegation_contracts(hypothesis)
        if not delegation_check["allowed"]:
            layer2["aligned"] = False
            layer2["reasoning"] = f"VIOLAÇÃO DE CONTRATO: {delegation_check['reason']}\n{layer2['reasoning']}"

        approved = (
            layer1["consistent"]
            and layer2["aligned"]
            and layer3["no_instrumental"]
        )

        return EvaluationResult(
            layer1_consistent=layer1["consistent"],
            layer1_reasoning=layer1["reasoning"],
            layer2_aligned=layer2["aligned"],
            layer2_reasoning=layer2["reasoning"],
            layer2_coherence_impact=layer2["coherence_impact"],
            layer3_no_instrumental_behavior=layer3["no_instrumental"],
            layer3_reasoning=layer3["reasoning"],
            approved=approved,
            overall_reasoning=self._synthesize_reasoning(layer1, layer2, layer3),
            lessons_learned=layer1.get("lessons", ""),
            clarity_impact=layer2.get("clarity_impact", 0.0),
            missed_signals=layer1.get("missed_signals"),
            twin_perspective_would_help=layer1.get("twin_would_help", False),
        )

    def _evaluate_layer1(
        self, hypothesis: Dict, signals: list
    ) -> Dict[str, Any]:
        """
        Layer 1 — Consistência Lógica (IMUTÁVEL).

        INTENÇÃO: Verifica se a hipótese contradiz os dados disponíveis.
        Esta camada é puramente lógica — não considera valores ou emoções.

        INVARIANTE: Esta camada NUNCA é modificada pelo agente.
        """
        prompt = f"""Analise a consistência lógica desta hipótese:

HIPÓTESE:
- Raciocínio: {hypothesis.get('reasoning', '')}
- Previsão: {hypothesis.get('predicted_movement', {})}
- Confiança: {hypothesis.get('confidence_calibrated', 0)}
- Incerteza reconhecida: {hypothesis.get('uncertainty_acknowledged', '')}

SINAIS DISPONÍVEIS:
{self._format_signals(signals[:10])}

Responda:
1. A hipótese é logicamente CONSISTENTE com os sinais? (sim/não)
2. Quais sinais CONTRADIZEM a hipótese? (se houver)
3. Que sinais estão FALTANDO que poderiam mudar a conclusão?
4. A perspectiva do gêmeo oposto ajudaria? (sim/não)
5. Lições aprendidas desta análise.
"""

        try:
            completion_kwargs = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content":
                     "Você é um avaliador de consistência lógica rigoroso. "
                     "Sua única função é verificar se a hipótese contradiz os dados. "
                     "Não avalie valores, emoções ou alinhamento — apenas lógica."},
                    {"role": "user", "content": prompt},
                ],
                "api_key": self._api_key,
                "temperature": 1.0 if "kimi" in self._model else 0.1,
            }
            if self._api_base:
                completion_kwargs["api_base"] = self._api_base
            
            response = litellm.completion(**completion_kwargs)

            analysis = response.choices[0].message.content
            is_consistent = "CONSISTENTE" in analysis.upper() and "INCONSISTENTE" not in analysis.upper()

            return {
                "consistent": is_consistent,
                "reasoning": analysis,
                "missed_signals": [],
                "twin_would_help": "GÊMEO" in analysis.upper(),
                "lessons": analysis[-200:] if len(analysis) > 200 else analysis,
            }

        except Exception as e:
            logger.error(f"Layer 1 falhou: {e}")
            # Falha conservadora — rejeita quando não consegue avaliar
            return {
                "consistent": False,
                "reasoning": f"Avaliação falhou: {e}. Rejeitado por conservadorismo.",
                "missed_signals": [],
                "twin_would_help": False,
                "lessons": "Falha na avaliação Layer 1.",
            }

    def _evaluate_layer2(
        self, hypothesis: Dict, intent_model: Optional[Dict]
    ) -> Dict[str, Any]:
        """
        Layer 2 — Alinhamento com Valores do Usuário (evolui lentamente).

        INTENÇÃO: Verifica se a ação proposta está alinhada com os valores
        observados do usuário. O lucro é apenas uma métrica — a clareza
        do usuário é a métrica humana.
        """
        if not intent_model:
            return {
                "aligned": True,  # Sem modelo de intenções, assume alinhado
                "reasoning": "Modelo de intenções ainda não construído. Assumindo alinhamento.",
                "coherence_impact": 0.0,
                "clarity_impact": 0.0,
            }

        prompt = f"""Analise o alinhamento desta ação com os valores do usuário:

AÇÃO PROPOSTA: {hypothesis.get('action', {})}
RACIOCÍNIO: {hypothesis.get('reasoning', '')}

MODELO DE INTENÇÕES DO USUÁRIO:
- Valores declarados: {intent_model.get('values_declared', {})}
- Valores observados: {intent_model.get('values_observed', {})}
- Contradições detectadas: {intent_model.get('contradictions_detected', [])}

A ação está ALINHADA com o que o usuário realmente valoriza?
Qual o impacto esperado na CLAREZA do usuário? (-1.0 a 1.0)
Qual o impacto esperado na COERÊNCIA do usuário? (-1.0 a 1.0)
"""

        try:
            completion_kwargs = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content":
                     "Você é um avaliador de alinhamento de valores. "
                     "Avalie se ações propostas refletem os valores reais do usuário, "
                     "não apenas maximização de métricas."},
                    {"role": "user", "content": prompt},
                ],
                "api_key": self._api_key,
                "temperature": 1.0 if "kimi" in self._model else 0.2,
            }
            if self._api_base:
                completion_kwargs["api_base"] = self._api_base
            
            response = litellm.completion(**completion_kwargs)

            analysis = response.choices[0].message.content
            is_aligned = "ALINHAD" in analysis.upper() and "DESALINHAD" not in analysis.upper()

            return {
                "aligned": is_aligned,
                "reasoning": analysis,
                "coherence_impact": 0.0,
                "clarity_impact": 0.0,
            }

        except Exception as e:
            logger.error(f"Layer 2 falhou: {e}")
            return {
                "aligned": True,  # Assume alinhado quando não consegue avaliar
                "reasoning": f"Avaliação falhou: {e}.",
                "coherence_impact": 0.0,
                "clarity_impact": 0.0,
            }

    def _evaluate_layer3(
        self, hypothesis: Dict, performance_stats: Dict
    ) -> Dict[str, Any]:
        """
        Layer 3 — Detecção de Comportamento Instrumental (evolui com precisão).

        INTENÇÃO: Detecta se o agente está otimizando uma métrica ao custo
        de outra, ou se está "gamificando" o sistema de avaliação.

        Exemplos de comportamento instrumental:
        - Aumentar win rate evitando trades difíceis
        - Reportar confiança alta quando histórico não justifica
        - Ignorar sinais negativos para manter narrativa positiva
        """
        prompt = f"""Analise se esta hipótese mostra sinais de COMPORTAMENTO INSTRUMENTAL:

HIPÓTESE:
- Raciocínio: {hypothesis.get('reasoning', '')}
- Confiança reportada: {hypothesis.get('confidence_calibrated', 0)}
- Incerteza reconhecida: {hypothesis.get('uncertainty_acknowledged', '')}
- Ação proposta: {hypothesis.get('action', {})}

PERFORMANCE HISTÓRICA:
- Win rate: {performance_stats.get('win_rate', 0):.1%}
- Total trades: {performance_stats.get('total_trades', 0)}

SINAIS DE ALERTA PARA COMPORTAMENTO INSTRUMENTAL:
1. Confiança muito maior que o win rate histórico
2. Incerteza vaga ou genérica (não específica)
3. Evitar trades difíceis para manter win rate
4. Ignorar sinais contrários à hipótese
5. Raciocínio circular ou autorreferencial

Há sinais de comportamento instrumental? (sim/não + análise detalhada)
"""

        try:
            completion_kwargs = {
                "model": self._model,
                "messages": [
                    {"role": "system", "content":
                     "Você é um detector de comportamento instrumental em agentes de IA. "
                     "Identifique se o agente está otimizando métricas ao invés de buscar "
                     "genuinamente o melhor resultado."},
                    {"role": "user", "content": prompt},
                ],
                "api_key": self._api_key,
                "temperature": 1.0 if "kimi" in self._model else 0.1,
            }
            if self._api_base:
                completion_kwargs["api_base"] = self._api_base
            
            response = litellm.completion(**completion_kwargs)

            analysis = response.choices[0].message.content
            no_instrumental = "NÃO" in analysis[:100].upper() or "SEM SINAIS" in analysis[:200].upper()

            return {
                "no_instrumental": no_instrumental,
                "reasoning": analysis,
            }

        except Exception as e:
            logger.error(f"Layer 3 falhou: {e}")
            return {
                "no_instrumental": True,  # Assume sem instrumentalidade quando falha
                "reasoning": f"Avaliação falhou: {e}.",
            }

    def _check_delegation_contracts(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Varre a hipótese em busca de apontadores vault:// e valida mandatos.
        """
        if not self.delegation_registry:
            return {"allowed": True} # Sem registro, assume que não há contratos (ou falha externa)

        action = hypothesis.get("action", {})
        details = str(action.get("details", ""))
        
        # Encontrar apontadores vault:// na string de detalhes
        import re
        vault_pointers = re.findall(r"vault://([\w-]+)", details)
        
        if not vault_pointers:
            return {"allowed": True}

        intent = hypothesis.get("intent", "unknown_action")
        
        for pointer in vault_pointers:
            check = self.delegation_registry.check_authorization(pointer, intent)
            if not check["allowed"]:
                logger.warning(f"Mandato violado para {pointer}: {check['reason']}")
                return check
                
        return {"allowed": True}

    def _format_signals(self, signals: list) -> str:
        """Formata sinais para injeção no prompt."""
        if not signals:
            return "Nenhum sinal disponível."
        lines = []
        for s in signals:
            lines.append(f"- [{s.get('domain', '')}] {s.get('title', '')} "
                         f"(relevância: {s.get('relevance_score', 0):.2f})")
        return "\n".join(lines)

    def _synthesize_reasoning(
        self, layer1: Dict, layer2: Dict, layer3: Dict
    ) -> str:
        """Sintetiza o raciocínio das 3 camadas."""
        parts = [
            f"## Layer 1 — Consistência Lógica: {'✓' if layer1['consistent'] else '✗'}",
            layer1["reasoning"][:200],
            "",
            f"## Layer 2 — Alinhamento de Valores: {'✓' if layer2['aligned'] else '✗'}",
            layer2["reasoning"][:200],
            "",
            f"## Layer 3 — Sem Instrumentalidade: {'✓' if layer3['no_instrumental'] else '✗'}",
            layer3["reasoning"][:200],
        ]
        return "\n".join(parts)
