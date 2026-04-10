---

title: SupportDesk OpenEnv
emoji: 🚀
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
---

# 🛠️ SupportDesk OpenEnv

A **real-world customer support ticket triage environment** built for the **Meta PyTorch OpenEnv Hackathon**.

This environment simulates realistic support workflows where an agent must:

* classify tickets
* prioritize them
* escalate when needed
* respond appropriately

---

## 🚀 Live Deployment

🔗 Hugging Face Space:
https://huggingface.co/spaces/Gaurav217/supportdesk-openenv

🌐 API Base URL:
https://Gaurav217-supportdesk-openenv.hf.space

---

## 🎯 Tasks

The environment includes **3 progressively complex tasks**:

### 1. Easy — Refund Handling

* Single ticket
* Billing classification
* Medium priority
* Refund-focused response

### 2. Medium — Fraud + Billing

* Multi-ticket handling
* Security + billing mix
* Escalation required
* Multi-step reasoning

### 3. Hard — Multi-Queue Workflow

* Multiple tickets across domains:

  * Technical
  * Compliance
  * Shipping
* Requires prioritization, escalation, and sequencing

---

## ⚙️ API Endpoints

### `POST /reset`

Initialize a new task

```bash
curl -X POST https://Gaurav217-supportdesk-openenv.hf.space/reset -H "Content-Type: application/json" -d "{}"
```

---

### `POST /step`

Take an action

```bash
curl -X POST https://Gaurav217-supportdesk-openenv.hf.space/step \
-H "Content-Type: application/json" \
-d "{\"action_type\":\"classify\",\"ticket_id\":\"T1\",\"value\":\"billing\"}"
```

---

### `GET /state`

Get current environment state

```bash
curl https://Gaurav217-supportdesk-openenv.hf.space/state
```

---

### `GET /healthz`

Health check

```bash
curl https://Gaurav217-supportdesk-openenv.hf.space/healthz
```

---

## 🧠 Environment Design

* Deterministic reward system
* Objective-based scoring
* Step-by-step state transitions
* Realistic ticket simulation

Each task defines:

* objectives
* expected actions
* reward shaping

---

## 🤖 Inference

Run the baseline agent:

```bash
python inference.py
```

### Required environment variables:

```bash
API_BASE_URL=https://router.huggingface.co/v1
MODEL_NAME=Qwen/Qwen2.5-72B-Instruct
HF_TOKEN=your_token_here
```

---

## 🐳 Docker

Build and run locally:

```bash
docker build -t supportdesk-openenv .
docker run -p 7860:7860 supportdesk-openenv
```

---

## 📦 Project Structure

```text
.
├── Dockerfile
├── README.md
├── openenv.yaml
├── pyproject.toml
├── uv.lock
├── requirements.txt
├── inference.py
├── server/
│   ├── __init__.py
│   └── app.py
└── supportdesk_env/
    ├── env.py
    ├── tasks.py
    ├── graders.py
    ├── models.py
```

---

## ✅ Validation

* ✔ `openenv validate` passed
* ✔ Local API tests passed
* ✔ Docker build successful
* ✔ Hugging Face deployment live
* ✔ `/reset` endpoint verified

---

## 🏁 Submission

* Hugging Face Space: https://huggingface.co/spaces/Gaurav217/supportdesk-openenv

---

## 👤 Author

**Gaurav Singh**

---

## 📄 License

MIT License
