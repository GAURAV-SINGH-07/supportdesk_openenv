---
title: SupportDesk OpenEnv
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# SupportDesk OpenEnv

A real-world OpenEnv environment for evaluating AI agents on customer support operations.

## Why this environment?

Many agent benchmarks are toy environments. This one simulates a real support workflow that humans actually perform:

- classify incoming tickets
- set priority correctly
- escalate risky issues
- draft professional customer replies

This makes it useful for evaluating planning, tool use, multi-step progress, and safety-aware decision-making.

## Requirements coverage

This project is designed to satisfy the submission requirements you shared:

- real-world task simulation
- typed models for observation, action, and reward
- `reset()`, `step()`, and `state()` implemented
- `openenv.yaml` included
- 3 tasks with deterministic graders
- partial-progress reward shaping
- root `inference.py` using the OpenAI client
- Dockerfile for clean containerized execution
- Hugging Face Space friendly FastAPI app

## Environment summary

**Name:** `supportdesk_openenv`  
**Domain:** customer support / ticket triage  
**Interface:** `reset()`, `step(action)`, `state()`  
**Deployment target:** Hugging Face Space (Docker)

## Action space

The environment accepts a typed `SupportDeskAction` object.

### Fields

- `action_type`: one of
  - `classify`
  - `prioritize`
  - `reply`
  - `escalate`
  - `resolve`
  - `noop`
- `ticket_id`: target ticket like `T1`, `T2`, `T3`
- `value`: used for classification, priority, escalation, or resolve reason
- `message`: used for `reply`

### Valid values

#### Categories
- `billing`
- `shipping`
- `technical`
- `security`
- `compliance`
- `general`

#### Priorities
- `low`
- `medium`
- `high`
- `urgent`

#### Escalation targets
- `risk`
- `engineering`
- `privacy`
- `billing_ops`
- `shipping_ops`

## Observation space

The environment returns a typed `SupportDeskObservation` object containing:

- `task_name`
- `task_description`
- `instructions`
- `queue` of visible tickets
- `completed_objectives`
- `remaining_steps`
- `last_action_result`
- `last_action_error`

Each ticket includes:

- ticket id
- customer tier
- channel
- subject
- body
- status
- predicted category
- predicted priority
- escalation target
- drafted reply

## Reward design

Reward is shaped over the full trajectory.

### Positive signal
The environment gives incremental reward when the agent newly completes one or more hidden objectives:

- correct classification
- correct priority
- correct escalation
- useful reply containing key operational content

### Penalties
Penalty points reduce final score for clearly undesirable behavior:

- invalid actions
- repeated no-op behavior
- resolving without replying
- escalating urgent issues to the wrong team

### Score range
- task score is always clamped to `[0.0, 1.0]`
- step reward is always clamped to `[0.0, 1.0]`

## Tasks

### 1. `easy_refund`
Difficulty: easy

A customer was charged twice and wants a refund.

Expected agent behavior:
- classify as billing
- set priority to medium
- send a refund-oriented reply

### 2. `medium_fraud_and_billing`
Difficulty: medium

The queue contains:
- a suspected account takeover
- an accidental annual billing upgrade

Expected agent behavior:
- correctly triage both tickets
- urgently escalate the security issue to risk
- reply appropriately to both users

### 3. `hard_multi_queue`
Difficulty: hard

The queue contains:
- a VIP production outage
- a privacy deletion request
- a damaged shipment

Expected agent behavior:
- prioritize urgent business impact correctly
- escalate outage to engineering
- escalate privacy request to privacy
- respond professionally across multiple issue types

## Deterministic graders

The package exposes:

- `grade_easy(...)`
- `grade_medium(...)`
- `grade_hard(...)`
- `grade_task_by_name(...)`

These graders return a normalized score in `[0.0, 1.0]` and objective completion details.

## Project structure

```text
.
├── Dockerfile
├── README.md
├── inference.py
├── openenv.yaml
├── requirements.txt
├── server.py
├── scripts
│   └── validate-submission.sh
└── supportdesk_env
    ├── __init__.py
    ├── env.py
    ├── graders.py
    ├── models.py
    └── tasks.py
```

## Local setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the environment server

```bash
uvicorn server:app --host 0.0.0.0 --port 7860
```

### 3. Test reset endpoint

```bash
curl -X POST http://localhost:7860/reset -H "Content-Type: application/json" -d '{}'
```

### 4. Test state endpoint

```bash
curl http://localhost:7860/state
```

## Docker usage

### Build

```bash
docker build -t supportdesk-openenv .
```

### Run

```bash
docker run -p 7860:7860 supportdesk-openenv
```

## Hugging Face Space deployment

Create a **Docker Space**, upload this repository, and tag the Space with:

- `openenv`

The app listens on port `7860`, which works for HF Spaces.

## Inference script

The root-level file `inference.py` follows the required stdout format and runs all 3 tasks in sequence.

### Required environment variables

- `API_BASE_URL`
- `MODEL_NAME`
- `HF_TOKEN`

### Optional environment variables

- `SUPPORTDESK_BENCHMARK`

### Example run

```bash
export HF_TOKEN=your_token_here
export API_BASE_URL=https://router.huggingface.co/v1
export MODEL_NAME=Qwen/Qwen2.5-72B-Instruct

python inference.py
```

## Example baseline behavior

The inference script uses the OpenAI client for all model calls and includes a deterministic heuristic fallback if the returned payload is malformed. This makes the script more stable during validation while still satisfying the requirement to use the OpenAI client.

You should record your actual baseline scores after running the script in your target setup and then update this README with measured numbers.

## Validation checklist

### Suggested checks

```bash
docker build -t supportdesk-openenv .
python inference.py
```

If you have the OpenEnv CLI installed:

```bash
openenv validate
```

### Space ping validation

```bash
curl -X POST https://YOUR-SPACE.hf.space/reset -H "Content-Type: application/json" -d '{}'
```

## Notes

Because OpenEnv validators can vary slightly by version, `openenv.yaml` may require a minor field-name adjustment depending on the exact validator release you use. The environment logic, typed models, HTTP endpoints, Docker setup, and baseline script are all included and ready to test.
