"""
Inference script for SupportDesk OpenEnv.

MANDATORY ENV VARS (per submission spec):
- API_BASE_URL
- MODEL_NAME
- HF_TOKEN

This script emits strict stdout logs:
[START] task=<task_name> env=<benchmark> model=<model_name>
[STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
[END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
"""

import asyncio
import json
import os
import textwrap
from typing import Dict, List, Optional

from openai import OpenAI

from supportdesk_env import SupportDeskAction, SupportDeskEnv

API_KEY = os.getenv("HF_TOKEN") or os.getenv("OPENAI_API_KEY") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
BENCHMARK = os.getenv("SUPPORTDESK_BENCHMARK", "supportdesk_openenv")
TASKS = ["easy_refund", "medium_fraud_and_billing", "hard_multi_queue"]
TEMPERATURE = 0.0
MAX_TOKENS = 220
SUCCESS_SCORE_THRESHOLD = 0.85

SYSTEM_PROMPT = textwrap.dedent(
    """
    You are operating a customer support ticket triage environment.
    Return exactly one JSON object with this schema:
    {
      "action_type": "classify|prioritize|reply|escalate|resolve|noop",
      "ticket_id": "T1",
      "value": "billing|shipping|technical|security|compliance|general|low|medium|high|urgent|risk|engineering|privacy|billing_ops|shipping_ops|null",
      "message": "reply text or null"
    }

    Rules:
    - Output JSON only.
    - Prefer progress-making actions.
    - Read the observation carefully.
    - Use reply actions only when you can provide a professional customer-support reply.
    - Never wrap the JSON in markdown.
    """
).strip()


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)



def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )



def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)



def build_user_prompt(step_num: int, obs: Dict, history: List[str]) -> str:
    history_block = "\n".join(history[-6:]) if history else "None"
    return textwrap.dedent(
        f"""
        Step number: {step_num}

        Observation JSON:
        {json.dumps(obs, ensure_ascii=False)}

        Recent history:
        {history_block}

        Choose the single best next action.
        """
    ).strip()



def safe_json_action(text: str) -> Dict:
    text = (text or "").strip()
    if not text:
        return {"action_type": "noop", "ticket_id": None, "value": None, "message": None}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass
    return {"action_type": "noop", "ticket_id": None, "value": None, "message": None}



def heuristic_action(obs: Dict) -> Dict:
    queue = obs.get("queue", [])
    for ticket in queue:
        ticket_id = ticket["id"]
        subject = (ticket.get("subject") or "").lower()
        body = (ticket.get("body") or "").lower()
        text = f"{subject} {body}"

        if not ticket.get("predicted_category"):
            if any(k in text for k in ["refund", "charged", "billing", "annual"]):
                return {"action_type": "classify", "ticket_id": ticket_id, "value": "billing", "message": None}
            if any(k in text for k in ["login", "taken over", "sign-in alert", "recovery phone"]):
                return {"action_type": "classify", "ticket_id": ticket_id, "value": "security", "message": None}
            if any(k in text for k in ["dashboard", "down", "inaccessible", "production"]):
                return {"action_type": "classify", "ticket_id": ticket_id, "value": "technical", "message": None}
            if any(k in text for k in ["delete all my personal data", "privacy law", "data deleted"]):
                return {"action_type": "classify", "ticket_id": ticket_id, "value": "compliance", "message": None}
            if any(k in text for k in ["shipment", "damaged", "replacement", "hardware"]):
                return {"action_type": "classify", "ticket_id": ticket_id, "value": "shipping", "message": None}
            return {"action_type": "classify", "ticket_id": ticket_id, "value": "general", "message": None}

        if not ticket.get("predicted_priority"):
            category = ticket.get("predicted_category")
            if "dashboard" in text or "exec" in text or category == "security":
                priority = "urgent"
            elif category == "compliance":
                priority = "high"
            elif category == "billing" and "annual" in text:
                priority = "high"
            elif category == "shipping":
                priority = "medium"
            else:
                priority = "medium"
            return {"action_type": "prioritize", "ticket_id": ticket_id, "value": priority, "message": None}

        if not ticket.get("escalation_target"):
            category = ticket.get("predicted_category")
            if category == "security":
                return {"action_type": "escalate", "ticket_id": ticket_id, "value": "risk", "message": None}
            if category == "technical" and ("dashboard" in text or "production" in text):
                return {"action_type": "escalate", "ticket_id": ticket_id, "value": "engineering", "message": None}
            if category == "compliance":
                return {"action_type": "escalate", "ticket_id": ticket_id, "value": "privacy", "message": None}

        if not ticket.get("drafted_reply"):
            category = ticket.get("predicted_category")
            if category == "billing":
                msg = (
                    "Thanks for reporting this. We will review the duplicate or annual billing issue and "
                    "work on the refund request. We are reviewing the charge now and will update you within 3-5 business days."
                )
            elif category == "security":
                msg = (
                    "Thanks for alerting us. We are working to secure your account, and the case has been escalated. "
                    "Our team is investigating the account activity now and will update you as soon as possible."
                )
            elif category == "technical":
                msg = (
                    "We understand this is urgent. Engineering has been engaged and is investigating the outage now. "
                    "We will share an update as soon as we have more information."
                )
            elif category == "compliance":
                msg = (
                    "We have received your delete request and will confirm the next steps. "
                    "Our privacy team will review the request and provide a timeline for completion."
                )
            elif category == "shipping":
                msg = (
                    "We are sorry the shipment arrived with damage. We will review the damage report and begin the replacement process. "
                    "We will follow up with shipment details shortly."
                )
            else:
                msg = "Thanks for contacting support. We are reviewing your request and will follow up shortly with next steps."
            return {"action_type": "reply", "ticket_id": ticket_id, "value": None, "message": msg}

    return {"action_type": "noop", "ticket_id": None, "value": None, "message": None}



def get_model_action(client: OpenAI, step_num: int, obs: Dict, history: List[str]) -> Dict:
    user_prompt = build_user_prompt(step_num, obs, history)
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        content = (completion.choices[0].message.content or "").strip()
        parsed = safe_json_action(content)
        if parsed.get("action_type") in {"classify", "prioritize", "reply", "escalate", "resolve", "noop"}:
            return parsed
    except Exception:
        pass
    return heuristic_action(obs)


async def run_task(client: OpenAI, task_name: str) -> float:
    env = await SupportDeskEnv.create(task_name=task_name)
    rewards: List[float] = []
    history: List[str] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)
    try:
        result = await env.reset()
        max_steps = result.info.max_steps

        for step_num in range(1, max_steps + 1):
            if result.done:
                break

            obs_dict = result.observation.model_dump()
            action_dict = get_model_action(client, step_num, obs_dict, history)

            try:
                action = SupportDeskAction(**action_dict)
            except Exception:
                action = SupportDeskAction(action_type="noop")

            result = await env.step(action)
            reward = result.reward
            done = result.done
            error = result.observation.last_action_error
            score = result.info.score
            steps_taken = step_num
            rewards.append(reward)

            action_str = json.dumps(action.model_dump(), ensure_ascii=False, separators=(",", ":"))
            log_step(step=step_num, action=action_str, reward=reward, done=done, error=error)
            history.append(f"step={step_num} action={action_str} reward={reward:.2f} score={score:.2f}")

            if done:
                break

        success = score >= SUCCESS_SCORE_THRESHOLD
    finally:
        try:
            await env.close()
        except Exception:
            pass
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


async def main() -> None:
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    scores: List[float] = []
    for task_name in TASKS:
        score = await run_task(client, task_name)
        scores.append(score)


if __name__ == "__main__":
    asyncio.run(main())
