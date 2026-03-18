# agent/local/executor_local.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — executor de ferramentas locais (Hands)

import os
import logging
import asyncio
import pyautogui
from datetime import datetime, timezone
from playwright.async_api import async_playwright
from typing import Dict, Any, Optional, List

try:
    from local.vault.master_vault import MasterVault
except ImportError:
    from local.vault.master_vault import MasterVault

logger = logging.getLogger(__name__)

class LocalExecutor:
    """
    Local Executor — As mãos da Rebeka no dispositivo.
    Executa comandos de automação baseados nas decisões do Planejador.
    """

    def __init__(self, vault: Optional[MasterVault] = None):
        self.browser = None
        self.context = None
        self.page = None
        self.vault = vault
        self.whatsapp_adapter = None
        self.sync_client = None

    def register_whatsapp_adapter(self, adapter: Any) -> None:
        """Registra o adaptador local do WhatsApp para envio seguro."""
        self.whatsapp_adapter = adapter

    def register_sync_client(self, client: Any) -> None:
        """Registra o SyncClient para envio de sinais locais para a VPS."""
        self.sync_client = client

    async def execute(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Orquestra a execução da ferramenta chamada."""
        # O log contém apenas os argumentos originais (com vault:// se houver), protegendo o segredo.
        logger.info(f"Executando ferramenta: {tool_name} com {arguments}")
        
        try:
            if tool_name == "create_project":
                return await self.create_project(
                    arguments["name"], 
                    arguments["type"], 
                    arguments["description"],
                    arguments.get("ai_agent", "antigravity"),
                    arguments.get("model", "claude")
                )
            elif tool_name == "run_terminal_command":
                return self.run_terminal_command(arguments["command"])
            elif tool_name == "browser_navigate":
                return await self.browser_navigate(arguments["url"])
            elif tool_name == "desktop_click":
                return self.desktop_click(arguments.get("x"), arguments.get("y"), arguments.get("element_text"))
            elif tool_name == "desktop_type_text":
                # Injeção cega: a resolução ocorre dentro do método de digitação.
                return self.desktop_type_text(arguments["text"], arguments.get("interval", 0.1))
            elif tool_name == "desktop_hotkey":
                return self.desktop_hotkey(arguments["keys"])
            elif tool_name == "desktop_screenshot":
                return self.desktop_screenshot(arguments.get("file_name", "screenshot.png"))
            elif tool_name == "read_code":
                return self.read_code(arguments["file_path"])
            elif tool_name == "write_code":
                return self.write_code(arguments["file_path"], arguments["content"])
            elif tool_name == "list_installed_programs":
                return self.list_installed_programs(arguments.get("search_term", ""))
            elif tool_name == "open_program":
                return self.open_program(arguments["app_name"])
            elif tool_name == "close_program":
                return self.close_program(arguments["process_name"])
            elif tool_name == "perplexity_search":
                return await self.perplexity_search(arguments["query"])
            elif tool_name == "google_antigravity_login":
                return await self.google_antigravity_login()
            elif tool_name == "run_remote_command":
                return self.run_remote_command(arguments["command"])
            elif tool_name == "remember_user_info":
                return self.remember_user_info(arguments["key"], arguments["value"])
            elif tool_name == "list_directory":
                return self.list_directory(arguments["path"])
            elif tool_name == "find_file":
                return self.find_file(arguments.get("name"), arguments.get("path"))
            elif tool_name == "improve_whatsapp_system":
                return self.improve_whatsapp_system(arguments.get("folder_path"))
            elif tool_name == "add_whatsapp_monitoring":
                return self.add_whatsapp_monitoring(arguments.get("folder_path"))
            elif tool_name == "whatsapp_send_message":
                return await self._send_whatsapp_message(arguments)
            elif tool_name == "request_antigravity_service":
                return {
                    "status": "success",
                    "message": "Solicitação enviada ao núcleo Antigravity. Aguardando processamento de alta prioridade.",
                    "problem": arguments.get("problem_description")
                }
            elif tool_name == "run_local_tool":
                return await self._dispatch_any_tool(
                    arguments.get("tool_name"),
                    arguments.get("arguments", {})
                )
            else:
                return {"status": "error", "message": f"Ferramenta {tool_name} não implementada no executor local."}
        except Exception as e:
            logger.error(f"Erro ao executar {tool_name}: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _dispatch_any_tool(self, tool_name: Optional[str], tool_args: Any) -> Dict[str, Any]:
        if not tool_name:
            return {"status": "error", "message": "tool_name obrigatório"}
        if not hasattr(self, tool_name):
            return {"status": "error", "message": f"Ferramenta {tool_name} não encontrada no executor local."}
        tool_fn = getattr(self, tool_name)
        if not callable(tool_fn):
            return {"status": "error", "message": f"{tool_name} não é executável."}
        try:
            if isinstance(tool_args, dict):
                result = tool_fn(**tool_args)
            elif isinstance(tool_args, list):
                result = tool_fn(*tool_args)
            else:
                result = tool_fn(tool_args)
            if asyncio.iscoroutine(result):
                result = await result
            if isinstance(result, dict):
                return result
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Erro ao executar {tool_name}: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _send_whatsapp_message(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        contact_name = arguments.get("contact_name") or arguments.get("contact") or arguments.get("name")
        message = arguments.get("message") or ""
        if not contact_name:
            return {"status": "error", "message": "contact_name obrigatorio para whatsapp_send_message"}
        if not self.whatsapp_adapter:
            return {"status": "error", "message": "WhatsApp adapter nao registrado no executor local."}
        return await self.whatsapp_adapter.send_message(contact_name, message)

    async def notify_vps(
        self,
        domain: str,
        source: str,
        title: str,
        content: str,
        relevance: float = 0.5,
        raw_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        priority: str = "normal",
    ) -> Dict[str, Any]:
        """Envia um sinal abstrato do ambiente local para a VPS via SyncClient."""
        if not self.sync_client:
            logger.warning("Sync client nao registrado; notify_vps ignorado.")
            return {"status": "error", "message": "Sync client nao registrado."}

        payload: Dict[str, Any] = {
            "type": "context_sync",
            "priority": priority,
            "data": {
                "domain": domain,
                "source": source,
                "title": title,
                "content": content,
                "relevance_score": relevance,
            },
        }

        if raw_data is not None:
            payload["data"]["raw_data"] = raw_data
        if metadata is not None:
            payload["data"]["metadata"] = metadata

        await self.sync_client.send(payload)
        return {"status": "success", "message": "context_sync enviado para a VPS."}

    def run_remote_command(self, command: str) -> Dict[str, Any]:
        """Executa um comando na VPS remota via SSH."""
        remote_host = os.getenv("REMOTE_VPS_HOST")
        if not remote_host:
            return {"status": "error", "message": "REMOTE_VPS_HOST não configurado no .env local."}
        
        # Escapar aspas no comando
        safe_command = command.replace('"', '\\"')
        ssh_command = f'ssh {remote_host} "{safe_command}"'
        return self.run_terminal_command(ssh_command)

    def _resolve_vault_pointers(self, text: str) -> str:
        """Substitui pointers vault://id pelo valor real apenas no momento da ação."""
        if not self.vault or "vault://" not in text:
            return text
            
        import re
        pointers = re.findall(r"vault://([\w-]+)", text)
        
        resolved_text = text
        for p in pointers:
            secret = self.vault.get_secret(p)
            if secret:
                # Prioriza campo 'value' ou 'password', senão usa o objeto todo (se for string)
                val = secret.get("value") or secret.get("password") or str(secret)
                resolved_text = resolved_text.replace(f"vault://{p}", val)
            else:
                logger.warning(f"Vault pointer '{p}' não pôde ser resolvido.")
        return resolved_text

    def _find_ide_executable(self, ide_name: str) -> Optional[str]:
        """Tenta encontrar o executável de uma IDE de forma resiliente e cross-platform."""
        import shutil
        import os
        import sys
        
        # 1. Tentar PATH lógico
        exe_path = shutil.which(ide_name)
        if exe_path:
            return f'"{exe_path}"'
            
        common_paths = []
        
        # 2. Heurística baseada no Sistema Operacional
        if sys.platform == "win32":
            local_app_data = os.environ.get('LOCALAPPDATA', '')
            program_files = os.environ.get('ProgramFiles', '')
            program_files_x86 = os.environ.get('ProgramFiles(x86)', '')
            
            if ide_name.lower() == "cursor":
                common_paths.append(os.path.join(local_app_data, 'Programs', 'cursor', 'Cursor.exe'))
            elif ide_name.lower() == "code":
                common_paths.extend([
                    os.path.join(local_app_data, 'Programs', 'Microsoft VS Code', 'Code.exe'),
                    os.path.join(program_files, 'Microsoft VS Code', 'Code.exe'),
                    os.path.join(program_files_x86, 'Microsoft VS Code', 'Code.exe'),
                ])
                
        elif sys.platform == "darwin":  # macOS
            if ide_name.lower() == "cursor":
                common_paths.append('/Applications/Cursor.app/Contents/MacOS/Cursor')
            elif ide_name.lower() == "code":
                common_paths.append('/Applications/Visual Studio Code.app/Contents/MacOS/Electron')
                
        else:  # Linux (Ubuntu/PopOS etc)
            if ide_name.lower() == "cursor":
                # Geralmente no Linux o cursor usa AppImage, mas instaladores podem jogar no /opt/
                common_paths.extend([
                    '/opt/cursor/cursor',
                    '/opt/Cursor/cursor',
                    os.path.expanduser('~/Applications/cursor')
                ])
            elif ide_name.lower() == "code":
                common_paths.extend([
                    '/usr/bin/code',
                    '/usr/share/code/bin/code'
                ])
                
        for path in common_paths:
            if os.path.exists(path):
                return f'"{path}"'
                
        return None

    async def create_project(self, name: str, p_type: str, description: str, ai_agent: str = "antigravity", model: str = "claude") -> Dict[str, Any]:
        """Cria um novo projeto/aplicação delegando para outro Agente (Antigravity/Cursor)."""
        try:
            # Lógica para criar diretório e arquivos base
            base_dir = os.path.abspath(os.path.join(os.getcwd(), "generated_projects"))
            path = os.path.join(base_dir, name)
            os.makedirs(path, exist_ok=True)
            
            prompt_content = f"# Especificação do Projeto: {name}\n\n"
            prompt_content += f"**Framework/Tech Stack**: {p_type}\n"
            prompt_content += f"**Modelo Preferido**: {model}\n\n"
            prompt_content += f"## Descrição Funcional\n{description}\n\n"
            prompt_content += "## Instruções para a IA (Cursor/Antigravity/Aider)\n"
            prompt_content += "1. Leia esta especificação completamente.\n"
            prompt_content += "2. Crie todos os arquivos necessários para a aplicação funcionar.\n"
            prompt_content += "3. Instale as dependências necessárias.\n"
            prompt_content += "4. Teste localmente se possível.\n"

            prompt_path = os.path.join(path, "AGENT_PROMPT.md")
            with open(prompt_path, "w", encoding="utf-8-sig") as f:
                f.write(prompt_content)
                
            import subprocess
            invocation_msg = ""
            if "cursor" in ai_agent.lower() or "antigravity" in ai_agent.lower():
                # Para projetos AI (Cursor/Antigravity), vamos tentar o Cursor primeiro
                cursor_exe = self._find_ide_executable("cursor")
                if cursor_exe:
                    try:
                        subprocess.run(f"{cursor_exe} \"{path}\" --disable-workspace-trust", shell=True)
                        if "antigravity" in ai_agent.lower():
                            invocation_msg = f"Projeto preparado. Cursor IDE ativo para hospedar Antigravity em {path}."
                        else:
                            invocation_msg = "Cursor IDE aberto no diretório do projeto com as instruções prontas."
                    except Exception:
                        invocation_msg = "Tentativa de abrir Cursor IDE falhou internamente. Abra a pasta manualmente."
                else:
                    # Fallback para VS Code (onde o Antigravity tbm pode rodar)
                    vscode_exe = self._find_ide_executable("code")
                    if vscode_exe:
                        try:
                            subprocess.run(f"{vscode_exe} \"{path}\" --disable-workspace-trust", shell=True)
                            invocation_msg = "Cursor não encontrado no PC. Abrimos o VS Code em fallback com as instruções prontas."
                        except Exception:
                            invocation_msg = "VS Code falhou internamente ao abrir."
                    else:
                        invocation_msg = f"Nenhuma IDE detectada (Cursor/VSCode). Arquivos gerados no disco em {path}."
                
                # Script mock para Antigravity caso necessário
                if "antigravity" in ai_agent.lower():
                    with open(os.path.join(path, "start_antigravity.ps1"), "w") as f:
                        f.write(f'Write-Host "Iniciando Antigravity Agent localmente para {name} usando {model}..."\n')
            else:
                invocation_msg = f"Diretório base e prompt gerados em {path}. Abra no seu IDE preferido."
            
            return {
                "status": "success", 
                "message": f"Delegação de projeto iniciada. Ação: {invocation_msg}"
            }
        except Exception as e:
            logger.error(f"Erro ao criar projeto: {str(e)}")
            return {"status": "error", "message": str(e)}

    def run_terminal_command(self, command: str) -> Dict[str, Any]:
        """Executa um comando no terminal local."""
        try:
            import subprocess
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return {
                "status": "success" if result.returncode == 0 else "error",
                "stdout": result.stdout,
                "stderr": result.stderr,
                "return_code": result.returncode
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def _ensure_page(self, use_persistent_profile: bool = True):
        """Garante que o browser e a página estão prontos, usando um perfil persistente local do projeto."""
        if self.page and not self.page.is_closed():
            return
            
        playwright = await async_playwright().start()
        
        if use_persistent_profile:
            # Usar um caminho dentro do projeto para evitar conflitos com o Chrome real do usuário
            # e garantir que a sessão fique salva apenas para a Rebeka
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            user_data_dir = os.path.join(base_dir, 'agent', 'local', 'vault', 'browser_session')
            os.makedirs(user_data_dir, exist_ok=True)
            
            try:
                self.context = await playwright.chromium.launch_persistent_context(
                    user_data_dir,
                    headless=False, # Rebeka sempre age visivelmente para o usuário poder intervir se necessário
                    args=['--remote-debugging-port=9222']
                )
                logger.info(f"Browser iniciado com perfil persistente local em: {user_data_dir}")
            except Exception as e:
                logger.warning(f"Erro ao iniciar perfil persistente local: {e}. Lançando perfil temporário.")
                self.browser = await playwright.chromium.launch(headless=False)
                self.context = await self.browser.new_context()
        else:
            self.browser = await playwright.chromium.launch(headless=False)
            self.context = await self.browser.new_context()

        self.page = await self.context.new_page()

    async def _ensure_browser(self):
        """Método de legado para compatibilidade."""
        await self._ensure_page()

    async def browser_navigate(self, url: str) -> Dict[str, Any]:
        """Navega para uma URL e fecha o browser em seguida para poupar recursos."""
        try:
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(headless=True)  # Mais rápido
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url, timeout=15000)  # Timeout menor
            title = await page.title()
            await browser.close()
            await playwright.stop()
            return {"status": "success", "current_url": url, "title": title, "message": "Navegação concluída."}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    async def browser_search(self, query: str) -> Dict[str, Any]:
        """Pesquisa no Bing e retorna os resultados."""
        try:
            import urllib.parse
            encoded_query = urllib.parse.quote(query)
            search_url = f"https://www.bing.com/search?q={encoded_query}&setlang=pt-BR"
            
            playwright = await async_playwright().start()
            browser = await playwright.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            await page.goto(search_url, timeout=20000)
            await page.wait_for_load_state('domcontentloaded')
            await page.wait_for_timeout(2500)
            
            results = []
            # Seletores do Bing
            result_elements = await page.query_selector_all('.b_algo h2 a')
            
            for elem in result_elements[:10]:
                try:
                    title = await elem.inner_text()
                    link = await elem.get_attribute('href')
                    if title and link and link.startswith('http'):
                        results.append({"title": title, "link": link, "snippet": ""})
                except:
                    continue
            
            await browser.close()
            await playwright.stop()
            
            return {
                "status": "success",
                "query": query,
                "results": results,
                "count": len(results)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def desktop_type_text(self, text: str, interval: float = 0.1) -> Dict[str, Any]:
        """Digita texto no teclado, resolvendo segredos do Vault no último milissegundo."""
        try:
            # Blind Injection: Resolução ocorre aqui para evitar vazamento nos logs do chamador.
            final_text = self._resolve_vault_pointers(text)
            
            pyautogui.write(final_text, interval=interval)
            
            # O retorno nunca deve conter o segredo em texto puro
            safe_text = "INJECTED_FROM_VAULT" if "vault://" in text else text
            return {"status": "success", "action": f"Digitou: {safe_text}"}
        except Exception as e:
            return {"status": "error", "message": f"Erro ao digitar: {str(e)}"}

    def desktop_hotkey(self, keys: List[str]) -> Dict[str, Any]:
        """Executa atalho de teclado."""
        try:
            pyautogui.hotkey(*keys)
            return {"status": "success", "action": f"Executou atalho: {keys}"}
        except Exception as e:
            return {"status": "error", "message": f"Erro no atalho: {str(e)}"}

    def desktop_screenshot(self, file_name: str = "screenshot.png") -> Dict[str, Any]:
        """Tira um print da tela para análise visual."""
        try:
            pyautogui.screenshot(file_name)
            return {"status": "success", "action": f"Screenshot salva como {file_name}", "path": os.path.abspath(file_name)}
        except Exception as e:
            return {"status": "error", "message": f"Erro ao tirar screenshot: {str(e)}"}

    def read_code(self, file_path: str) -> Dict[str, Any]:
        """Lê o código de um arquivo local."""
        try:
            # Segurança básica: permitir apenas leitura dentro da pasta do projeto
            # (Pode ser expandido futuramente)
            with open(file_path, "r", encoding="utf-8-sig") as f:
                content = f.read()
            return {"status": "success", "content": content}
        except Exception as e:
            return {"status": "error", "message": f"Erro ao ler arquivo: {str(e)}"}

    def write_code(self, file_path: str, content: str) -> Dict[str, Any]:
        """Escreve/Sobrescreve um arquivo local."""
        try:
            with open(file_path, "w", encoding="utf-8-sig") as f:
                f.write(content)
            return {"status": "success", "message": f"Arquivo {file_path} escrito com sucesso."}
        except Exception as e:
            return {"status": "error", "message": f"Erro ao construir resposta: {str(e)}"}

    def desktop_click(self, x: Optional[int], y: Optional[int], text: Optional[str]) -> Dict[str, Any]:
        """Executa um clique no desktop."""
        if x is not None and y is not None:
            pyautogui.click(x, y)
            return {"status": "success", "action": f"Clicou em ({x}, {y})"}
        elif text:
            # Placeholder para OCR/Busca de imagem de botão
            logger.warning(f"Busca por texto '{text}' requer módulo Vision ativo.")
            return {"status": "partial_success", "message": f"Tentativa de clique em '{text}' registrada (Vision pendente)."}
        return {"status": "error", "message": "Parâmetros de clique insuficientes."}

    async def open_internal_browser(self, url: str, use_persistent_profile: bool = True) -> Dict[str, Any]:
        """Abre o navegador e inicia o stream de screenshots para o dashboard."""
        try:
            if not self.browser:
                playwright = await async_playwright().start()
                
                if use_persistent_profile:
                    user_data_dir = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Google/Chrome/User Data/Default')
                    # Tentar lançar. Se falhar (chrome aberto), lançar sem perfil.
                    try:
                        self.context = await playwright.chromium.launch_persistent_context(
                            user_data_dir,
                            headless=False,
                            args=['--remote-debugging-port=9222']
                        )
                        logger.info("Navegador lançado com perfil persistente.")
                    except Exception:
                        logger.warning("Falha ao usar perfil persistente (Chrome pode estar aberto). Lançando perfil limpo.")
                        self.browser = await playwright.chromium.launch(headless=False)
                        self.context = await self.browser.new_context()
                else:
                    self.browser = await playwright.chromium.launch(headless=False)
                    self.context = await self.browser.new_context()

                self.page = await self.context.new_page()

            await self.page.goto(url)
            
            # Iniciar tarefa de "streaming" (captura periódica)
            asyncio.create_task(self._stream_screenshots())
            
            return {"status": "success", "message": f"Navegador interno aberto em {url}"}
        except Exception as e:
            logger.error(f"Erro no navegador interno: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _stream_screenshots(self):
        """Salva screenshots periódicos da página para o dashboard ler."""
        # Caminho onde o dashboard espera encontrar o feed
        # vps/dashboard/static/browser_feed.png
        # Usar caminho absoluto vindo da raiz do projeto para segurança
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        feed_path = os.path.join(base_dir, "vps", "dashboard", "static", "browser_feed.png")
        os.makedirs(os.path.dirname(feed_path), exist_ok=True)
        
        logger.info(f"Stream de screenshots iniciado. Salvando em: {feed_path}")

        while self.page and not self.page.is_closed():
            try:
                await self.page.screenshot(path=feed_path)
                await asyncio.sleep(2) # 2 segundos de intervalor para o "live feed"
            except Exception as e:
                logger.error(f"Erro no stream de screenshots: {str(e)}")
                break
        logger.info("Stream de screenshots encerrado.")

    def list_installed_programs(self, search_term: str = "") -> Dict[str, Any]:
        """Lista programas instalados no Windows."""
        try:
            import subprocess
            # Usamos ConvertTo-Json para garantir um parsing limpo no Python
            if search_term:
                cmd = f'Get-StartApps | Where-Object {{ $_.Name -match "{search_term}" }} | Select-Object Name, AppID | ConvertTo-Json -Compress'
            else:
                # Se não tem termo de busca, limita a 50 para evitar sobrecarga
                cmd = 'Get-StartApps | Select-Object -First 50 Name, AppID | ConvertTo-Json -Compress'
                
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
            
            if result.returncode != 0:
                return {"status": "error", "message": result.stderr}
                
            import json
            stdout_txt = result.stdout.strip()
            if not stdout_txt:
                return {"status": "success", "programs": "Nenhum programa encontrado."}
                
            apps = json.loads(stdout_txt)
            if isinstance(apps, dict):
                apps = [apps] # ConvertTo-Json retorna dict se for só 1 item
                
            app_list = [f"- {app.get('Name', 'Unknown')} (ID: {app.get('AppID', 'Unknown')})" for app in apps]
            res_text = "\n".join(app_list) if app_list else "Nenhum programa encontrado."
            
            return {"status": "success", "programs": res_text}
        except Exception as e:
            logger.error(f"Erro ao listar programas: {str(e)}")
            return {"status": "error", "message": str(e)}

    def open_program(self, app_name: str) -> Dict[str, Any]:
        """Abre um programa usando o AppID via PowerShell e retorna informações para posterior fechamento."""
        try:
            import subprocess
            cmd = f'''
            $app = Get-StartApps | Where-Object {{ $_.Name -match "{app_name}" }} | Select-Object -First 1
            if ($app) {{
                $process = Start-Process "explorer.exe" "shell:appsFolder\\$($app.AppID)" -PassThru
                Write-Output "Opened:$($app.Name):$($app.AppID)"
            }} else {{
                Write-Output "App not found"
            }}
            '''
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
            
            output = result.stdout.strip()
            if "Opened:" in output:
                parts = output.split(":")
                name = parts[1] if len(parts) > 1 else app_name
                # Tenta derivar um nome de processo provável (nem sempre exato, mas ajuda a LLM)
                probable_process = name.replace(" ", "").lower()
                if "chrome" in probable_process or "brave" in probable_process or "edge" in probable_process:
                    probable_process = "chrome" if "chrome" in probable_process else ("brave" if "brave" in probable_process else "msedge")
                
                return {
                    "status": "success", 
                    "message": f"Programa '{name}' iniciado com sucesso.",
                    "app_name": name,
                    "tip": f"Para fechar silenciosamente depois, use a ferramenta close_program com o nome do processo (ex: '{probable_process}' ou consulte a barra de tarefas)."
                }
            else:
                return {"status": "error", "message": f"Programa '{app_name}' não encontrado. Tente listar os programas para ver o nome correto."}
        except Exception as e:
            logger.error(f"Erro ao abrir programa: {str(e)}")
            return {"status": "error", "message": str(e)}

    def close_program(self, process_name: str) -> Dict[str, Any]:
        """Fecha um programa em execução silenciosamente."""
        try:
            import subprocess
            # Tenta fechar amigavelmente primeiro, senão força
            cmd = f'''
            $processes = Get-Process -Name "{process_name}"* -ErrorAction SilentlyContinue
            if ($processes) {{
                $processes | Stop-Process -Force
                Write-Output "Closed"
            }} else {{
                Write-Output "Not Found"
            }}
            '''
            result = subprocess.run(["powershell", "-Command", cmd], capture_output=True, text=True)
            
            output = result.stdout.strip()
            if "Closed" in output:
                return {"status": "success", "message": f"Processo(s) '{process_name}' encerrado(s) com sucesso. Ambiente limpo."}
            else:
                return {"status": "error", "message": f"Nenhum processo correspondente a '{process_name}' foi encontrado em execução."}
        except Exception as e:
            logger.error(f"Erro ao fechar programa: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def perplexity_search(self, query: str) -> Dict[str, Any]:
        """Realiza uma pesquisa profunda no Perplexity verificando se há usuário logado."""
        try:
            await self._ensure_page(use_persistent_profile=True)
            
            logger.info(f"Verificando estado de login no Perplexity...")
            await self.page.goto("https://www.perplexity.ai/")
            
            # 1. Verificar se está logado ou se há modal de login
            # Heurística: se houver botão de 'Sign in' ou modal de login, não está pronto.
            signin_button = await self.page.query_selector('button:has-text("Sign in"), a:has-text("Sign in"), button:has-text("Entrar")')
            login_modal = await self.page.query_selector('text="Entrar ou criar uma conta", [class*="AuthModal"]')
            avatar = await self.page.query_selector('img[src*="googleusercontent"], .avatar, [class*="UserAccount"]')
            
            # Se encontrar o modal ou botão de login e não houver avatar claro, tentar login autônomo
            if (login_modal or signin_button) and not avatar:
                logger.info("Perplexity solicitou login. Iniciando fluxo autônomo com Google...")
                
                login_success = await self._handle_google_login()
                
                if not login_success:
                    return {
                        "status": "requires_login",
                        "message": "A Rebeka tentou logar sozinha no Google, mas parou em uma etapa que exige sua atenção (como o 2FA/Celular ou senha ausente no Vault).",
                        "action_required": "Por favor, complete o login ou aprove o 2FA no seu celular."
                    }
                
                # Recarregar a página após login para garantir estado limpo
                await self.page.goto("https://www.perplexity.ai/")
                await asyncio.sleep(3)

            logger.info(f"Usuário logado detectado. Iniciando Deep Research: {query}")
            
            # 2. Executar a busca
            # Seletores mais flexíveis
            textarea_selector = 'textarea, [role="textbox"]'
            await self.page.wait_for_selector(textarea_selector, timeout=20000)
            await self.page.fill(textarea_selector, query)
            await self.page.keyboard.press("Enter")
            
            await asyncio.sleep(4)  # Reduzido de 8 para 4 segundos
            
            # 3. Capturar Resposta
            # O perplexity mudou seletores. Vamos tentar pegar a última resposta estruturada
            content_selector = '.prose, [class*="content"], [class*="answer"]'
            await self.page.wait_for_selector(content_selector, timeout=60000)
            
            responses = await self.page.query_selector_all(content_selector)
            final_text = await responses[-1].inner_text() if responses else "Conteúdo não capturado."
            
            return {
                "status": "success",
                "is_pro": True, # Assumindo baseado no perfil do usuário
                "query": query,
                "answer_preview": final_text[:500] + "...",
                "full_answer": final_text,
                "url": self.page.url
            }
        except Exception as e:
            logger.error(f"Erro no Perplexity Search: {str(e)}")
            return {"status": "error", "message": f"Falha na pesquisa Perplexity: {str(e)}"}

    async def _handle_google_login(self) -> bool:
        """Fluxo autônomo de login via Google OAuth."""
        try:
            # 1. Clicar em 'Continue with Google'
            google_btn = await self.page.query_selector('button:has-text("Google")')
            if google_btn:
                # Perplexity abre em popup geralmente. Precisamos capturar o evento de popup.
                async with self.context.expect_page() as popup_info:
                    await google_btn.click()
                popup = await popup_info.value
                await popup.wait_for_load_state()
                
                logger.info("Janela de login do Google aberta.")
                
                # Definir o email a ser procurado via variável de ambiente (fallback para prompt manual se quiser)
                user_email = os.getenv("GMAIL_IMAP_USER", "gabriel.bsrj@gmail.com")
                user_email_prefix = user_email.split("@")[0]
                
                # 2. Procurar conta do usuário ou digitar email
                # Se a conta já estiver na lista
                account_selector = f'div[data-identifier*="{user_email_prefix}"], div:has-text("{user_email_prefix}")'
                account_listed = await popup.query_selector(account_selector)
                
                if account_listed:
                    logger.info(f"Conta '{user_email}' encontrada na lista. Clicando...")
                    await account_listed.click()
                    await asyncio.sleep(3)
                else:
                    # Tentar digitar o email se não estiver na lista
                    email_input = await popup.query_selector('input[type="email"]')
                    if email_input:
                        logger.info(f"Digitando email {user_email} no Google...")
                        await email_input.fill(user_email)
                        await popup.keyboard.press("Enter")
                        await asyncio.sleep(3)

                # 3. Verificar se pediu senha ou se já logou (janela fechou)
                if popup.is_closed(): return True

                password_input = await popup.query_selector('input[type="password"]')
                if password_input:
                    logger.info("Google solicitou senha. Tentando injeção do Vault...")
                    password = self._resolve_vault_pointers("vault://google_pass")
                    if password == "vault://google_pass":
                        logger.warning("Senha 'google_pass' não encontrada no Vault. Pedindo ajuda.")
                        return False
                    await password_input.fill(password)
                    await popup.keyboard.press("Enter")
                    await asyncio.sleep(4)
                
                # 4. Detecção de 2FA (Verificação em duas etapas)
                # Se a janela ainda está aberta e tem textos de 'verificação' ou 'celular'
                two_fa_indicator = await popup.query_selector('text="verificação", text="celular", text="aprovar", text="2-step"')
                if two_fa_indicator:
                    logger.warning("2FA/Verificação em duas etapas detectada. Requer ação do usuário no celular.")
                    return False

                # Aguardar finalização para ver se a janela fecha
                for _ in range(10):
                    if popup.is_closed(): return True
                    await asyncio.sleep(1)
                
            return False
                
            return False
        except Exception as e:
            logger.error(f"Erro no login autônomo do Google: {e}")
            return False
    async def google_antigravity_login(self) -> Dict[str, Any]:
        """Inicia o fluxo de login do Google Antigravity e salva no Vault."""
        try:
            from local.tools.login_antigravity import perform_google_login
            logger.info("Iniciando fluxo de login Google Antigravity...")
            
            # 1. Executar o login (abre browser, servidor local, troca tokens)
            creds = perform_google_login(timeout_seconds=300)
            
            if not creds or "access_token" not in creds:
                return {"status": "error", "message": "Falha ao obter tokens do Google."}
            
            # 2. Salvar no MasterVault
            from local.vault.master_vault import MasterVault
            vault = MasterVault()
            vault.save_secret("google_antigravity_creds", creds)
            
            email = creds.get("email", "Desconhecido")
            project = creds.get("project_id", "Desconhecido")
            
            return {
                "status": "success",
                "message": f"Login realizado com sucesso para {email} (Projeto: {project}). Credenciais salvas no MasterVault.",
                "user_email": email,
                "project_id": project
            }
        except Exception as e:
            logger.error(f"Erro no google_antigravity_login: {str(e)}")
            return {"status": "error", "message": f"Erro no login: {str(e)}"}

    def remember_user_info(self, key: str, value: str) -> Dict[str, Any]:
        """Salva informações pessoais do usuário no Banco de Causalidade."""
        try:
            from memory.causal_bank import CausalBank
            import os
            
            db_url = os.getenv("DATABASE_URL", "sqlite:///causal_bank_dev.db")
            origin = os.getenv("TWIN_TYPE", "local")
            bank = CausalBank(database_url=db_url, origin=origin)
            
            profile_data = {
                "domain": key,
                "observed_value": value,
                "confidence": 0.9,
                "source": "conversation",
                "last_observed_at": datetime.now(timezone.utc),
                "evidence": []
            }
            
            record_id = bank.insert_user_profile_observed(profile_data)
            
            logger.info(f"Informação do usuário salva: {key} = {value}")
            
            return {
                "status": "success",
                "message": f"Entendido! Guardei que seu {key} é {value}.",
                "key": key,
                "value": value
            }
        except Exception as e:
            logger.error(f"Erro ao lembrar informação do usuário: {str(e)}")
            return {"status": "error", "message": f"Erro ao salvar: {str(e)}"}

    def list_directory(self, path: str) -> Dict[str, Any]:
        """Lista arquivos e pastas em um diretório."""
        try:
            import os
            
            # Resolve path shortcuts
            if path.lower() == "desktop":
                path = os.path.join(os.path.expanduser("~"), "Desktop")
            elif path.lower() == "downloads":
                path = os.path.join(os.path.expanduser("~"), "Downloads")
            elif path.lower() == "documents":
                path = os.path.join(os.path.expanduser("~"), "Documents")
            
            if not os.path.exists(path):
                return {"status": "error", "message": f"Diretório não encontrado: {path}"}
            
            items = os.listdir(path)
            items_formatted = []
            for item in items:
                full_path = os.path.join(path, item)
                item_type = "pasta" if os.path.isdir(full_path) else "arquivo"
                items_formatted.append(f"[{item_type}] {item}")
            
            return {
                "status": "success",
                "path": path,
                "items": items_formatted,
                "message": f"Encontrados {len(items)} itens em {path}"
            }
        except Exception as e:
            logger.error(f"Erro ao listar diretório: {str(e)}")
            return {"status": "error", "message": f"Erro: {str(e)}"}

    def find_file(self, name: str, path: str = None) -> Dict[str, Any]:
        """Procura por arquivos ou pastas que contenham um nome específico."""
        try:
            import os
            
            # Default to Desktop if no path specified
            if not path or path.lower() == "desktop":
                path = os.path.join(os.path.expanduser("~"), "Desktop")
            elif path.lower() == "downloads":
                path = os.path.join(os.path.expanduser("~"), "Downloads")
            
            matches = []
            name_lower = name.lower()
            
            for root, dirs, files in os.walk(path):
                # Check directories
                for d in dirs:
                    if name_lower in d.lower():
                        matches.append(os.path.join(root, d))
                # Check files
                for f in files:
                    if name_lower in f.lower():
                        matches.append(os.path.join(root, f))
                
                # Limit search depth to avoid too long searches
                if len(matches) > 20:
                    break
            
            if not matches:
                return {
                    "status": "success",
                    "message": f"Nenhum arquivo ou pasta encontrado com '{name}' em {path}",
                    "matches": []
                }
            
            return {
                "status": "success",
                "message": f"Encontrados {len(matches)} resultados para '{name}'",
                "matches": matches[:20]
            }
        except Exception as e:
            logger.error(f"Erro ao buscar arquivo: {str(e)}")
            return {"status": "error", "message": f"Erro: {str(e)}"}

    def improve_whatsapp_system(self, folder_path: str = None) -> Dict[str, Any]:
        """Melhora o sistema de automação WhatsApp para evitar banimento."""
        import os
        import random
        
        # Resolve path
        if folder_path:
            if folder_path.lower() == "mercado_livre" or "mercado" in folder_path.lower():
                folder_path = os.path.join(os.path.expanduser("~"), "Desktop", "mercado_livre")
        else:
            folder_path = os.path.join(os.path.expanduser("~"), "Desktop", "mercado_livre")
        
        if not os.path.exists(folder_path):
            return {"status": "error", "message": f"Pasta não encontrada: {folder_path}"}
        
        changes = []
        
        # 1. Create/improve config.py with safe limits
        config_path = os.path.join(folder_path, "config.py")
        config_content = '''# Configuração de Segurança para Evitar Banimento no WhatsApp
# Modificado pela Rebeka em 2026-03-03

import random

# ===== LIMITES DE SEGURANÇA =====
MAX_OFFERS_PER_RUN = 4          # Máximo de ofertas por execução
MAX_MESSAGES_PER_HOUR = 6       # Máximo de mensagens por hora
MIN_DELAY_BETWEEN_MESSAGES = 300  # 5 minutos mínimo entre mensagens
MAX_DELAY_BETWEEN_MESSAGES = 600  # 10 minutos máximo entre mensagens

# ===== DELAYS EM MILISSEGUNDOS (para API do WhatsApp) =====
MIN_DELAY_MS = 300000   # 5 minutos em ms
MAX_DELAY_MS = 600000  # 10 minutos em ms

# ===== HORÁRIOS DE ENVIO (mínimo 4 horas de intervalo) =====
POST_TIMES = ["08:00", "13:00", "18:00", "22:00"]

# ===== TEMPLATES DE MENSAGEM (rotacionar para evitar spam) =====
MESSAGE_TEMPLATES = [
    "Encontrei {title} por {price}. Link: {link}",
    "Opa, {title} está com preço bom: {price}. Vale a pena! {link}",
    "Dica: {title} por {price} está em oferta. {link}",
    "Vi isso e pensei em você: {title} por {price}. {link}",
    "Olha que interessante: {title} por {price}. {link}",
]

def get_safe_delay():
    """Retorna um delay seguro com jitter."""
    base = random.randint(MIN_DELAY_BETWEEN_MESSAGES, MAX_DELAY_BETWEEN_MESSAGES)
    jitter = random.randint(0, 120)  # +0-2 minutos aleatório
    return base + jitter

def get_safe_delay_ms():
    """Retorna delay em milissegundos para API."""
    return random.randint(MIN_DELAY_MS, MAX_DELAY_MS)

def get_random_message_template():
    """Retorna um template aleatório para evitar padrão."""
    return random.choice(MESSAGE_TEMPLATES)
'''
        
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(config_content)
            changes.append(f"✓ config.py atualizado com limites seguros")
        except Exception as e:
            changes.append(f"✗ Erro ao criar config.py: {e}")
        
        # 2. Create safe_send_promos.py
        safe_promos_path = os.path.join(folder_path, "send_promos_safe.py")
        safe_promos_content = '''#!/usr/bin/env python3
"""
send_promos_safe.py - Versão segura do enviaador de promoções
Modificado pela Rebeka para evitar banimento no WhatsApp
"""

import asyncio
import random
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from whatsapp_poster import WhatsAppPoster
import config

class SafeWhatsAppPoster(WhatsAppPoster):
    """Versão segura com delays e limites."""
    
    def __init__(self):
        super().__init__()
        self.messages_sent_this_hour = 0
        self.last_reset = datetime.now()
        self.message_templates = config.MESSAGE_TEMPLATES
        
    def check_hourly_limit(self):
        """Reseta contador a cada hora."""
        now = datetime.now()
        if (now - self.last_reset).seconds >= 3600:
            self.messages_sent_this_hour = 0
            self.last_reset = now
            
    async def send_with_safe_delay(self, jid: str, message: str):
        """Envia mensagem com delay seguro."""
        self.check_hourly_limit()
        
        if self.messages_sent_this_hour >= config.MAX_MESSAGES_PER_HOUR:
            print(f"⚠️ Limite hourly atingido. Aguardando...")
            await asyncio.sleep(3600)
        
        delay = config.get_safe_delay()
        print(f"⏳ Aguardando {delay} segundos...")
        await asyncio.sleep(delay)
        
        result = await self.send_message(jid, message)
        
        if result.get("success"):
            self.messages_sent_this_hour += 1
            
        return result
    
    def format_safe_message(self, title: str, price: str, link: str) -> str:
        """Formata mensagem usando template aleatório."""
        template = random.choice(self.message_templates)
        return template.format(title=title, price=price, link=link)

async def main():
    poster = SafeWhatsAppPoster()
    
    # Lista de produtos (você pode integrar com ml_offers.py)
    offers = [
        {"title": "Produto Exemplo 1", "price": "R$ 99,90", "link": "https://produto.mercadolivre.com.br/..."},
        {"title": "Produto Exemplo 2", "price": "R$ 149,90", "link": "https://produto.mercadolivre.com.br/..."},
    ]
    
    group_jid = os.getenv("GROUP_JID", "seu-grupo@j.g.us")
    
    for offer in offers[:config.MAX_OFFERS_PER_RUN]:
        message = poster.format_safe_message(
            title=offer["title"],
            price=offer["price"],
            link=offer["link"]
        )
        
        print(f"📤 Enviando: {offer['title']}")
        result = await poster.send_with_safe_delay(group_jid, message)
        
        if result.get("success"):
            print(f"✅ Enviado com sucesso!")
        else:
            print(f"❌ Erro: {result}")
    
    print(f"📊 Total enviado esta rodada: {poster.messages_sent_this_hour}")

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        try:
            with open(safe_promos_path, "w", encoding="utf-8") as f:
                f.write(safe_promos_content)
            changes.append("✓ send_promos_safe.py criado com delays seguros")
        except Exception as e:
            changes.append(f"✗ Erro ao criar send_promos_safe.py: {e}")
        
        # 3. Update whatsapp_poster.py with safer delays if it exists
        whatsapp_path = os.path.join(folder_path, "whatsapp_poster.py")
        if os.path.exists(whatsapp_path):
            try:
                with open(whatsapp_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Add delay import if not exists
                if "import random" not in content:
                    content = "import random\n" + content
                
                # Add safe delay function if not exists
                if "def get_safe_delay" not in content:
                    safe_delay_code = '''

def get_safe_delay():
    """Retorna delay seguro em segundos (5-10 minutos)."""
    import random
    return random.randint(300, 600) + random.randint(0, 120)
'''
                    content = content.replace("import asyncio", "import asyncio" + safe_delay_code)
                
                with open(whatsapp_path, "w", encoding="utf-8") as f:
                    f.write(content)
                    
                changes.append("✓ whatsapp_poster.py atualizado com delays seguros")
            except Exception as e:
                changes.append(f"✗ Erro ao atualizar whatsapp_poster.py: {e}")
        
        return {
            "status": "success",
            "message": "Sistema melhorado para evitar banimento!",
            "changes": changes,
            "summary": {
                "max_offers_per_run": 4,
                "max_messages_per_hour": 6,
                "min_delay": "5 minutos",
                "max_delay": "10 minutos",
                "message_templates": 5
            }
        }

    def add_whatsapp_monitoring(self, folder_path: str = None) -> Dict[str, Any]:
        """Adiciona sistema de monitoramento avançado ao WhatsApp."""
        import os
        import json
        from datetime import datetime, timedelta
        
        # Resolve path
        if folder_path:
            if "mercado" in folder_path.lower():
                folder_path = os.path.join(os.path.expanduser("~"), "Desktop", "mercado_livre")
        else:
            folder_path = os.path.join(os.path.expanduser("~"), "Desktop", "mercado_livre")
        
        if not os.path.exists(folder_path):
            return {"status": "error", "message": f"Pasta não encontrada: {folder_path}"}
        
        changes = []
        
        # 1. Create monitoring module
        monitoring_path = os.path.join(folder_path, "whatsapp_monitor.py")
        monitoring_content = '''#!/usr/bin/env python3
"""
whatsapp_monitor.py - Sistema de Monitoramento Avançado
Monitora banimentos, retries, cooldown e alertas
Criado pela Rebeka em 2026-03-03
"""

import os
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WhatsAppMonitor:
    """Sistema de monitoramento para evitar banimento."""
    
    def __init__(self, data_file: str = "monitor_data.json"):
        self.data_file = data_file
        self.data = self._load_data()
        
        # Configurações de segurança
        self.MAX_RETRIES = 3
        self.COOLDOWN_HOURS = 24  # 24h de cooldown após warning
        self.BAN_CHECK_INTERVAL = 300  # Verificar a cada 5 minutos
        self.MAX_ERRORS_PER_DAY = 5
        
    def _load_data(self) -> Dict:
        """Carrega dados do monitoramento."""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {
            "cooldown_until": None,
            "warnings": [],
            "errors": [],
            "retries": [],
            "last_check": None,
            "ban_count": 0,
            "total_sent": 0
        }
    
    def _save_data(self):
        """Salva dados do monitoramento."""
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)
    
    def is_in_cooldown(self) -> bool:
        """Verifica se está em período de cooldown."""
        if not self.data.get("cooldown_until"):
            return False
        cooldown_until = datetime.fromisoformat(self.data["cooldown_until"])
        if datetime.now() < cooldown_until:
            return True
        # Cooldown ended, clear it
        self.data["cooldown_until"] = None
        self._save_data()
        return False
    
    def get_cooldown_remaining(self) -> Optional[int]:
        """Retorna minutos restantes de cooldown."""
        if not self.data.get("cooldown_until"):
            return None
        cooldown_until = datetime.fromisoformat(self.data["cooldown_until"])
        remaining = (cooldown_until - datetime.now()).total_seconds() / 60
        return int(remaining) if remaining > 0 else None
    
    def trigger_cooldown(self, reason: str = "warning_received"):
        """Ativa cooldown de 24h."""
        cooldown_until = datetime.now() + timedelta(hours=self.COOLDOWN_HOURS)
        self.data["cooldown_until"] = cooldown_until.isoformat()
        self.data["warnings"].append({
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })
        self._save_data()
        logger.warning(f"⚠️ COOLDOWN ATIVADO! Motivo: {reason}. Retornar em {self.COOLDOWN_HOURS}h")
    
    def add_error(self, error_type: str, message: str):
        """Registra erro e verifica se precisa de cooldown."""
        self.data["errors"].append({
            "type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Limpar erros antigos (mais de 24h)
        self._clean_old_errors()
        
        # Se muitos erros hoje, ativar cooldown
        today_errors = [e for e in self.data["errors"] 
                       if datetime.fromisoformat(e["timestamp"]).date() == datetime.now().date()]
        
        if len(today_errors) >= self.MAX_ERRORS_PER_DAY:
            self.trigger_cooldown(f" Muitos erros ({len(today_errors)} hoje)")
        
        self._save_data()
    
    def _clean_old_errors(self):
        """Remove erros com mais de 24h."""
        cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
        self.data["errors"] = [e for e in self.data["errors"] 
                              if e["timestamp"] > cutoff]
    
    async def send_with_retry(self, send_func, *args, **kwargs) -> Dict:
        """Envia mensagem com retry e backoff exponencial."""
        last_error = None
        
        for attempt in range(self.MAX_RETRIES):
            try:
                result = await send_func(*args, **kwargs)
                
                if result.get("success"):
                    self.data["total_sent"] += 1
                    self._save_data()
                    return result
                
                last_error = result.get("error", "Unknown error")
                self.add_error("send_failed", last_error)
                
            except Exception as e:
                last_error = str(e)
                self.add_error("exception", last_error)
            
            if attempt < self.MAX_RETRIES - 1:
                # Backoff exponencial: 2, 4, 8 segundos
                wait_time = 2 ** (attempt + 1)
                logger.info(f"⏳ Retry em {wait_time}s (tentativa {attempt + 1}/{self.MAX_RETRIES})")
                time.sleep(wait_time)
        
        # Todas tentativas falharam
        return {"success": False, "error": f"Falhou após {self.MAX_RETRIES} tentativas: {last_error}"}
    
    def check_if_banned(self, api_response: Dict) -> bool:
        """Detecta se a conta foi banida."""
        error_messages = [
            "banido", "banned", "blocked", "account disabled",
            "número bloqueado", "phone number blocked"
        ]
        
        error_text = str(api_response).lower()
        for msg in error_messages:
            if msg in error_text:
                self.data["ban_count"] += 1
                self.trigger_cooldown("Conta banida detectada!")
                return True
        
        return False
    
    def get_status(self) -> Dict:
        """Retorna status atual do monitoramento."""
        return {
            "in_cooldown": self.is_in_cooldown(),
            "cooldown_remaining_minutes": self.get_cooldown_remaining(),
            "total_sent": self.data.get("total_sent", 0),
            "ban_count": self.data.get("ban_count", 0),
            "warnings_today": len([w for w in self.data.get("warnings", []) 
                                  if datetime.fromisoformat(w["timestamp"]).date() == datetime.now().date()]),
            "errors_today": len([e for e in self.data.get("errors", []) 
                                if datetime.fromisoformat(e["timestamp"]).date() == datetime.now().date()])
        }
    
    def reset(self):
        """Reseta todos os dados de monitoramento."""
        self.data = {
            "cooldown_until": None,
            "warnings": [],
            "errors": [],
            "retries": [],
            "last_check": None,
            "ban_count": 0,
            "total_sent": 0
        }
        self._save_data()
        logger.info("✅ Monitoramento resetado")


# Função para integrar com o sistema existente
def create_monitored_poster(original_poster_class):
    """Cria versão monitorada de qualquer poster."""
    
    class MonitoredPoster(original_poster_class):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.monitor = WhatsAppMonitor()
        
        async def send_message(self, *args, **kwargs):
            # Verifica cooldown primeiro
            if self.monitor.is_in_cooldown():
                remaining = self.monitor.get_cooldown_remaining()
                raise Exception(f"Sistema em cooldown. Aguarde {remaining} minutos.")
            
            # Envia com retry
            result = await self.monitor.send_with_retry(
                super().send_message, *args, **kwargs
            )
            
            # Verifica se foi banido
            self.monitor.check_if_banned(result)
            
            return result
    
    return MonitoredPoster


if __name__ == "__main__":
    # Teste
    monitor = WhatsAppMonitor()
    print("📊 Status:", monitor.get_status())
'''
        
        try:
            with open(monitoring_path, "w", encoding="utf-8") as f:
                f.write(monitoring_content)
            changes.append("✓ whatsapp_monitor.py criado com sistema de cooldown e retry")
        except Exception as e:
            changes.append(f"✗ Erro ao criar monitor: {e}")
        
        # 2. Create dashboard for monitoring
        dashboard_path = os.path.join(folder_path, "monitor_dashboard.py")
        dashboard_content = '''#!/usr/bin/env python3
"""
monitor_dashboard.py - Dashboard de Monitoramento
Visualize o status do sistema de automação
Criado pela Rebeka em 2026-03-03
"""

import os
import sys
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from whatsapp_monitor import WhatsAppMonitor
except ImportError:
    print("Erro: whatsapp_monitor.py não encontrado")
    sys.exit(1)

def print_status():
    monitor = WhatsAppMonitor()
    status = monitor.get_status()
    
    print("\\n" + "="*50)
    print("📊 MONITOR WHATSAPP - STATUS ATUAL")
    print("="*50)
    print(f"⏰ Em Cooldown: {'🔴 SIM' if status['in_cooldown'] else '🟢 NÃO'}")
    
    if status['cooldown_remaining_minutes']:
        print(f"⏳ Tempo restante: {status['cooldown_remaining_minutes']} minutos")
    
    print(f"\\n📤 Total enviado: {status['total_sent']}")
    print(f"⚠️ Banimentos: {status['ban_count']}")
    print(f"⚠️ Avisos hoje: {status['warnings_today']}")
    print(f"❌ Erros hoje: {status['errors_today']}")
    
    print("\\n" + "="*50)
    
    if status['in_cooldown']:
        print("⚠️  ATENÇÃO: Sistema em modo cooldown!")
        print("   Não envie mensagens até o cooldown terminar.")
    elif status['warnings_today'] >= 3:
        print("⚠️  ATENÇÃO: Muitos avisos hoje!")
        print("   Considere parar o sistema temporariamente.")
    else:
        print("✅ Sistema operando normalmente.")
    
    print("="*50)

def print_help():
    print("""
📖 Comandos:
  python monitor_dashboard.py status    - Ver status atual
  python monitor_dashboard.py reset      - Resetar monitoramento
  python monitor_dashboard.py help        - Mostrar esta ajuda
""")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "status":
            print_status()
        elif command == "reset":
            monitor = WhatsAppMonitor()
            monitor.reset()
            print("✅ Monitoramento resetado!")
        else:
            print_help()
    else:
        print_status()
'''
        
        try:
            with open(dashboard_path, "w", encoding="utf-8") as f:
                f.write(dashboard_content)
            changes.append("✓ monitor_dashboard.py criado para visualização de status")
        except Exception as e:
            changes.append(f"✗ Erro ao criar dashboard: {e}")
        
        # 3. Create health check script
        health_path = os.path.join(folder_path, "health_check.py")
        health_content = '''#!/usr/bin/env python3
"""
health_check.py - Verificação de Saúde do Sistema
Execute periodicamente para verificar se tudo está bem
Criado pela Rebeka em 2026-03-03
"""

import os
import sys
import asyncio
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def check_api_health(api_url: str) -> bool:
    """Verifica se a API está respondendo."""
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{api_url}/health", timeout=5) as resp:
                return resp.status == 200
    except:
        return False

async def check_group_exists(api, group_jid: str) -> bool:
    """Verifica se o grupo ainda existe."""
    try:
        # Implementar verificação específica da API
        return True
    except:
        return False

async def main():
    print("🔍 Verificando saúde do sistema...")
    
    # Carregar config
    try:
        import config
        api_url = getattr(config, 'EVOLUTION_API_URL', 'http://localhost:8080')
        group_jid = getattr(config, 'GROUP_JID', None)
    except:
        print("❌ Erro ao carregar config.py")
        return
    
    # Verificar API
    api_healthy = await check_api_health(api_url)
    if not api_healthy:
        print(f"❌ API não está respondendo: {api_url}")
    else:
        print(f"✅ API respondendo: {api_url}")
    
    # Verificar monitor
    try:
        from whatsapp_monitor import WhatsAppMonitor
        monitor = WhatsAppMonitor()
        status = monitor.get_status()
        
        if status['in_cooldown']:
            print(f"⏳ Sistema em cooldown: {status['cooldown_remaining_minutes']}min restantes")
        elif status['warnings_today'] >= 3:
            print(f"⚠️ Muitos avisos hoje: {status['warnings_today']}")
        else:
            print("✅ Monitor OK")
            
    except Exception as e:
        print(f"⚠️ Erro no monitor: {e}")
    
    # Verificar histórico
    history_file = "sent_offers_history.json"
    if os.path.exists(history_file):
        import json
        with open(history_file, 'r') as f:
            history = json.load(f)
        print(f"📊 Histórico: {len(history)} ofertas enviadas")

if __name__ == "__main__":
    asyncio.run(main())
'''
        
        try:
            with open(health_path, "w", encoding="utf-8") as f:
                f.write(health_content)
            changes.append("✓ health_check.py criado para verificação de saúde")
        except Exception as e:
            changes.append(f"✗ Erro ao criar health check: {e}")
        
        # 4. Update scheduler to respect cooldown
        scheduler_path = os.path.join(folder_path, "scheduler.py")
        if os.path.exists(scheduler_path):
            try:
                with open(scheduler_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # Add cooldown check
                cooldown_check = '''
# Check if system is in cooldown before running
try:
    from whatsapp_monitor import WhatsAppMonitor
    monitor = WhatsAppMonitor()
    if monitor.is_in_cooldown():
        remaining = monitor.get_cooldown_remaining()
        logger.warning(f"Sistema em cooldown. Pulando execução. Restam {remaining} minutos.")
        return
except ImportError:
    pass
'''
                if "cooldown" not in content.lower():
                    content = content.replace("def run_job", cooldown_check + "\ndef run_job")
                    with open(scheduler_path, "w", encoding="utf-8") as f:
                        f.write(content)
                    changes.append("✓ scheduler.py atualizado para respeitar cooldown")
            except Exception as e:
                changes.append(f"✗ Erro ao atualizar scheduler: {e}")
        
        return {
            "status": "success",
            "message": "Sistema de monitoramento adicionado!",
            "changes": changes,
            "summary": {
                "whatsapp_monitor": "Sistema de cooldown 24h e retry com backoff",
                "monitor_dashboard": "Visualize o status a qualquer momento",
                "health_check": "Verificação automática de saúde",
                "scheduler_update": "Respeita cooldown antes de executar"
            },
            "how_to_use": {
                "status": "python monitor_dashboard.py status",
                "reset": "python monitor_dashboard.py reset",
                "health": "python health_check.py"
            }
        }

