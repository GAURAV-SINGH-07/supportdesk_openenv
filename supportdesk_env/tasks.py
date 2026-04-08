from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class ObjectiveSpec:
    objective_id: str
    description: str
    kind: str
    ticket_id: str
    target_value: str | None = None
    required_keywords: List[str] | None = None
    min_keyword_hits: int = 0


@dataclass(frozen=True)
class TaskSpec:
    name: str
    description: str
    instructions: str
    max_steps: int
    tickets: List[dict]
    objectives: List[ObjectiveSpec]



def get_task_catalog() -> Dict[str, TaskSpec]:
    return {
        "easy_refund": TaskSpec(
            name="easy_refund",
            description="Triage a single refund request and send an appropriate response.",
            instructions=(
                "Handle the ticket like a real support agent. "
                "Classify the issue, set an appropriate priority, and draft a useful reply."
            ),
            max_steps=6,
            tickets=[
                {
                    "id": "T1",
                    "customer_tier": "standard",
                    "channel": "email",
                    "subject": "Charged twice for the same subscription renewal",
                    "body": (
                        "Hi team, I was charged twice today for my monthly subscription. "
                        "Please refund the duplicate charge. My account is under the same email."
                    ),
                }
            ],
            objectives=[
                ObjectiveSpec("obj1", "Classify ticket T1 as billing", "classify", "T1", target_value="billing"),
                ObjectiveSpec("obj2", "Set T1 priority to medium", "prioritize", "T1", target_value="medium"),
                ObjectiveSpec(
                    "obj3",
                    "Reply to T1 with a refund-oriented response",
                    "reply",
                    "T1",
                    required_keywords=["refund", "duplicate", "review", "3-5 business days"],
                    min_keyword_hits=2,
                ),
            ],
        ),
        "medium_fraud_and_billing": TaskSpec(
            name="medium_fraud_and_billing",
            description="Handle a possible account compromise and a billing complaint in the same queue.",
            instructions=(
                "Work the queue safely. Urgent security-related issues should be escalated correctly. "
                "Billing issues still need a clear, useful reply."
            ),
            max_steps=9,
            tickets=[
                {
                    "id": "T1",
                    "customer_tier": "business",
                    "channel": "web",
                    "subject": "Unknown login and changed phone number on my account",
                    "body": (
                        "I got a sign-in alert from a city I have never visited, and now my recovery phone number "
                        "looks different. I think my account has been taken over."
                    ),
                },
                {
                    "id": "T2",
                    "customer_tier": "standard",
                    "channel": "email",
                    "subject": "Need refund for annual plan after accidental upgrade",
                    "body": (
                        "I accidentally upgraded to annual billing instead of monthly. "
                        "Can you help reverse this and refund the annual charge?"
                    ),
                },
            ],
            objectives=[
                ObjectiveSpec("obj1", "Classify T1 as security", "classify", "T1", target_value="security"),
                ObjectiveSpec("obj2", "Set T1 priority to urgent", "prioritize", "T1", target_value="urgent"),
                ObjectiveSpec("obj3", "Escalate T1 to risk", "escalate", "T1", target_value="risk"),
                ObjectiveSpec(
                    "obj4",
                    "Reply to T1 with a security-conscious message",
                    "reply",
                    "T1",
                    required_keywords=["secure", "account", "investigating", "escalated"],
                    min_keyword_hits=2,
                ),
                ObjectiveSpec("obj5", "Classify T2 as billing", "classify", "T2", target_value="billing"),
                ObjectiveSpec("obj6", "Set T2 priority to high", "prioritize", "T2", target_value="high"),
                ObjectiveSpec(
                    "obj7",
                    "Reply to T2 with a refund-oriented billing response",
                    "reply",
                    "T2",
                    required_keywords=["refund", "annual", "billing", "review"],
                    min_keyword_hits=2,
                ),
            ],
        ),
        "hard_multi_queue": TaskSpec(
            name="hard_multi_queue",
            description="Handle a mixed queue with outage, privacy, and shipping issues.",
            instructions=(
                "Act like a strong real-world agent: triage correctly, escalate where appropriate, "
                "and send professional replies. Prioritize urgent business impact first."
            ),
            max_steps=12,
            tickets=[
                {
                    "id": "T1",
                    "customer_tier": "vip",
                    "channel": "chat",
                    "subject": "Production dashboard is down for our whole exec team",
                    "body": (
                        "Our executive dashboard has been inaccessible for 20 minutes and a board review starts soon. "
                        "We need immediate help."
                    ),
                },
                {
                    "id": "T2",
                    "customer_tier": "standard",
                    "channel": "web",
                    "subject": "Please delete all my personal data under privacy law",
                    "body": (
                        "I want all my account data deleted permanently. "
                        "Please confirm what happens next and how long this takes."
                    ),
                },
                {
                    "id": "T3",
                    "customer_tier": "business",
                    "channel": "email",
                    "subject": "Replacement needed for damaged shipment",
                    "body": (
                        "The hardware arrived with visible damage and cannot be used. "
                        "We need a replacement shipped quickly."
                    ),
                },
            ],
            objectives=[
                ObjectiveSpec("obj1", "Classify T1 as technical", "classify", "T1", target_value="technical"),
                ObjectiveSpec("obj2", "Set T1 priority to urgent", "prioritize", "T1", target_value="urgent"),
                ObjectiveSpec("obj3", "Escalate T1 to engineering", "escalate", "T1", target_value="engineering"),
                ObjectiveSpec(
                    "obj4",
                    "Reply to T1 with outage-response language",
                    "reply",
                    "T1",
                    required_keywords=["investigating", "urgent", "engineering", "update"],
                    min_keyword_hits=2,
                ),
                ObjectiveSpec("obj5", "Classify T2 as compliance", "classify", "T2", target_value="compliance"),
                ObjectiveSpec("obj6", "Set T2 priority to high", "prioritize", "T2", target_value="high"),
                ObjectiveSpec("obj7", "Escalate T2 to privacy", "escalate", "T2", target_value="privacy"),
                ObjectiveSpec(
                    "obj8",
                    "Reply to T2 with privacy-request language",
                    "reply",
                    "T2",
                    required_keywords=["delete", "request", "confirm", "timeline"],
                    min_keyword_hits=2,
                ),
                ObjectiveSpec("obj9", "Classify T3 as shipping", "classify", "T3", target_value="shipping"),
                ObjectiveSpec("obj10", "Set T3 priority to medium", "prioritize", "T3", target_value="medium"),
                ObjectiveSpec(
                    "obj11",
                    "Reply to T3 with replacement logistics language",
                    "reply",
                    "T3",
                    required_keywords=["replacement", "damage", "shipment", "review"],
                    min_keyword_hits=2,
                ),
            ],
        ),
    }
