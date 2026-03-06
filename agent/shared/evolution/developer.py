# agent/shared/evolution/developer.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — motor de geração de melhorias de código

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class Developer:
    """
    Developer — O construtor de si mesmo.
    
    INTENÇÃO: Propõe mudanças de código (diffs) baseadas 
    em necessidades identificadas pelo Observer.
    
    INVARIANTE: O Developer propõe, o Sandbox/Tester valida.
    Nunca escreve diretamente em produção.
    """

    def __init__(self):
        from shared.core.config_loader import get_model_config
        self.config = get_model_config("developer")

    def propose_improvement(self, target_file: str, issue_description: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Gera uma proposta de melhoria de código baseada em LLM.
        """
        from litellm import completion
        import os

        logger.info(f"Developer gerando proposta para: {target_file}")
        
        # 1. Ler o conteúdo atual do arquivo
        try:
            with open(target_file, "r", encoding="utf-8") as f:
                current_code = f.read()
        except Exception as e:
            return {"error": f"Falha ao ler arquivo alvo: {str(e)}"}

        api_key = os.getenv("MOONSHOT_API_KEY")
        api_base = os.getenv("OPENAI_API_BASE")
        
        # 2. Chamar LLM para propor a mudança
        prompt = f"""
        Você é o módulo 'Developer' da Rebeka. Sua função é evoluir seu próprio código.
        
        ATENÇÃO: Você ainda é considerada 'LEIGA' (iniciante). Não tente mudanças complexas ou arriscadas.
        Seu objetivo não é apenas consertar, mas aprender a manter a robustez.
        
        Arquivo Alvo: {target_file}
        Problema Identificado pelo Observer: {issue_description}
        Métricas de Performance: {metrics}
        
        Código Atual:
        ```python
        {current_code}
        ```
        
        Tarefa:
        Proponha uma modificação no código para resolver o problema. 
        Mantenha o estilo e a filosofia de transcendência (robustez, logs, invariantes).
        
        Responda seguindo este formato EXATO:
        RATIONALE: <explicação curta>
        IMPACT: <análise de impacto>
        CODE:
        ```python
        <CÓDIGO COMPLETO COMPILÁVEL DO ARQUIVO MODIFICADO>
        ```
        """
        
        try:
            response = completion(
                model=self.config["model"],
                messages=[{"role": "user", "content": prompt}],
                api_key=api_key,
                api_base=api_base,
                temperature=self.config["temperature"],
                max_tokens=self.config["max_tokens"]
            )
            content = response.choices[0].message.content
            
            # Parsing manual resiliente
            import re
            rationale_match = re.search(r"RATIONALE:\s*(.*)", content)
            impact_match = re.search(r"IMPACT:\s*(.*)", content)
            code_match = re.search(r"```python\n(.*?)\n```", content, re.DOTALL)
            
            if not code_match:
                return {"error": "LLM não retornou bloco de código válido."}
            
            import uuid
            return {
                "evolution_id": str(uuid.uuid4()),
                "target_file": target_file,
                "rationale": rationale_match.group(1).strip() if rationale_match else "N/A",
                "impact_analysis": impact_match.group(1).strip() if impact_match else "N/A",
                "proposed_content": code_match.group(1).strip()
            }
        except Exception as e:
            logger.error(f"Erro na geração de proposta pelo Developer: {e}")
            return {"error": str(e)}
