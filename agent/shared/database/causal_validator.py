# shared/database/causal_validator.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — validador de causalidade via LLM e OOS

import logging
from typing import Dict, Any, List, Optional
from litellm import completion
import json

logger = logging.getLogger(__name__)

class CausalValidator:
    """
    Valida se um padrão tem mecanismo causal plausível.

    INTENÇÃO: Evitar agir sobre correlações espúrias. 
    Usa LLM para analisar se existe um "porquê" lógico entre causa e efeito.
    """

    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        self.model_name = model_name

    def validate_pattern(self, cause: str, effect: str, domain: str) -> Dict[str, Any]:
        """
        Analisa a relação entre causa e efeito.

        Returns:
            Dict com 'is_plausible', 'mechanism' e 'confidence'.
        """
        prompt = f"""
        Analise a seguinte relação causal no domínio: {domain}

        Causa: {cause}
        Efeito: {effect}

        Tarefa:
        1. Determine se existe um mecanismo causal plausível que explique como a causa gera o efeito.
        2. Descreva este mecanismo de forma concisa.
        3. Atribua um nível de confiança (0.0 a 1.0) na relação.

        Responda APENAS em JSON no formato:
        {{
            "is_plausible": bool,
            "mechanism": "string explicando o porquê",
            "confidence": float
        }}
        """

        try:
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            
            logger.info(
                "Padrão validado causalmente",
                extra={
                    "domain": domain,
                    "is_plausible": result.get("is_plausible"),
                    "confidence": result.get("confidence")
                }
            )
            return result

        except Exception as e:
            logger.error(f"Erro na validação causal: {str(e)}")
            return {
                "is_plausible": False,
                "mechanism": f"Erro na validação: {str(e)}",
                "confidence": 0.0
            }

    def validate_out_of_sample(self, pattern_id: str, historical_data: List[Dict]) -> bool:
        """
        Valida se o padrão se sustenta em dados que não foram usados para descobri-lo.
        
        INTENÇÃO: Rigor estatístico contra overfitting de regime. Usa LLM para analisar 
        se a regra ou mecanismo se aplica aos novos eventos (out-of-sample).
        """
        if not historical_data:
            logger.info(f"OOS Validation para '{pattern_id}' abortada: sem dados históricos.")
            return False
            
        prompt = f"""
        Você é um validador causal restrito. O objetivo é testar se um padrão causal
        identificado anteriormente (ID: {pattern_id}) se sustenta num conjunto de dados não vistos (OOS).
        
        Dados Históricos (Amostra):
        {json.dumps(historical_data[:10], ensure_ascii=False, default=str)}
        
        Tarefa:
        Baseado EXCLUSIVAMENTE nos dados acima, verifique se a relação de causa/efeito original do padrão ainda tem aderência ou se ocorre com frequência suficiente para ser estatisticamente válida neste novo set.

        Responda APENAS em JSON no formato exato:
        {{
            "sustained": bool,
            "reasoning": "explicação breve baseada nos dados analisados"
        }}
        """
        
        try:
            response = completion(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)
            
            is_sustained = result.get("sustained", False)
            
            logger.info(
                "Validação Out-of-Sample concluída",
                extra={
                    "pattern_id": pattern_id,
                    "sustained": is_sustained,
                    "reasoning": result.get("reasoning")
                }
            )
            return is_sustained

        except Exception as e:
            logger.error(f"Erro na validação OOS para padrão {pattern_id}: {str(e)}")
            return False
