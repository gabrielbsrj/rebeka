# intelligence/developer.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-03-12
# CHANGELOG: Criação inicial — Developer para propostas de melhoria evolutiva

"""
Developer — Propositor de Melhorias

Quando o Observer detecta problemas de performance ou integridade,
o Developer propõe modificações de código.

Opera em Shadow Mode: nunca aplica mudanças diretamente.
Todas as propostas passam por Sandbox → SecurityAnalyzer → PropertyTester → User Approval.
"""

import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger("intelligence.developer")


class Developer:
    """Propõe melhorias de código baseadas em análise do Observer."""

    def __init__(self):
        self.mode = "shadow"  # Sempre em shadow mode
        logger.info("Developer inicializado (Shadow Mode).")

    def propose_improvement(
        self,
        target_file: str,
        issue_description: str,
        metrics: dict = None,
    ) -> dict:
        """
        Propõe uma melhoria para um arquivo dado um problema detectado.

        Retorna dict com:
        - evolution_id: ID único da proposta
        - target_file: arquivo alvo
        - rationale: justificativa
        - proposed_content: conteúdo proposto (placeholder)
        - metrics_snapshot: snapshot das métricas
        - timestamp: quando foi proposto
        """
        evolution_id = f"evo_{uuid.uuid4().hex[:12]}"

        try:
            # Ler conteúdo atual do arquivo
            with open(target_file, "r", encoding="utf-8") as f:
                current_content = f.read()
        except FileNotFoundError:
            return {
                "error": f"Arquivo não encontrado: {target_file}",
                "evolution_id": evolution_id,
            }
        except Exception as e:
            return {
                "error": f"Erro ao ler arquivo: {str(e)}",
                "evolution_id": evolution_id,
            }

        # Gerar rationale baseado nas métricas
        rationale = self._generate_rationale(issue_description, metrics)

        proposal = {
            "evolution_id": evolution_id,
            "target_file": target_file,
            "rationale": rationale,
            "proposed_content": current_content,  # Em shadow mode, propõe o mesmo conteúdo
            "metrics_snapshot": metrics or {},
            "issue_description": issue_description,
            "mode": self.mode,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"Proposta de melhoria gerada: {evolution_id} para {target_file}"
        )
        return proposal

    def _generate_rationale(self, issue: str, metrics: dict = None) -> str:
        """Gera justificativa para a proposta de melhoria."""
        parts = [f"Problema detectado: {issue}"]

        if metrics:
            win_rate = metrics.get("win_rate", "N/A")
            confidence = metrics.get("avg_reported_confidence", "N/A")
            cal_error = metrics.get("confidence_calibration_error", "N/A")

            if isinstance(win_rate, (int, float)):
                parts.append(f"Win rate atual: {win_rate:.1%}")
            if isinstance(confidence, (int, float)):
                parts.append(f"Confiança média reportada: {confidence:.1%}")
            if isinstance(cal_error, (int, float)):
                parts.append(f"Erro de calibração: {cal_error:.2f}")

        parts.append(f"Modo: {self.mode} (sem aplicação automática)")

        return " | ".join(parts)
