# system_conflict_checker.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-03-06
# CHANGELOG: Fase 1 - Verificação de conflitos entre sistemas

import psutil
import os
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SystemConflictChecker:
    """
    Auditor de conflitos entre sistemas existentes.
    Verifica portas, APIs, banco de dados e recursos antes de inicializar.
    
    PRIORIDADE: CRÍTICA - Executar antes de qualquer inicialização.
    """
    
    # Sistemas conhecidos pelo usuário
    SISTEMAS_CONHECIDOS = {
        "mercado_livre_bot": {
            "path": "C:/Users/Aridelson/Desktop/mercado_livre",
            "portas_tipicas": [8080, 8081, 5000, 3000],
            "api_keys": ["mercadolibre"],
            "description": "Bot de promoções do Mercado Livre Chile"
        },
        "sistema_trader": {
            "path": "C:/Users/Aridelson/Documents/sistematrader",
            "portas_tipicas": [8000, 8080, 9000, 5432],
            "api_keys": ["broker", "polymarket"],
            "description": "Sistema de trade avançado"
        },
        "rebeka_agent": {
            "path": "C:/Users/Aridelson/Desktop/rebeka2/agent",
            "portas_tipicas": [8000, 8086],
            "api_keys": ["moonshot", "google"],
            "description": "Agente Rebeka (este sistema)"
        }
    }
    
    def __init__(self):
        self.report = {}
        
    def get_ports_in_use(self) -> Dict[int, Dict[str, Any]]:
        """Retorna todas as portas em uso no sistema com detalhes do processo."""
        portas = {}
        try:
            for conn in psutil.net_connections():
                if conn.status == 'LISTEN' and conn.laddr:
                    porta = conn.laddr.port
                    try:
                        proc = psutil.Process(conn.pid)
                        portas[porta] = {
                            "pid": conn.pid,
                            "process_name": proc.name(),
                            "status": conn.status
                        }
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        portas[porta] = {
                            "pid": conn.pid,
                            "process_name": "unknown",
                            "status": conn.status
                        }
        except Exception as e:
            logger.error(f"Erro ao verificar portas: {e}")
        return portas
    
    def check_port_conflicts(self) -> List[Dict[str, Any]]:
        """Verifica se algum sistema conhecido está usando portas em conflito."""
        conflitos = []
        portas_em_uso = self.get_ports_in_use()
        
        for sistema_nome, sistema_info in self.SISTEMAS_CONHECIDOS.items():
            for porta_tipica in sistema_info["portas_tipicas"]:
                if porta_tipica in portas_em_uso:
                    proc_info = portas_em_uso[porta_tipica]
                    conflitos.append({
                        "tipo": "porta",
                        "sistema": sistema_nome,
                        "porta": porta_tipica,
                        "processo": proc_info["process_name"],
                        "pid": proc_info["pid"],
                        "severidade": "CRÍTICO" if porta_tipica in [8000, 5432] else "ALTO"
                    })
                    
        return conflitos
    
    def check_system_directories(self) -> Dict[str, bool]:
        """Verifica se os diretórios dos sistemas conhecidos existem."""
        resultado = {}
        for nome, info in self.SISTEMAS_CONHECIDOS.items():
            caminho = info["path"]
            # Expand user path
            caminho = os.path.expanduser(caminho) if "~" in caminho else caminho
            existe = os.path.exists(caminho)
            resultado[nome] = {
                "existe": existe,
                "caminho": caminho
            }
        return resultado
    
    def check_process_running(self, process_names: List[str]) -> List[Dict[str, Any]]:
        """Verifica se processos estão rodando."""
        processos_encontrados = []
        
        for proc in psutil.process_iter(['name', 'pid', 'cpu_percent', 'memory_percent']):
            try:
                nome = proc.info['name'].lower()
                for nome_busca in process_names:
                    if nome_busca.lower() in nome:
                        processos_encontrados.append({
                            "nome": proc.info['name'],
                            "pid": proc.info['pid'],
                            "cpu": proc.info['cpu_percent'],
                            "memoria": proc.info['memory_percent']
                        })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        return processos_encontrados
    
    def check_api_conflicts(self) -> List[Dict[str, Any]]:
        """
        Verifica conflitos de API.
        Por enquanto, retorna aviso sobre rate limits potenciais.
        """
        # Aqui podemos expandir para verificar se há APIs sendo chamadas
        # simultaneamente por diferentes sistemas
        return []
    
    def check_database_access(self) -> Dict[str, Any]:
        """
        Verifica acesso ao banco de dados.
        """
        resultado = {
            "postgresql_em_uso": False,
            "processos_postgres": [],
            "aviso": None
        }
        
        # Verificar se PostgreSQL está rodando
        processos = self.check_process_running(["postgres", "pg"])
        if processos:
            resultado["postgresql_em_uso"] = True
            resultado["processos_postgres"] = processos
            
        return resultado
    
    def audit_on_startup(self) -> Dict[str, Any]:
        """
        Executa auditoria completa ao iniciar.
        Retorna relatório com todos os conflitos encontrados.
        """
        logger.info("Iniciando auditoria de conflitos de sistemas...")
        
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "porta_conflitos": self.check_port_conflicts(),
            "sistemas_encontrados": self.check_system_directories(),
            "processos_ativos": self.check_process_running(["python", "node", "docker"]),
            "database_status": self.check_database_access(),
            "api_conflicts": self.check_api_conflicts(),
            "recomendacoes": []
        }
        
        # Gerar recomendações
        if self.report["porta_conflitos"]:
            self.report["recomendacoes"].append({
                "tipo": "PORTA",
                "prioridade": "ALTA",
                "mensagem": f"Conflitos de porta detectados: {len(self.report['porta_conflitos'])}"
            })
            
        # Verificar se é seguro iniciar
        self.report["safe_to_start"] = self.safe_to_start()
        
        logger.info(f"Auditoria concluída. Seguro iniciar: {self.report['safe_to_start']}")
        
        return self.report
    
    def safe_to_start(self) -> bool:
        """
        Determina se é seguro inicializar os sistemas.
        Retorna False se houver conflitos críticos.
        """
        if not hasattr(self, 'report') or not self.report:
            self.audit_on_startup()
            
        # Conflitos críticos: portas 8000 (dashboard) ou 5432 (banco)
        conflitos_criticos = [
            c for c in self.report.get("porta_conflitos", [])
            if c.get("severidade") == "CRÍTICO"
        ]
        
        return len(conflitos_criticos) == 0
    
    def get_status_summary(self) -> str:
        """Retorna resumo formatado do status."""
        if not hasattr(self, 'report') or not self.report:
            self.audit_on_startup()
            
        summary = f"""
=== REBEKA - AUDITORIA DE SISTEMAS ===
Timestamp: {self.report['timestamp']}

PORTAS EM USO:
"""
        if self.report['porta_conflitos']:
            for c in self.report['porta_conflitos']:
                summary += f"  ⚠️ [{c['severidade']}] {c['sistema']} - Porta {c['porta']} em uso por {c['processo']}\n"
        else:
            summary += "  ✅ Nenhum conflito de porta detectado\n"
            
        summary += "\nDIRETÓRIOS:\n"
        for sist, info in self.report['sistemas_encontrados'].items():
            status = "✅" if info['existe'] else "❌"
            summary += f"  {status} {sist}: {info['caminho']}\n"
            
        summary += f"""
STATUS GERAL:
  Seguro para iniciar: {'✅ SIM' if self.report['safe_to_start'] else '❌ NÃO'}
"""
        
        return summary


def run_audit() -> Dict[str, Any]:
    """Executa auditoria e retorna relatório."""
    checker = SystemConflictChecker()
    return checker.audit_on_startup()


if __name__ == "__main__":
    checker = SystemConflictChecker()
    checker.audit_on_startup()
    print(checker.get_status_summary())
