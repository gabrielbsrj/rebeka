# shared/intent/ambiguity_resolver.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-21
# CHANGELOG: Implementação de _resolve_from_intents via LLM
#
# IMPACTO GÊMEO VPS: Resolve ambiguidades em decisões financeiras
# IMPACTO GÊMEO LOCAL: Resolve ambiguidades em contexto pessoal
# DIFERENÇA DE COMPORTAMENTO: Mesma lógica, diferentes fontes de dados

"""
Ambiguity Resolver — Resolve situações ambíguas via intenções + LLM.

INTENÇÃO: Quando os dados são insuficientes para uma decisão clara,
o resolver consulta o modelo de intenções do usuário e,
se necessário, pergunta ao usuário diretamente.

IMPLEMENTAÇÃO:
- _resolve_from_intents: analisa situação vs valores declarados via LLM
- Hierarquia: intenções → histórico → LLM → usuário

INVARIANTE: Nunca assume quando pode perguntar.
"""

import json
import logging
from typing import Dict, Any, Optional, List

import litellm

logger = logging.getLogger(__name__)


class AmbiguityResolver:
    """
    Resolve situações ambíguas consultando intenções e LLM.

    INTENÇÃO: Em vez de adivinhar, o agente reconhece quando não sabe
    e busca clareza — primeiro no modelo de intenções, depois no histórico,
    e como último recurso, pergunta ao usuário.
    """

    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        self._model = model
        self._api_key = api_key

    def resolve(
        self,
        situation: str,
        options: List[Dict[str, Any]],
        intent_model: Optional[Dict] = None,
        historical_decisions: Optional[List[Dict]] = None,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Tenta resolver uma ambiguidade.

        INTENÇÃO: Hierarquia de resolução:
        1. Modelo de intenções (se disponível e confiante)
        2. Decisões históricas similares
        3. Análise LLM com contexto
        4. Pergunta ao usuário (último recurso)

        Args:
            situation: Descrição da situação ambígua
            options: Lista de opções disponíveis (cada uma é um dict)
            intent_model: Modelo de intenções/valores do usuário
            historical_decisions: Decisões similares no passado
            context: Contexto adicional (domain, urgency, etc.)

        Returns:
            Dict com resolved, recommended_option, confidence, reasoning, ask_user
        """
        if not options:
            return {
                "resolved": False,
                "recommended_option": None,
                "confidence": 0.0,
                "reasoning": "Nenhuma opção disponível para resolver.",
                "source": "no_options",
                "ask_user": True,
            }

        # Tentativa 1: Resolver via modelo de intenções
        if intent_model:
            intent_resolution = self._resolve_from_intents(
                situation, options, intent_model, context
            )
            if intent_resolution.get("confidence", 0) >= 0.6:
                logger.info(f"Ambiguidade resolvida via intenções: {intent_resolution.get('recommended_option')}")
                return intent_resolution

        # Tentativa 2: Usar histórico de decisões
        if historical_decisions and len(historical_decisions) >= 3:
            history_resolution = self._resolve_from_history(
                situation, options, historical_decisions
            )
            if history_resolution.get("confidence", 0) >= 0.5:
                logger.info(f"Ambiguidade resolvida via histórico: {history_resolution.get('recommended_option')}")
                return history_resolution

        # Tentativa 3: Análise LLM com contexto completo
        llm_resolution = self._resolve_with_llm(
            situation, options, intent_model, historical_decisions, context
        )
        
        return llm_resolution

    def _resolve_from_intents(
        self,
        situation: str,
        options: List[Dict],
        intent_model: Dict,
        context: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Tenta resolver usando o modelo de intenções do usuário.

        INTENÇÃO: Compara cada opção com os valores declarados e
        retorna a mais alinhada. Usa LLM para análise semântica.

        Returns:
            Dict com resolved, recommended_option, confidence, reasoning
        """
        if not intent_model:
            return self._fallback_result("Modelo de intenções vazio")

        # Extrair valores relevantes
        declared_values = self._extract_relevant_values(intent_model, situation)
        
        if not declared_values:
            return self._fallback_result("Nenhum valor relevante encontrado")

        # Preparar prompt para análise
        system_prompt = """Você é um resolvedor de ambiguidades que respeita os valores do usuário.

Sua tarefa é analisar uma situação ambígua e recomendar a opção mais alinhada 
com os valores declarados do usuário.

Responda em JSON:
{
    "recommended_index": 0-N (índice da opção recomendada),
    "confidence": 0.0-1.0,
    "reasoning": "explicação de por que esta opção está mais alinhada",
    "values_aligned": ["valores que esta opção respeita"],
    "values_conflicted": ["valores que esta opção pode conflitar"],
    "ask_user": true/false (true se confiança < 0.5 ou conflito significativo)
}

Critérios:
- confidence >= 0.7: clara alinhamento com valores
- confidence 0.5-0.7: alinhamento parcial
- confidence < 0.5: incerteza, recomende perguntar ao usuário
- Se houver conflito significativo com valores importantes, ask_user = true"""

        # Construir contexto
        options_text = "\n".join([
            f"[{i}] {opt.get('name', opt.get('description', str(opt)))}"
            for i, opt in enumerate(options)
        ])

        values_text = "\n".join([
            f"- {v.get('value', v)} (prioridade: {v.get('priority', 'média')})"
            for v in declared_values[:10]
        ])

        user_prompt = f"""## SITUAÇÃO
{situation}

## VALORES DECLARADOS DO USUÁRIO
{values_text}

## OPÇÕES DISPONÍVEIS
{options_text}

## CONTEXTO ADICIONAL
{context or 'Nenhum'}

Analise e recomende a opção mais alinhada com os valores do usuário."""

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

            recommended_idx = result.get("recommended_index", 0)
            confidence = float(result.get("confidence", 0.0))
            ask_user = result.get("ask_user", confidence < 0.5)

            # Validar índice
            if 0 <= recommended_idx < len(options):
                recommended = options[recommended_idx]
            else:
                recommended = options[0] if options else None
                confidence = 0.3
                ask_user = True

            return {
                "resolved": not ask_user and confidence >= 0.5,
                "recommended_option": recommended,
                "recommended_index": recommended_idx,
                "confidence": confidence,
                "reasoning": result.get("reasoning", ""),
                "values_aligned": result.get("values_aligned", []),
                "values_conflicted": result.get("values_conflicted", []),
                "source": "intent_model",
                "ask_user": ask_user,
            }

        except Exception as e:
            logger.error(f"Erro na resolução por intenções: {e}")
            return self._fallback_result(f"Erro na análise: {e}")

    def _resolve_from_history(
        self,
        situation: str,
        options: List[Dict],
        historical_decisions: List[Dict],
    ) -> Dict[str, Any]:
        """
        Tenta resolver baseado em decisões históricas similares.

        INTENÇÃO: Se o usuário fez decisões similares no passado,
        usa padrões anteriores como guia.
        """
        # Preparar análise via LLM
        system_prompt = """Você é um analisador de padrões de decisão.

Dada uma situação atual e um histórico de decisões similares do usuário,
determine qual opção o usuário provavelmente escolheria baseado no padrão.

Responda em JSON:
{
    "recommended_index": 0-N,
    "confidence": 0.0-1.0,
    "reasoning": "explicação baseada no padrão histórico",
    "pattern_detected": "descrição do padrão identificado"
}"""

        history_text = "\n".join([
            f"- {d.get('description', d.get('situation', 'Decisão'))} → Escolheu: {d.get('chosen_option', d.get('choice', 'N/A'))}"
            for d in historical_decisions[:10]
        ])

        options_text = "\n".join([
            f"[{i}] {opt.get('name', opt.get('description', str(opt)))}"
            for i, opt in enumerate(options)
        ])

        user_prompt = f"""## SITUAÇÃO ATUAL
{situation}

## DECISÕES SIMILARES NO PASSADO
{history_text}

## OPÇÕES ATUAIS
{options_text}

Baseado no padrão histórico, qual opção o usuário provavelmente escolheria?"""

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

            recommended_idx = result.get("recommended_index", 0)
            confidence = float(result.get("confidence", 0.0))

            if 0 <= recommended_idx < len(options):
                recommended = options[recommended_idx]
            else:
                recommended = options[0] if options else None
                confidence = min(confidence, 0.3)

            return {
                "resolved": confidence >= 0.5,
                "recommended_option": recommended,
                "recommended_index": recommended_idx,
                "confidence": confidence,
                "reasoning": result.get("reasoning", ""),
                "pattern_detected": result.get("pattern_detected", ""),
                "source": "historical_pattern",
                "ask_user": confidence < 0.5,
            }

        except Exception as e:
            logger.error(f"Erro na resolução por histórico: {e}")
            return self._fallback_result(f"Erro na análise histórica: {e}")

    def _resolve_with_llm(
        self,
        situation: str,
        options: List[Dict],
        intent_model: Optional[Dict],
        historical_decisions: Optional[List[Dict]],
        context: Optional[Dict],
    ) -> Dict[str, Any]:
        """
        Análise LLM completa quando outras fontes não foram suficientes.

        INTENÇÃO: Último recurso antes de perguntar ao usuário.
        """
        system_prompt = """Você é um assistente que resolve ambiguidades.

Analise a situação, considere todas as informações disponíveis e recomende
a melhor opção. Se não houver informações suficientes, recomende perguntar.

Responda em JSON:
{
    "recommended_index": 0-N ou -1 se deve perguntar,
    "confidence": 0.0-1.0,
    "reasoning": "explicação completa",
    "ask_user": true/false,
    "clarifying_questions": ["perguntas que ajudariam a decidir"]
}"""

        # Construir contexto completo
        context_parts = [f"## SITUAÇÃO\n{situation}\n"]

        if intent_model:
            values = intent_model.get("declared_values", [])
            if values:
                context_parts.append("## VALORES DO USUÁRIO\n")
                for v in values[:5]:
                    context_parts.append(f"- {v.get('value', v)}\n")

        if historical_decisions:
            context_parts.append("## DECISÕES ANTERIORES\n")
            for d in historical_decisions[:5]:
                context_parts.append(f"- {d.get('description', 'Decisão')}\n")

        if context:
            context_parts.append(f"## CONTEXTO\n{context}\n")

        options_text = "\n".join([
            f"[{i}] {opt.get('name', opt.get('description', str(opt)))}"
            for i, opt in enumerate(options)
        ])
        context_parts.append(f"## OPÇÕES\n{options_text}")

        try:
            response = litellm.completion(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": "\n".join(context_parts)},
                ],
                api_key=self._api_key,
                temperature=0.3,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content
            result = json.loads(raw)

            recommended_idx = result.get("recommended_index", -1)
            confidence = float(result.get("confidence", 0.0))
            ask_user = result.get("ask_user", confidence < 0.4)

            if ask_user or recommended_idx < 0 or recommended_idx >= len(options):
                return {
                    "resolved": False,
                    "recommended_option": None,
                    "confidence": confidence,
                    "reasoning": result.get("reasoning", "Informações insuficientes para decidir automaticamente."),
                    "source": "llm_analysis",
                    "ask_user": True,
                    "clarifying_questions": result.get("clarifying_questions", []),
                }

            return {
                "resolved": not ask_user,
                "recommended_option": options[recommended_idx],
                "recommended_index": recommended_idx,
                "confidence": confidence,
                "reasoning": result.get("reasoning", ""),
                "source": "llm_analysis",
                "ask_user": ask_user,
                "clarifying_questions": result.get("clarifying_questions", []),
            }

        except Exception as e:
            logger.error(f"Erro na análise LLM: {e}")
            return {
                "resolved": False,
                "recommended_option": None,
                "confidence": 0.0,
                "reasoning": f"Erro na análise: {e}",
                "source": "error",
                "ask_user": True,
            }

    def _extract_relevant_values(
        self,
        intent_model: Dict,
        situation: str,
    ) -> List[Dict]:
        """
        Extrai valores relevantes do modelo de intenções para a situação.
        """
        values = []

        # Valores declarados explicitamente
        if "declared_values" in intent_model:
            values.extend(intent_model["declared_values"])

        # Intenções extraídas de regras
        if "intentions" in intent_model:
            for path, intent in intent_model["intentions"].items():
                values.append({
                    "value": intent.get("intention", ""),
                    "source": "rule",
                    "rule_path": path,
                })

        # Valores inferidos
        if "inferred_values" in intent_model:
            for v in intent_model["inferred_values"]:
                if v.get("confidence", 0) >= 0.5:
                    values.append(v)

        return values

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        """Resultado padrão quando não consegue resolver."""
        return {
            "resolved": False,
            "recommended_option": None,
            "confidence": 0.0,
            "reasoning": reason,
            "source": "fallback",
            "ask_user": True,
        }

    def quick_resolve(
        self,
        situation: str,
        options: List[str],
        user_values: List[str],
    ) -> Dict[str, Any]:
        """
        Método simplificado para resoluções rápidas.

        Útil quando não há tempo para análise completa.

        Args:
            situation: Descrição breve
            options: Lista de strings com opções
            user_values: Lista de valores importantes

        Returns:
            Dict com recommended (string), confidence, reasoning
        """
        if not options:
            return {"recommended": None, "confidence": 0.0, "reasoning": "Sem opções"}

        prompt = f"""Situação: {situation}
Opções: {', '.join(options)}
Valores do usuário: {', '.join(user_values)}

Qual opção é mais alinhada? Responda em JSON:
{{"recommended": "opção", "confidence": 0.0-1.0, "reasoning": "explicação"}}"""

        try:
            response = litellm.completion(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                api_key=self._api_key,
                temperature=0.2,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            return {
                "recommended": result.get("recommended"),
                "confidence": float(result.get("confidence", 0.5)),
                "reasoning": result.get("reasoning", ""),
            }

        except Exception as e:
            logger.warning(f"Quick resolve falhou: {e}")
            return {
                "recommended": options[0] if options else None,
                "confidence": 0.3,
                "reasoning": f"Fallback (erro: {e})",
            }
