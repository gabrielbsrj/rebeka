# shared/communication/reporter.py
# VERSION: 1.0.0
# LAST_MODIFIED: 2026-02-19
# CHANGELOG: Criação inicial

"""
Reporter — Gerador de relatórios de performance e evolução.

INTENÇÃO: Relatórios diários e semanais que mostram ao usuário
como o agente está evoluindo. Transparência é confiança.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class Reporter:
    """
    Gera relatórios estruturados de performance e evolução.

    INTENÇÃO: O usuário precisa ver progresso real, não apenas resultados.
    Cada relatório mostra: performance, evolução do raciocínio,
    coerência do usuário, e próximos passos propostos.
    """

    def __init__(self, personality_name: str = "Rebeka"):
        self._personality_name = personality_name

    def generate_daily_report(
        self,
        performance_stats: Dict[str, Any],
        hypotheses_generated: int,
        evaluations_done: int,
        coherence_summary: Optional[Dict] = None,
        evolution_proposals: Optional[list] = None,
    ) -> str:
        """
        Gera relatório diário.

        INTENÇÃO: Conciso, honesto, e acionável.
        """
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        report = f"""📊 **Relatório Diário — {self._personality_name}**
_{now}_

**Performance:**
- Win rate: {performance_stats.get('win_rate', 0):.1%}
- Total trades: {performance_stats.get('total_trades', 0)}
- P&L total: ${performance_stats.get('total_pnl', 0):.2f}
- Max drawdown: ${performance_stats.get('max_drawdown', 0):.2f}

**Atividade:**
- Hipóteses geradas: {hypotheses_generated}
- Avaliações realizadas: {evaluations_done}
"""

        if coherence_summary:
            report += f"""
**Coerência do Usuário:**
- Observações: {coherence_summary.get('observations', 0)}
- Score médio: {coherence_summary.get('avg_coherence', 0):.2f}
- Tendência: {coherence_summary.get('trend', 'N/A')}
"""

        if evolution_proposals:
            report += "\n**Propostas de Evolução:**\n"
            for prop in evolution_proposals:
                report += f"- {prop.get('rule_path', 'N/A')}: {prop.get('reasoning', '')[:100]}\n"

        return report

    def generate_weekly_report(
        self,
        daily_stats: list,
        patterns_discovered: int,
        patterns_deprecated: int,
        transcendence_candidates: Optional[list] = None,
    ) -> str:
        """Gera relatório semanal com visão mais ampla."""
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        report = f"""📈 **Relatório Semanal — {self._personality_name}**
_Semana terminando em {now}_

**Resumo:**
- Padrões descobertos: {patterns_discovered}
- Padrões arquivados: {patterns_deprecated}
- Dias reportados: {len(daily_stats)}
"""

        if transcendence_candidates:
            report += "\n**Candidatas a Transcendência:**\n"
            for c in transcendence_candidates:
                report += (
                    f"- {c.get('restriction_name', 'N/A')}: "
                    f"compliance {c.get('voluntary_compliance_rate', 0):.0%}\n"
                )

        return report
