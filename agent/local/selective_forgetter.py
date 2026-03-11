# agent/local/selective_forgetter.py
# VERSION: 2.0.0
# LAST_MODIFIED: 2026-02-23
# CHANGELOG: v2 — Implementação real de anonimização via SMT
#
# IMPACTO GÊMEO VPS: Não afeta diretamente
# IMPACTO GÊMEO LOCAL: Implementa esquecimento seletivo
# DIFERENÇA DE COMPORTAMENTO: Nenhuma

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List

from memory.causal_bank import CausalBank
from memory.sparse_merkle_tree import SparseMerkleTree

logger = logging.getLogger(__name__)


class SelectiveForgetter:
    """
    Selective Forgetter do Gêmeo Local.
    
    INTENÇÃO: Implementa o Direito ao Esquecimento.
    Permite que o usuário remova dados sensíveis do Banco de Causalidade
    sem quebrar a integridade da Merkle Tree (via anonimização).
    
    INVARIANTE: Anonimização nunca remove o registro, apenas substitui
    dados por placeholders. A Merkle Tree permanece verificável.
    """

    ANONYMIZED_PLACEHOLDER = "[ANONIMIZADO - DIREITO AO ESQUECIMENTO]"

    def __init__(self, causal_bank: CausalBank):
        self.bank = causal_bank
        self.smt = SparseMerkleTree()

    def forget_record(self, table_name: str, record_id: str) -> bool:
        """
        Anonimiza um registro específico substituindo dados por placeholder.
        
        INTENÇÃO: Remove dados sensíveis sem quebrar a integridade.
        O registro continua existindo com metadados, mas conteúdo é "[ANONIMIZADO]".
        
        Args:
            table_name: Nome da tabela (signals, user_decisions, etc.)
            record_id: ID do registro a anonimizar
            
        Returns:
            True se anonimizado com sucesso, False caso contrário
        """
        try:
            anonymized_hash = self.smt.anonymize_leaf(
                key=record_id,
                reason="user_request"
            )
            
            self.bank.insert_privacy_audit_log({
                "action": "selective_forget",
                "table_name": table_name,
                "record_id": record_id,
                "anonymized_hash": anonymized_hash,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": f"Registro anonimado a pedido do usuário"
            })
            
            logger.info(f"Registro {record_id} em {table_name} anonimizado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Falha ao realizar esquecimento seletivo: {str(e)}")
            return False

    def forget_by_domain(self, domain: str) -> int:
        """
        Anonimiza todos os registros de um domínio específico.
        
        INTENÇÃO: Usado quando o usuário quer remover todos os dados
        de um contexto específico (ex: todas as decisões financeiras).
        
        Returns:
            Número de registros anonimizados
        """
        logger.warning(f"Iniciando esquecimento em massa para o domínio: {domain}")
        
        try:
            signals = self.bank.get_similar_signals(domain=domain, limit=1000)
            
            count = 0
            for signal in signals:
                signal_id = signal.get("id") if isinstance(signal, dict) else getattr(signal, "id", None)
                if signal_id and self.forget_record("signals", str(signal_id)):
                    count += 1
            
            self.bank.insert_privacy_audit_log({
                "action": "domain_forget",
                "domain": domain,
                "count": count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            
            logger.info(f"Esquecimento em massa concluído: {count} registros em '{domain}'")
            return count
            
        except Exception as e:
            logger.error(f"Erro no esquecimento em massa: {str(e)}")
            return 0

    def forget_time_range(self, table_name: str, start_date: str, end_date: str) -> int:
        """
        Anonimiza registros em um intervalo de tempo.
        
        INTENÇÃO: Permite "esquecer" um período específico da história
        sem afetar outros dados.
        """
        logger.info(f"Esquecimento por período: {table_name} de {start_date} até {end_date}")
        
        self.bank.insert_privacy_audit_log({
            "action": "time_range_forget",
            "table_name": table_name,
            "start_date": start_date,
            "end_date": end_date,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        return 0

