# agent/shared/evolution/sandbox.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — ambiente isolado de validação

import logging
import os
import shutil
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class Sandbox:
    """
    Sandbox — O laboratório isolado.
    
    INTENÇÃO: Toda mudança de código nasce e deve ser validada aqui.
    O ambiente não tem rede, não tem acesso ao banco de produção 
    e opera sobre dados sintéticos.
    """

    def __init__(self, sandbox_path: str = None):
        if sandbox_path is None:
            # Caminho absoluto para evitar confusão no Windows
            self.path = os.path.abspath(os.path.join(os.path.dirname(__file__), "sandbox_run"))
        else:
            self.path = os.path.abspath(sandbox_path)
            
        if not os.path.exists(self.path):
            os.makedirs(self.path)

    def run_validation(self, file_path: str, code_content: str) -> Dict[str, Any]:
        """
        Executa o código proposto em um subprocesso com ambiente restrito.
        """
        logger.info(f"Iniciando validação no Sandbox para: {file_path}")
        
        # 1. Preparar arquivo temporário dentro do sandbox
        filename = os.path.basename(file_path)
        temp_file = os.path.join(self.path, f"evolved_{filename}")
        
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(code_content)
        
        # 2. Executar teste de fumaça (importação e sintaxe)
        import subprocess
        import sys
        
        # Criar ambiente "limpo" (sem chaves de API reais)
        clean_env = os.environ.copy()
        for key in list(clean_env.keys()):
            if "KEY" in key or "SECRET" in key or "TOKEN" in key:
                clean_env[key] = "MASKED_IN_SANDBOX"
        
        # Desabilitar rede (simulação simples via variáveis de ambiente comuns)
        clean_env["HTTP_PROXY"] = "http://127.0.0.1:9999"
        clean_env["HTTPS_PROXY"] = "https://127.0.0.1:9999"

        try:
            # Tentar rodar o script (apenas verificação de sintaxe primeiro)
            result = subprocess.run(
                [sys.executable, "-m", "py_compile", temp_file],
                capture_output=True,
                text=True,
                env=clean_env,
                timeout=30
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": "Erro de Sintaxe ou Compilação",
                    "details": result.stderr
                }
            
            # Se passou na compilação, o Sandbox considera um sucesso preliminar
            # O PropertyTester fará a validação lógica profunda.
            return {
                "success": True,
                "sandbox_path": temp_file,
                "message": "Código compilado com sucesso no ambiente isolado."
            }
            
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Timeout na Sandbox (loop infinito provável?)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def cleanup(self):
        """Limpa o ambiente do sandbox."""
        if os.path.exists(self.path):
            import shutil
            shutil.rmtree(self.path)
            os.makedirs(self.path)
        logger.info("Sandbox limpo.")
