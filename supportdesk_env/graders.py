from __future__ import annotations

from typing import Dict, List, Tuple

from .models import ObjectiveStatus, TicketView
from .tasks import TaskSpec, get_task_catalog


TASK_CATALOG = get_task_catalog()


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()



def _reply_keyword_hits(reply: str | None, keywords: List[str] | None) -> int:
    reply_norm = _normalize_text(reply)
    if not reply_norm or not keywords:
        return 0
    return sum(1 for kw in keywords if kw.lower() in reply_norm)



def evaluate_objectives(task: TaskSpec, tickets: List[TicketView]) -> Tuple[List[ObjectiveStatus], Dict[str, bool]]:
    ticket_map = {t.id: t for t in tickets}
    results: List[ObjectiveStatus] = []
    objective_map: Dict[str, bool] = {}

    for obj in task.objectives:
        ticket = ticket_map[obj.ticket_id]
        completed = False

        if obj.kind == "classify":
            completed = _normalize_text(ticket.predicted_category) == _normalize_text(obj.target_value)
        elif obj.kind == "prioritize":
            completed = _normalize_text(ticket.predicted_priority) == _normalize_text(obj.target_value)
        elif obj.kind == "escalate":
            completed = _normalize_text(ticket.escalation_target) == _normalize_text(obj.target_value)
        elif obj.kind == "reply":
            hits = _reply_keyword_hits(ticket.drafted_reply, obj.required_keywords)
            completed = hits >= obj.min_keyword_hits
        elif obj.kind == "resolve":
            completed = ticket.status == "resolved"

        results.append(
            ObjectiveStatus(
                objective_id=obj.objective_id,
                description=obj.description,
                completed=completed,
            )
        )
        objective_map[obj.objective_id] = completed

    return results, objective_map



def compute_score(task: TaskSpec, tickets: List[TicketView], penalty_points: float) -> float:
    _, objective_map = evaluate_objectives(task, tickets)
    total = max(len(objective_map), 1)
    achieved = sum(1 for v in objective_map.values() if v)
    raw_score = achieved / total
    return max(0.0, min(1.0, raw_score - penalty_points))



def grade_task(task: TaskSpec, tickets: List[TicketView], penalty_points: float) -> Dict[str, float | int | Dict[str, bool]]:
    objective_statuses, objective_map = evaluate_objectives(task, tickets)
    score = compute_score(task, tickets, penalty_points)
    return {
        "score": round(score, 4),
        "completed_objectives": sum(1 for v in objective_map.values() if v),
        "total_objectives": len(objective_map),
        "objective_map": objective_map,
        "completed": all(o.completed for o in objective_statuses),
    }



def grade_task_by_name(task_name: str, tickets: List[TicketView], penalty_points: float = 0.0) -> Dict[str, float | int | Dict[str, bool]]:
    if task_name not in TASK_CATALOG:
        raise ValueError(f"Unknown task_name '{task_name}'. Available tasks: {list(TASK_CATALOG)}")
    return grade_task(TASK_CATALOG[task_name], tickets, penalty_points)



def grade_easy(tickets: List[TicketView], penalty_points: float = 0.0) -> Dict[str, float | int | Dict[str, bool]]:
    return grade_task(TASK_CATALOG["easy_refund"], tickets, penalty_points)



def grade_medium(tickets: List[TicketView], penalty_points: float = 0.0) -> Dict[str, float | int | Dict[str, bool]]:
    return grade_task(TASK_CATALOG["medium_fraud_and_billing"], tickets, penalty_points)



def grade_hard(tickets: List[TicketView], penalty_points: float = 0.0) -> Dict[str, float | int | Dict[str, bool]]:
    return grade_task(TASK_CATALOG["hard_multi_queue"], tickets, penalty_points)
