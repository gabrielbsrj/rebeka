# agent/sync/synthesis_engine.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — emergência de terceira perspectiva

import logging
from typing import Dict, Any, List, Optional
from litellm import completion
import json

logger = logging.getLogger(__name__)

class SynthesisEngine:
    """
    Synthesis Engine — Onde a tensão vira sabedoria.
    
    INTENÇÃO: Quando os gêmeos divergem, não escolhemos um lado.
    Criamos uma terceira perspectiva que integra os dois contextos.
    """

    def __init__(self, model_name: str = "gpt-4-turbo-preview"):
        self.model_name = model_name

    def synthesize(
        self, 
        vps_view: Dict[str, Any], 
        local_view: Dict[str, Any], 
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Tenta sintetizar duas perspectivas divergentes.
        """
        prompt = f"""
        Você é o Synthesis Engine de um sistema de Gêmeos Idênticos.
        Duas instâncias do mesmo agente chegaram a conclusões diferentes devido a seus contextos.

        PERSPECTIVA VPS (Visão Global/Macro):
        {json.dumps(vps_view, indent=2)}

        PERSPECTIVA LOCAL (Visão Íntima/Usuário):
        {json.dumps(local_view, indent=2)}

        CONTEXTO ADICIONAL:
        {json.dumps(context or {}, indent=2)}

        TAREFA:
        1. Identifique a raiz da divergência (Divergence Root).
        2. Não escolha um lado. Crie uma TERCEIRA PERSPECTIVA (Síntese) que reconheça a validade
           de ambos os contextos e gere uma recomendação superior.
        3. Se a síntese for impossível, explique exatamente o porquê.

        Responda APENAS em JSON no formato:
        {{
            "synthesis_id": "string",
            "divergence_root": "descrição curta de onde divergem",
            "emergent_perspective": "o raciocínio da nova visão",
            "recommendation": "ação proposta",
            "synthesis_quality": 0.0-1.0,
            "requires_user": bool
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
                "Síntese realizada",
                extra={
                    "divergence_root": result.get("divergence_root"),
                    "quality": result.get("synthesis_quality")
                }
            )
            return result

        except Exception as e:
            logger.error(f"Falha na síntese: {str(e)}")
            return {
                "synthesis_id": "error",
                "divergence_root": "technical_failure",
                "emergent_perspective": f"Erro técnico: {str(e)}",
                "recommendation": "Consultar usuário devido a erro no Synthesis Engine.",
                "synthesis_quality": 0.0,
                "requires_user": True
            }
