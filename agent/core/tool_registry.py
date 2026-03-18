# agent/shared/core/tool_registry.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — registro de ferramentas para a LLM

from typing import Dict, Any, List, Callable

class ToolRegistry:
    """
    Registro Central de Ferramentas.
    Define o que a Rebeka pode fazer no mundo físico/digital.
    """
    
    def __init__(self):
        self.tools = {}

    def register_tool(self, name: str, description: str, parameters: Dict[str, Any]):
        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters
        }

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Retorna as definições no formato compatível com OpenAI/Kimi function calling."""
        return [
            {
                "type": "function",
                "function": tool
            } for tool in self.tools.values()
        ]

# Instância global e registro de ferramentas padrão
registry = ToolRegistry()

registry.register_tool(
    "create_project",
    "DELEGA a criação de um projeto/aplicação complexa para um Agente de IA específico (como Cursor ou Antigravity). O sistema prepara o diretório e as instruções contextuais para a IA geratriz.",
    {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Nome do projeto ou pasta destino."},
            "type": {"type": "string", "description": "Stack tecnológica pretendida (ex: react, nextjs, fastapi)."},
            "description": {"type": "string", "description": "Descrição funcional completa do que o agente delegado deve programar."},
            "ai_agent": {"type": "string", "description": "IDE ou Agente de IA a delegar o código (ex: antigravity, cursor, aider).", "default": "antigravity"},
            "model": {"type": "string", "description": "Modelo de linguagem desejado para uso pela IA delegada (ex: claude-3-5-sonnet, gemini-1.5-pro, gpt-4o).", "default": "claude"}
        },
        "required": ["name", "type", "description"]
    }
)

registry.register_tool(
    "run_terminal_command",
    "Executa um comando no terminal do sistema (powershell/cmd). Use para instalar dependências ou rodar scripts de geração.",
    {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "O comando a ser executado."}
        },
        "required": ["command"]
    }
)

registry.register_tool(
    "run_local_tool",
    "Executa qualquer ferramenta local pelo nome, com argumentos arbitrários.",
    {
        "type": "object",
        "properties": {
            "tool_name": {"type": "string", "description": "Nome da ferramenta/método local a executar."},
            "arguments": {"type": "object", "description": "Argumentos para a ferramenta/método."}
        },
        "required": ["tool_name"]
    }
)

registry.register_tool(
    "browser_navigate",
    "Navega para uma URL específica no Google Chrome/Navegador padrão.",
    {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "A URL completa para navegar."}
        },
        "required": ["url"]
    }
)

registry.register_tool(
    "browser_search",
    "Pesquisa no Google por um termo específico.",
    {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "O termo de pesquisa."}
        },
        "required": ["query"]
    }
)

registry.register_tool(
    "desktop_screenshot",
    "Tira uma captura de tela (print) do estado atual do computador.",
    {
        "type": "object",
        "properties": {
            "file_name": {"type": "string", "description": "Nome do arquivo (ex: desktop.png)."}
        }
    }
)

registry.register_tool(
    "desktop_type_text",
    "Digita um texto no teclado do computador na posição atual do cursor.",
    {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "O texto a ser digitado."},
            "interval": {"type": "number", "description": "Intervalo entre teclas em segundos.", "default": 0.1}
        },
        "required": ["text"]
    }
)

registry.register_tool(
    "desktop_hotkey",
    "Executa um atalho de teclado (ex: ctrl+c, alt+tab).",
    {
        "type": "object",
        "properties": {
            "keys": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Lista de teclas para o atalho (ex: ['ctrl', 'c'])."
            }
        },
        "required": ["keys"]
    }
)

registry.register_tool(
    "desktop_click",
    "Clica em uma coordenada (X, Y) na tela ou em um elemento identificado por texto.",
    {
        "type": "object",
        "properties": {
            "x": {"type": "integer"},
            "y": {"type": "integer"},
            "element_text": {"type": "string", "description": "Texto do botão/elemento para clicar."}
        }
    }
)

registry.register_tool(
    "read_code",
    "Lê o conteúdo de um arquivo de código local para análise.",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "O caminho relativo ou absoluto do arquivo."}
        },
        "required": ["file_path"]
    }
)

registry.register_tool(
    "write_code",
    "Cria ou modifica um arquivo de código local.",
    {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "content": {"type": "string"},
            "mode": {"type": "string", "enum": ["write", "append"]}
        },
        "required": ["file_path", "content"]
    }
)
registry.register_tool(
    "open_internal_browser",
    "Abre um navegador interno controlado pela Rebeka para acessar sites (ex: Telegram Web) onde o usuário já está logado.",
    {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "A URL para abrir."},
            "use_persistent_profile": {"type": "boolean", "description": "Se deve usar o perfil do usuário para logins existentes.", "default": True}
        },
        "required": ["url"]
    }
)

registry.register_tool(
    "list_installed_programs",
    "Lista os programas instalados no computador. Pode usar um termo de busca para filtrar a lista.",
    {
        "type": "object",
        "properties": {
            "search_term": {"type": "string", "description": "Termo para filtrar os programas (opcional)."}
        }
    }
)

registry.register_tool(
    "open_program",
    "Abre um programa instalado no computador pelo nome (ex: 'calculadora', 'notepad', 'chrome').",
    {
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "Nome do programa a ser aberto."}
        },
        "required": ["app_name"]
    }
)

registry.register_tool(
    "close_program",
    "Fecha um programa em execução no computador pelo nome do processo (ex: 'calculator', 'notepad', 'chrome'). Use isso para manter o ambiente limpo após finalizar uma tarefa.",
    {
        "type": "object",
        "properties": {
            "process_name": {"type": "string", "description": "Nome do processo (sem .exe) a ser encerrado."}
        },
        "required": ["process_name"]
    }
)

registry.register_tool(
    "google_antigravity_login",
    "Inicia o fluxo de autenticação OAuth2 no navegador para acessar os modelos Google Antigravity (Claude/Gemini). Use esta ferramenta quando o usuário solicitar o uso de modelos do Google ou se as credenciais estiverem expiradas/ausentes.",
    {
        "type": "object",
        "properties": {}
    }
)

registry.register_tool(
    "remember_user_info",
    "SALVA informações pessoais que o usuário revelou sobre si mesmo (nome, hobbies, trabalho, preferências, etc). Use SEMPRE que o usuário mencionar informações pessoais importantes sobre si.",
    {
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Campo da informação (ex: nome, hobby, trabalho, cidade)"},
            "value": {"type": "string", "description": "Valor da informação (ex: Gabriel, música, desenvolvedor, São Paulo)"}
        },
        "required": ["key", "value"]
    }
)

registry.register_tool(
    "list_directory",
    "Lista arquivos e pastas em um diretório. Use para encontrar pastas no Desktop ou qualquer outro local.",
    {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Caminho do diretório (ex: C:\\Users\\Aridelson\\Desktop ou simplemente Desktop para área de trabalho)"}
        },
        "required": ["path"]
    }
)

registry.register_tool(
    "find_file",
    "Procura por arquivos ou pastas que contenham um nome específico. Busca recursivamente em um diretório.",
    {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Nome ou parte do nome a procurar (ex: 'Mercado', 'relatorio')"},
            "path": {"type": "string", "description": "Diretório inicial da busca (ex: Desktop)"}
        },
        "required": ["name"]
    }
)

registry.register_tool(
    "improve_whatsapp_system",
    "Melhora o sistema de automação do WhatsApp para evitar banimento. Adiciona delays seguros, limites de mensagens, rotação de mensagens, etc.",
    {
        "type": "object",
        "properties": {
            "folder_path": {"type": "string", "description": "Caminho da pasta do sistema (ex: Desktop/mercado_livre)"}
        },
        "required": ["folder_path"]
    }
)

registry.register_tool(
    "request_antigravity_service",
    "SOLICITA auxílio avançado ao Antigravity (IA Superior) quando você encontrar uma limitação técnica (ex: ler PDF, formatar vídeo, criar script complexo). O Antigravity resolverá o problema e devolverá o resultado ou a nova ferramenta pronta para você usar.",
    {
        "type": "object",
        "properties": {
            "problem_description": {"type": "string", "description": "Descrição detalhada do obstáculo ou ferramenta que você precisa."},
            "context": {"type": "string", "description": "Dados ou caminhos de arquivos relevantes para o problema."}
        },
        "required": ["problem_description"]
    }
)

registry.register_tool(
    "add_whatsapp_monitoring",
    "Adiciona sistema de monitoramento ao WhatsApp: retry com backoff, cooldown automático, verificação de grupo, alertas de banimento.",
    {
        "type": "object",
        "properties": {
            "folder_path": {"type": "string", "description": "Caminho da pasta do sistema"}
        },
        "required": ["folder_path"]
    }
)

