import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class EpisodicTaskMemory:
    """
    Memoria episodica operacional para os focos ativos do workspace global.

    Cada foco relevante ganha um episodio curto composto por:
    - um plano de orquestracao persistido no CausalBank;
    - uma tarefa ativa representando a frente operacional em andamento;
    - um estado em memoria para manter continuidade entre snapshots.
    """

    ACTION_EXECUTORS = {
        "alert": "survival_guard",
        "research": "market_analyst",
        "follow_up": "relationship_manager",
        "plan": "strategy_planner",
        "monitor": "signal_monitor",
    }

    def __init__(self, bank, chat_manager, max_open_episodes: int = 3):
        self.bank = bank
        self.chat_manager = chat_manager
        self.max_open_episodes = max_open_episodes
        self.active_episodes: Dict[str, Dict[str, Any]] = {}

    async def synchronize_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        focuses = list(snapshot.get("focuses", []))[: self.max_open_episodes]
        active_focus_ids = set()
        opened: List[Dict[str, Any]] = []
        refreshed: List[str] = []
        closed: List[Dict[str, Any]] = []

        for focus in focuses:
            focus_id = focus["focus_id"]
            active_focus_ids.add(focus_id)

            if focus_id in self.active_episodes:
                self._refresh_episode(focus, snapshot)
                refreshed.append(focus_id)
                continue

            episode = self._open_episode(focus, snapshot)
            opened.append(episode)

        stale_focus_ids = [focus_id for focus_id in list(self.active_episodes.keys()) if focus_id not in active_focus_ids]
        for focus_id in stale_focus_ids:
            closed_episode = self.close_episode(
                focus_id,
                outcome="Foco saiu do workspace ativo.",
                success=True,
            )
            if closed_episode:
                closed.append(closed_episode)

        return {
            "opened": opened,
            "refreshed": refreshed,
            "closed": closed,
            "active_focus_ids": sorted(active_focus_ids),
        }

    def mark_episode_outcome(self, focus_id: str, outcome: str, success: bool = True) -> Optional[Dict[str, Any]]:
        return self.close_episode(focus_id=focus_id, outcome=outcome, success=success)

    def close_episode(self, focus_id: str, outcome: str, success: bool = True) -> Optional[Dict[str, Any]]:
        episode = self.active_episodes.pop(focus_id, None)
        if not episode:
            return None

        task_status = "completed" if success else "failed"
        plan_status = "completed" if success else "failed"
        output = self._format_episode_outcome(episode, outcome, success)

        self.bank.update_task_execution(
            episode["task_id"],
            task_status,
            output=output,
            success=success,
        )
        self.bank.update_plan_status(episode["plan_id"], plan_status)

        self.chat_manager.push_insight(
            f"Memoria episodica encerrou '{episode['title']}' com status {task_status}."
        )

        return {
            "focus_id": focus_id,
            "plan_id": episode["plan_id"],
            "task_id": episode["task_id"],
            "status": task_status,
            "outcome": outcome,
        }

    def _open_episode(self, focus: Dict[str, Any], snapshot: Dict[str, Any]) -> Dict[str, Any]:
        plan_id = self._stable_episode_id("plan", focus["focus_id"])
        component_id = self._stable_episode_id("component", focus["focus_id"])
        task_id = self._stable_episode_id("task", focus["focus_id"])
        executor_id = self._resolve_executor(focus)
        instruction = self._build_instruction(focus)

        self.bank.insert_orchestration_plan(
            {
                "id": plan_id,
                "original_idea": focus["summary"],
                "central_objective": self._build_objective(focus),
                "final_deliverable": self._build_deliverable(focus),
                "components": [self._build_component(component_id, focus, executor_id)],
                "sequence": [{"phase": "active_focus", "components": [component_id]}],
                "status": "executing",
            }
        )

        self.bank.insert_task_execution(
            {
                "id": task_id,
                "plan_id": plan_id,
                "component_id": component_id,
                "executor_id": executor_id,
                "instruction_sent": instruction,
                "status": "running",
            }
        )

        episode = {
            "focus_id": focus["focus_id"],
            "plan_id": plan_id,
            "task_id": task_id,
            "component_id": component_id,
            "executor_id": executor_id,
            "instruction": instruction,
            "title": focus["title"],
            "domain": focus["domain"],
            "kind": focus["kind"],
            "priority": float(focus["priority"]),
            "recommended_action": focus["recommended_action"],
            "snapshot_signature": snapshot.get("signature"),
            "last_seen_at": snapshot.get("timestamp") or self._now_iso(),
        }
        self.active_episodes[focus["focus_id"]] = episode

        self.chat_manager.push_insight(
            f"Memoria episodica abriu frente para '{focus['title']}' [{focus['domain']}] via {executor_id}."
        )
        logger.info("Episodio aberto para foco %s", focus["focus_id"])
        return episode

    def _refresh_episode(self, focus: Dict[str, Any], snapshot: Dict[str, Any]) -> None:
        episode = self.active_episodes[focus["focus_id"]]
        episode["priority"] = float(focus["priority"])
        episode["snapshot_signature"] = snapshot.get("signature")
        episode["last_seen_at"] = snapshot.get("timestamp") or self._now_iso()
        episode["recommended_action"] = focus["recommended_action"]
        episode["title"] = focus["title"]
        episode["domain"] = focus["domain"]

    def _resolve_executor(self, focus: Dict[str, Any]) -> str:
        return self.ACTION_EXECUTORS.get(focus.get("recommended_action"), "signal_monitor")

    def _build_component(self, component_id: str, focus: Dict[str, Any], executor_id: str) -> Dict[str, Any]:
        return {
            "id": component_id,
            "nome": f"Gerir foco: {focus['title']}",
            "executor": executor_id,
            "status": "running",
            "focus_id": focus["focus_id"],
            "kind": focus["kind"],
            "domain": focus["domain"],
            "priority": float(focus["priority"]),
            "recommended_action": focus["recommended_action"],
        }

    def _build_objective(self, focus: Dict[str, Any]) -> str:
        return f"Responder com continuidade ao foco '{focus['title']}' no dominio {focus['domain']}."

    def _build_deliverable(self, focus: Dict[str, Any]) -> str:
        return (
            "Registrar o estado da frente, a acao sugerida e o resultado operacional "
            f"para '{focus['title']}'."
        )

    def _build_instruction(self, focus: Dict[str, Any]) -> str:
        return (
            f"Acompanhe o foco '{focus['title']}' no dominio {focus['domain']}. "
            f"Acao principal: {focus['recommended_action']}. "
            f"Resumo: {focus['summary']}"
        )

    def _format_episode_outcome(self, episode: Dict[str, Any], outcome: str, success: bool) -> str:
        result = "sucesso" if success else "falha"
        return (
            f"Episodio '{episode['title']}' encerrado com {result}. "
            f"Resultado: {outcome}"
        )

    def _stable_episode_id(self, prefix: str, focus_id: str) -> str:
        payload = f"{prefix}:{focus_id}"
        return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:20]

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()