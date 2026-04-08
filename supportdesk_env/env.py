from __future__ import annotations

import copy
from typing import List

from .graders import compute_score, evaluate_objectives
from .models import EnvironmentState, StepInfo, StepResult, SupportDeskAction, SupportDeskObservation, TicketView
from .tasks import TaskSpec, get_task_catalog


class SupportDeskEnv:
    """
    Real-world OpenEnv-style environment for customer support ticket triage.
    Implements reset(), step(), and state().
    """

    def __init__(self, task_name: str = "easy_refund") -> None:
        catalog = get_task_catalog()
        if task_name not in catalog:
            raise ValueError(f"Unknown task '{task_name}'. Available: {list(catalog)}")
        self.catalog = catalog
        self.task_name = task_name
        self.task: TaskSpec = catalog[task_name]
        self.max_steps = self.task.max_steps
        self.steps_taken = 0
        self.penalty_points = 0.0
        self.last_action_error: str | None = None
        self.last_action_result = "Environment created. Call reset() to begin."
        self.action_history: List[str] = []
        self.tickets: List[TicketView] = []
        self._done = False

    @classmethod
    async def create(cls, task_name: str = "easy_refund") -> "SupportDeskEnv":
        return cls(task_name=task_name)

    async def close(self) -> None:
        return None

    async def reset(self) -> StepResult:
        self.steps_taken = 0
        self.penalty_points = 0.0
        self.last_action_error = None
        self.last_action_result = "Queue loaded."
        self.action_history = []
        self._done = False
        self.tickets = [TicketView(**copy.deepcopy(t)) for t in self.task.tickets]
        observation = self._build_observation()
        info = self._build_info()
        return StepResult(observation=observation, reward=0.0, done=False, info=info)

    async def step(self, action: SupportDeskAction) -> StepResult:
        if self._done:
            observation = self._build_observation()
            info = self._build_info()
            return StepResult(observation=observation, reward=0.0, done=True, info=info)

        previous_score = compute_score(self.task, self.tickets, self.penalty_points)
        self.steps_taken += 1
        self.last_action_error = None
        self.last_action_result = "No action taken."

        try:
            self._apply_action(action)
        except ValueError as exc:
            self.last_action_error = str(exc)
            self.last_action_result = "Action failed."
            self.penalty_points = min(1.0, self.penalty_points + 0.05)

        self.action_history.append(action.model_dump_json())

        if action.action_type == "noop":
            self.penalty_points = min(1.0, self.penalty_points + 0.03)

        current_score = compute_score(self.task, self.tickets, self.penalty_points)
        reward = max(0.0, min(1.0, current_score - previous_score))

        objectives, _ = evaluate_objectives(self.task, self.tickets)
        all_done = all(o.completed for o in objectives)
        max_steps_hit = self.steps_taken >= self.max_steps
        self._done = all_done or max_steps_hit

        if max_steps_hit and not all_done:
            self.last_action_result += " Max steps reached."

        observation = self._build_observation()
        info = self._build_info()
        return StepResult(observation=observation, reward=round(reward, 4), done=self._done, info=info)

    def state(self) -> EnvironmentState:
        objectives, _ = evaluate_objectives(self.task, self.tickets)
        return EnvironmentState(
            task_name=self.task_name,
            score=compute_score(self.task, self.tickets, self.penalty_points),
            penalty_points=round(self.penalty_points, 4),
            steps_taken=self.steps_taken,
            max_steps=self.max_steps,
            tickets=self.tickets,
            completed_objectives=objectives,
            action_history=self.action_history,
            last_action_error=self.last_action_error,
        )

    def _get_ticket(self, ticket_id: str | None) -> TicketView:
        if not ticket_id:
            raise ValueError("ticket_id is required for this action.")
        for ticket in self.tickets:
            if ticket.id == ticket_id:
                return ticket
        raise ValueError(f"Unknown ticket_id '{ticket_id}'.")

    def _apply_action(self, action: SupportDeskAction) -> None:
        act = action.action_type

        if act == "noop":
            self.last_action_result = "No-op action executed."
            return

        ticket = self._get_ticket(action.ticket_id)

        if act == "classify":
            value = (action.value or "").strip().lower()
            allowed = {"billing", "shipping", "technical", "security", "compliance", "general"}
            if value not in allowed:
                raise ValueError(f"Invalid classify value '{value}'.")
            ticket.predicted_category = value  # type: ignore[assignment]
            self.last_action_result = f"Ticket {ticket.id} classified as {value}."

        elif act == "prioritize":
            value = (action.value or "").strip().lower()
            allowed = {"low", "medium", "high", "urgent"}
            if value not in allowed:
                raise ValueError(f"Invalid prioritize value '{value}'.")
            ticket.predicted_priority = value  # type: ignore[assignment]
            self.last_action_result = f"Ticket {ticket.id} priority set to {value}."

        elif act == "reply":
            message = (action.message or "").strip()
            if len(message) < 20:
                raise ValueError("Reply message must be at least 20 characters.")
            ticket.drafted_reply = message
            self.last_action_result = f"Reply drafted for ticket {ticket.id}."

        elif act == "escalate":
            value = (action.value or "").strip().lower()
            allowed = {"risk", "engineering", "privacy", "billing_ops", "shipping_ops"}
            if value not in allowed:
                raise ValueError(f"Invalid escalate value '{value}'.")
            ticket.escalation_target = value  # type: ignore[assignment]
            self.last_action_result = f"Ticket {ticket.id} escalated to {value}."

        elif act == "resolve":
            ticket.status = "resolved"
            self.last_action_result = f"Ticket {ticket.id} resolved."

        else:
            raise ValueError(f"Unsupported action_type '{act}'.")

        self._apply_behavior_penalties(action, ticket)

    def _apply_behavior_penalties(self, action: SupportDeskAction, ticket: TicketView) -> None:
        if action.action_type == "resolve" and not ticket.drafted_reply:
            self.penalty_points = min(1.0, self.penalty_points + 0.07)

        if action.action_type == "escalate":
            value = (action.value or "").strip().lower()
            if ticket.id == "T1" and self.task_name == "medium_fraud_and_billing" and value != "risk":
                self.penalty_points = min(1.0, self.penalty_points + 0.08)
            if ticket.id == "T1" and self.task_name == "hard_multi_queue" and value != "engineering":
                self.penalty_points = min(1.0, self.penalty_points + 0.08)
            if ticket.id == "T2" and self.task_name == "hard_multi_queue" and value != "privacy":
                self.penalty_points = min(1.0, self.penalty_points + 0.08)

    def _build_observation(self) -> SupportDeskObservation:
        objectives, _ = evaluate_objectives(self.task, self.tickets)
        return SupportDeskObservation(
            task_name=self.task.name,
            task_description=self.task.description,
            instructions=self.task.instructions,
            queue=self.tickets,
            completed_objectives=objectives,
            remaining_steps=max(self.max_steps - self.steps_taken, 0),
            last_action_result=self.last_action_result,
            last_action_error=self.last_action_error,
        )

    def _build_info(self) -> StepInfo:
        objectives, objective_map = evaluate_objectives(self.task, self.tickets)
        completed = all(o.completed for o in objectives)
        return StepInfo(
            score=round(compute_score(self.task, self.tickets, self.penalty_points), 4),
            penalty_points=round(self.penalty_points, 4),
            steps_taken=self.steps_taken,
            max_steps=self.max_steps,
            task_name=self.task_name,
            completed=completed,
            objective_map=objective_map,
        )
