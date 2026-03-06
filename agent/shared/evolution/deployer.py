# agent/shared/evolution/deployer.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial — deploy com rollback

import logging
import time
from typing import Dict, Any, Optional # Added Optional
import shutil # Added shutil

logger = logging.getLogger(__name__)

class Deployer:
    """
    Deployer — O mestre de obras.
    
    INTENÇÃO: Realiza o deploy do novo código validado.
    Mantém uma janela de observação para rollback automático.
    """

    def __init__(self, causal_bank: Optional[Any] = None):
        self.bank = causal_bank

    def deploy(self, evolution_id: str, target_file: str, new_content: str) -> Dict[str, Any]:
        """
        Aplica a mudança em produção apenas se aprovada formalmente.
        """
        logger.info(f"Revisando proposta de deploy {evolution_id}...")
        
        # 1. Verificar aprovação no banco (Modo Sombra — Etapa 11 Prompt L146)
        if self.bank:
            approval = self.bank.get_evolution_approval(evolution_id)
            if not approval or not approval.get("human_authorized"):
                logger.warning(f"DEPLOY BLOQUEADO: Evolução {evolution_id} aguarda aprovação manual do usuário.")
                return {
                    "success": False,
                    "status": "PENDING_USER_APPROVAL",
                    "reason": "Mapeada para Shadow Mode — Aprovação humana necessária no Dashboard."
                }

        # 2. Backup do arquivo original
        backup_path = f"{target_file}.{int(time.time())}.bak"
        try:
            shutil.copy2(target_file, backup_path)
            logger.info(f"Backup criado em: {backup_path}")
        except Exception as e:
            return {"success": False, "error": f"Falha no backup: {str(e)}"}

        # 3. Aplicar Mudança
        try:
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(new_content)
            logger.info(f"MUDANÇA APLICADA: {target_file} atualizado com sucesso!")
            
            # 4. Registrar no Banco
            if self.bank:
                self.bank.insert_system_event({
                    "event_type": "evolution_deploy",
                    "evolution_id": evolution_id,
                    "target_file": target_file,
                    "backup": backup_path
                })
                
            return {"success": True, "status": "DEPLOYED", "backup": backup_path}
        except Exception as e:
            # Rollback imediato se falhar a escrita
            logger.error(f"Erro no deploy — restaurando backup: {e}")
            shutil.copy2(backup_path, target_file)
            return {"success": False, "error": str(e)}

    def rollback(self, evolution_id: str, target_file: str, backup_path: str):
        """
        Reverte uma evolução usando o backup.
        """
        logger.error(f"EXECUTANDO ROLLBACK: {evolution_id} revertido de {backup_path}")
        try:
            shutil.copy2(backup_path, target_file)
            return True
        except Exception as e:
            logger.error(f"Falha crítica no rollback: {e}")
            return False
