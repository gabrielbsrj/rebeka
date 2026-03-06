import logging
import json
from typing import Dict, Any, Optional
from shared.communication.chat_manager import ChatManager

logger = logging.getLogger(__name__)

class IdeaDecomposer:
    """
    Transforma uma ideia bruta do usuário em um plano estruturado de execução.
    
    INTENÇÃO: Rebeka não pergunta 'o que exatamente você quer?'. Ela decompõe
    a ideia, cria um plano, e apenas confirma as incertezas críticas com o humano.
    """

    PROMPT_TEMPLATE = """
Dado esta ideia do usuário: {ideia_bruta}
Contexto do usuário: {perfil}
Histórico de projetos: {historico_de_projetos}

Decomponha a ideia da forma mais pragmática possível. Seu objetivo é pensar como uma Engenheira de Software sênior orquestrando a criação deste pedido.

Decomponha em:
1. OBJETIVO CENTRAL — em uma frase, o que essa ideia precisa fazer
2. ENTREGÁVEL FINAL — o que existe no mundo quando isso estiver pronto
3. COMPONENTES — lista das partes que precisam existir para o entregável
4. DEPENDÊNCIAS — o que precisa estar pronto antes de cada componente
5. INCERTEZAS — o que não está claro e precisa ser decidido antes de executar
6. EXECUTOR IDEAL POR COMPONENTE — qual agente/ferramenta é melhor para cada parte
7. SEQUÊNCIA SUGERIDA — ordem de execução com paralelismo onde possível

Para cada componente, especifique:
- id: Ex(C1, C2)
- nome
- executor: (cursor_agent, windsurf_agent, github_copilot, claude_api, gpt4_api, perplexity, n8n_workflow, make_scenario, usuario_humano, colaborador_externo)
- input: O que entra
- output: O que sai
- instrucao_para_executor: Como instruir esse executor
- criterio_de_aceite: Como testar
- dependencias: lista de IDs dos componentes base

Retorne ÚNICA e EXCLUSIVAMENTE um JSON estruturado seguindo exatamente este padrão. Não inclua Markdown, não coloque ```json. Apenas o objeto JSON puro:
{{
  "objetivo_central": "...",
  "entregavel_final": "...",
  "componentes": [
    {{
      "id": "C1",
      "nome": "...",
      "executor": "...",
      "input": "...",
      "output": "...",
      "instrucao_para_executor": "...",
      "criterio_de_aceite": "...",
      "dependencias": []
    }}
  ],
  "sequencia_sugerida": [
    {{"fase": 1, "paralelo": ["C1", "C2"], "nota": "..."}}
  ],
  "incertezas": ["..."]
}}
"""

    def __init__(self, chat_manager: Optional[ChatManager] = None):
        """Inicializa o Decomposer."""
        self.chat_manager = chat_manager or ChatManager()
        # Idealmente forçamos o modelo para um forte em raciocínio JSON
        if hasattr(self.chat_manager, 'switch_model'):
            # Usa o modelo ativo, mas internamente ele tentará usar strong models para isso
            pass

    async def decompose(self, raw_idea: str, user_profile: str = "", project_history: str = "") -> Dict[str, Any]:
        """
        Envia a ideia para o LLM e retorna o JSON estruturado da decomposição.
        """
        logger.info(f"Decompondo ideia: {raw_idea[:50]}...")
        
        prompt = self.PROMPT_TEMPLATE.format(
            ideia_bruta=raw_idea,
            perfil=user_profile or "Perfil não fornecido.",
            historico_de_projetos=project_history or "Nenhum histórico disponível."
        )

        try:
            # Chama o LLM (bypass normal de chat, enviando mensagem direta de sistema)
            response_data = await self.chat_manager.get_response(
                user_message=prompt,
                system_instruction="Você é a Orquestradora Rebeka v5.0. Retorne apenas JSON válido."
            )
            
            content = response_data.get("content", "").strip()
            
            # Limpa blockcodes se o LLM tiver teimado em enviar
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
                
            content = content.strip()
            
            plan_json = json.loads(content)
            logger.info(f"Ideia decomposta em {len(plan_json.get('componentes', []))} componentes.")
            return plan_json
            
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao converter decomposição para JSON: {e}\nRetorno do LLM: {content}")
            raise Exception("Falha na formatação da decomposição gerada pelo LLM.")
        except Exception as e:
            logger.error(f"Erro no módulo de decomposição: {e}")
            raise
