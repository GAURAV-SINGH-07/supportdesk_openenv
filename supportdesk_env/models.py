from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field


ActionType = Literal["classify", "prioritize", "reply", "escalate", "resolve", "noop"]
PriorityType = Literal["low", "medium", "high", "urgent"]
CategoryType = Literal["billing", "shipping", "technical", "security", "compliance", "general"]
EscalationType = Literal["risk", "engineering", "privacy", "billing_ops", "shipping_ops"]


class TicketView(BaseModel):
    id: str
    customer_tier: Literal["standard", "business", "vip"]
    channel: Literal["email", "chat", "web"]
    subject: str
    body: str
    status: Literal["open", "resolved"] = "open"
    predicted_category: Optional[CategoryType] = None
    predicted_priority: Optional[PriorityType] = None
    escalation_target: Optional[EscalationType] = None
    drafted_reply: Optional[str] = None


class ObjectiveStatus(BaseModel):
    objective_id: str
    description: str
    completed: bool = False


class SupportDeskObservation(BaseModel):
    task_name: str
    task_description: str
    instructions: str
    queue: List[TicketView]
    completed_objectives: List[ObjectiveStatus]
    remaining_steps: int
    last_action_result: str
    last_action_error: Optional[str] = None


class SupportDeskAction(BaseModel):
    action_type: ActionType = Field(..., description="One of classify, prioritize, reply, escalate, resolve, noop")
    ticket_id: Optional[str] = Field(default=None, description="Ticket identifier for the action")
    value: Optional[str] = Field(default=None, description="Category, priority, escalation team, or resolve reason")
    message: Optional[str] = Field(default=None, description="Reply text for reply actions")


class SupportDeskReward(BaseModel):
    value: float = Field(..., ge=0.0, le=1.0)
    reasoning: str


class StepInfo(BaseModel):
    score: float = Field(..., gt=0.0, lt=1.0)
    penalty_points: float = Field(..., ge=0.0, le=1.0)
    steps_taken: int
    max_steps: int
    task_name: str
    completed: bool
    objective_map: Dict[str, bool]


class StepResult(BaseModel):
    observation: SupportDeskObservation
    reward: float = Field(..., ge=0.0, le=1.0)
    done: bool
    info: StepInfo


class EnvironmentState(BaseModel):
    task_name: str
    score: float = Field(..., gt=0.0, lt=1.0)
    penalty_points: float = Field(..., ge=0.0, le=1.0)
    steps_taken: int
    max_steps: int
    tickets: List[TicketView]
    completed_objectives: List[ObjectiveStatus]
    action_history: List[str]
    last_action_error: Optional[str] = None
