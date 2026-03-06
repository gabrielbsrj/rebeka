# shared/intent/growth_horizon.py
# VERSION: 1.0.1
# LAST_MODIFIED: 2026-02-25
# CHANGELOG: v1.0.1 — Fixed timezone awareness bug in _get_current_week

import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional

from shared.database.causal_bank import CausalBank

logger = logging.getLogger(__name__)


class GrowthHorizon:
    """
    Monitor de horizonte de crescimento.
    """

    def __init__(self, causal_bank: CausalBank):
        self.bank = causal_bank

    def declare_growth_target(
        self,
        domain: str,
        current_state: str,
        desired_future: str,
        progress_metrics: List[str],
        deadline_days: Optional[int] = None,
    ) -> str:
        target_data = {
            "domain": domain,
            "current_state_declared": current_state,
            "desired_future_state": desired_future,
            "progress_metrics": {m: None for m in progress_metrics},
            "target_deadline": (
                datetime.now(timezone.utc) + timedelta(days=deadline_days)
                if deadline_days else None
            ),
            "active": True,
        }

        target_id = self.bank.insert_growth_target(target_data)
        logger.info(f"Horizonte de crescimento declarado: {domain} -> {desired_future}")
        return target_id

    def update_progress(
        self,
        target_id: str,
        metrics_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        targets = self.bank.get_active_growth_targets()
        target = next((t for t in targets if t["id"] == target_id), None)

        if not target:
            logger.warning(f"Alvo não encontrado: {target_id}")
            return {"error": "target_not_found"}

        desired_metrics = target.get("metrics", {})
        
        distance = self._calculate_distance(metrics_snapshot, desired_metrics)
        trend = self._calculate_trend(target_id, metrics_snapshot)
        
        notes = self._generate_notes(distance, trend, metrics_snapshot)

        progress_data = {
            "target_id": target_id,
            "week_number": self._get_current_week(target["created_at"]),
            "metrics_snapshot": metrics_snapshot,
            "distance_from_goal": distance,
            "trend": trend,
            "system_notes": notes,
        }

        self.bank.insert_growth_progress(progress_data)
        return {
            "distance": distance,
            "trend": trend,
            "notes": notes,
        }

    def get_weekly_report(self, target_id: Optional[str] = None) -> Dict[str, Any]:
        targets = self.bank.get_active_growth_targets()
        if target_id:
            targets = [t for t in targets if t["id"] == target_id]

        if not targets:
            return {"status": "no_active_targets", "targets": []}

        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "targets": []
        }

        for target in targets:
            history = self.bank.get_growth_progress_history(target["id"])
            
            if history:
                latest = history[0]
                target_report = {
                    "domain": target["domain"],
                    "current_state": target["current_state"],
                    "desired_state": target["desired_state"],
                    "week": latest.get("week", 1),
                    "metrics": latest.get("metrics", {}),
                    "distance": latest.get("distance", 1.0),
                    "trend": latest.get("trend", "unknown"),
                    "total_weeks_tracked": len(history),
                }
            else:
                target_report = {
                    "domain": target["domain"],
                    "current_state": target["current_state"],
                    "desired_state": target["desired_state"],
                    "status": "primeira_semana",
                }
            report["targets"].append(target_report)

        return report

    def _calculate_distance(self, current: Dict, target: Dict) -> float:
        """Calcula distância normalizada (0.0 a 1.0) entre estado atual e meta."""
        if not target:
            return 0.5
            
        distances = []
        for key, target_val in target.items():
            current_val = current.get(key, 0)
            
            # Se for número, calcula distância %
            if isinstance(target_val, (int, float)) and target_val != 0:
                try:
                    dist = abs(current_val - target_val) / abs(target_val)
                    distances.append(min(1.0, float(dist)))
                except Exception:
                    distances.append(1.0)
            # Se for boolean ou string exata
            elif target_val is not None:
                distances.append(0.0 if current_val == target_val else 1.0)
                
        if not distances:
            return 0.5
            
        return sum(distances) / len(distances)

    def _calculate_trend(self, target_id: str, current: Dict) -> str:
        history = self.bank.get_growth_progress_history(target_id)
        if len(history) < 2:
            return "iniciando"
        return "improving"

    def _get_current_week(self, created_at_iso: str) -> int:
        created = datetime.fromisoformat(created_at_iso)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - created).days
        return max(1, days // 7 + 1)

    def _generate_notes(self, distance: float, trend: str, metrics: Dict) -> str:
        return "Progresso monitorado."

    def propose_growth_conversation(self, target_id: Optional[str] = None) -> Optional[str]:
        return "Quer conversar sobre seu progresso em trading?"
