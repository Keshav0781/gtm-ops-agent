# GTM Ops Agent

Production-grade GTM (Go-To-Market) operations automation using LangGraph, n8n, and FastAPI. A multi-agent system that automates the complete GTM operations loop for a B2B SaaS startup — from lead scoring to HR onboarding.

---

## Live Demo

**Dashboard:** https://keshav0781.github.io/gtm-ops-agent/

**Live API:** https://gtm-ops-agent-324111066236.europe-west3.run.app

**API Docs:** https://gtm-ops-agent-324111066236.europe-west3.run.app/docs

---

## What It Does

Automates 6 daily manual operations that waste 3-4 hours every day:

| Agent | What it automates |
|---|---|
| Lead Intelligence | New lead → research → score → draft email → Slack approval |
| Email Triage | Email arrives → classify → draft reply → route to team |
| Meeting Intelligence | Meeting ends → extract action items → summary → Slack |
| CRM Hygiene | Scan deals → flag stale → alert owners via Slack |
| Competitor Intelligence | Scan competitor websites → detect changes → report to Slack |
| HR Onboarding | Natural language request → plan → manager approval in Slack → provision systems |

---

## Tech Stack

| Component | Technology |
|---|---|
| Agent framework | LangGraph |
| Primary LLM | Groq (Llama 3.3 70B) |
| Secondary LLM | Ollama (local, GDPR compliant) |
| Workflow orchestration | n8n |
| API framework | FastAPI |
| Database | PostgreSQL |
| Monitoring | LangSmith |
| Containerisation | Docker |
| Deployment | GCP Cloud Run + Cloud SQL |

---

## Architecture

The system has two distinct flows:

**Flow 1 — All Agents (Lead, Email, Meeting, CRM, Competitor)**

```
User
 │
 │ fills form and clicks Submit
 ▼
Dashboard (GitHub Pages)
 │
 │ HTTP POST
 ▼
FastAPI (GCP Cloud Run)
 │
 │ invokes agent
 ▼
LangGraph Agent
 │
 ├──► Groq LLM (reasoning, scoring, drafting)
 │
 └──► Slack (posts result/notification)
```

**Flow 2 — HR Onboarding (two-step with human approval)**

Step 1 — Plan and request approval:
```
User
 │
 │ types natural language request
 ▼
Dashboard (GitHub Pages)
 │
 │ HTTP POST /hr/onboard
 ▼
FastAPI (GCP Cloud Run)
 │
 │ invokes agent
 ▼
LangGraph Agent (nodes 1-3)
 │
 ├──► Groq LLM (parse request, plan provisioning)
 │
 ├──► PostgreSQL (save full state by request_id)
 │
 └──► Slack #hr-onboarding (posts approval card)
```

Step 2 — Manager approves and systems are provisioned:
```
Manager
 │
 │ types: APPROVE [request_id] in Slack
 ▼
Slack
 │
 │ sends event to webhook
 ▼
n8n
 │ Slack Trigger detects new message
 │ IF node checks: contains APPROVE + not a bot
 │
 │ HTTP POST /hr/provision
 ▼
FastAPI (GCP Cloud Run)
 │
 │ invokes provisioning agent
 ▼
LangGraph Agent (node 4)
 │
 ├──► PostgreSQL (retrieve state by request_id)
 │
 └──► Slack #hr-onboarding (posts confirmation)
```

---

## Try the Live Dashboard

Open https://keshav0781.github.io/gtm-ops-agent/ in your browser. The dashboard connects to the live GCP API automatically.

### Lead Intelligence
Fill in a company name and message. The agent researches the company, scores the lead HIGH/MEDIUM/LOW, and drafts a personalised outreach email.

Example input:
- Company: `Siemens Healthineers`
- Contact: `Klaus Weber`
- Email: `klaus@siemens-healthineers.com`
- Message: `We need a B2B analytics platform for our medical imaging division across 15 countries`
- Source: `Website`

Expected output: HIGH score, Healthcare Technology industry, draft email personalised to their use case.

### Email Triage
Paste any email. The agent classifies it (sales, support, partnership, spam), assigns priority, extracts the core request, routes it to the right person, and drafts a reply.

Example — Partnership email:
- Sender: `anna@techstart.de`
- Subject: `Partnership Opportunity`
- Body: `We are TechStart GmbH, a 50-person AI startup. We'd love to explore a technical partnership integrating our document AI with your analytics platform.`

Expected output: PARTNERSHIP classification, route to CEO, professional draft reply.

Example — Spam email:
- Sender: `noreply@casino-win.ru`
- Subject: `You have won €50,000!!!`
- Body: `Congratulations! Click here to claim your reward.`

Expected output: SPAM classification (red badge), LOW priority, route to ignore, no draft reply.

### Meeting Intelligence
Paste a meeting transcript or notes. The agent extracts action items, identifies decisions made, flags blockers, and generates a summary.

Example input:
- Title: `Q3 Product Roadmap`
- Attendees: `Keshav, Anna, Thomas`
- Transcript: `Keshav said we need to launch the dashboard feature by end of June. Anna will design mockups by next Friday. Thomas handles backend API by June 15th. We decided to drop mobile app from Q3 scope. No blockers identified.`

Expected output: PLANNING type, action items extracted with owners, decisions listed, blockers: NONE.

### CRM Hygiene
Click Run CRM Scan. The agent scans the deal pipeline using rule-based logic (no LLM) and flags:
- Deals with no contact in 30+ days
- Deals stuck in the same stage too long
- Deals missing key information

**Note:** Uses sample deal data for demo (BMW, Siemens, Bosch). In production this connects to HubSpot or Salesforce API. The agent is rule-based — no LLM involved — which makes it fast, deterministic, and auditable.

### Competitor Intelligence
Click Run Competitor Scan. The agent scrapes configured competitor websites and detects changes in pricing, features, and messaging compared to the previous scan.

**Note:** First scan always shows "no changes" because there is no previous content to compare against. In production, the agent runs weekly and builds up a history of changes over time. Each subsequent scan compares against the last stored version and reports what changed.

### HR Onboarding
Type a natural language onboarding request. The agent:
1. Parses employee details (name, role, email, start date, manager)
2. Plans provisioning based on role (Engineer → GitHub, Designer → Figma, etc.)
3. Posts an approval card to Slack #hr-onboarding
4. Waits for manager to type `APPROVE [request_id]` in Slack
5. n8n detects the approval and calls the provisioning endpoint
6. Systems are provisioned, welcome email drafted, confirmation posted to Slack

Example input:
```
Onboard Sarah Chen as Product Designer starting June 2nd,
email: sarah.chen@datasync.de, manager: Thomas Müller
```

Expected output: Figma flagged (manual invite), GitHub not needed, channels #general #design #product, approval card sent to Slack.

---

## Quick Start (Local)

### Prerequisites
- Python 3.13+
- Docker
- Groq API key (free at console.groq.com)
- LangSmith API key (free at smith.langchain.com)
- Slack Bot Token (create app at api.slack.com)

### Setup

**1 — Clone the repository**
```bash
git clone https://github.com/Keshav0781/gtm-ops-agent.git
cd gtm-ops-agent
```

**2 — Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate
```

**3 — Install dependencies**
```bash
pip install -r requirements.txt
```

**4 — Configure environment**
```bash
cp .env.example .env
# Edit .env with your API keys
```

**5 — Start PostgreSQL**
```bash
docker-compose up -d postgres
```

**6 — Apply database schema**
```bash
docker exec -i gtm-ops-postgres psql -U gtmuser -d gtmops < supabase/schema.sql
```

**7 — Start FastAPI**
```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

**8 — Start n8n**
```bash
docker-compose up n8n
```

API docs (only when running locally): http://localhost:8000/docs

---

## API Endpoints

```
GET  /health                  → Health check
POST /leads/analyze           → Lead Intelligence Agent
POST /emails/triage           → Email Triage Agent
POST /meetings/analyze        → Meeting Intelligence Agent
POST /crm/analyze             → CRM Hygiene Agent
POST /competitors/analyze     → Competitor Intelligence Agent
POST /hr/onboard              → HR Onboarding — plan and send approval
POST /hr/provision            → HR Onboarding — execute after approval
```

---

## Project Structure

```
gtm-ops-agent/
├── agents/
│   ├── lead_intelligence/
│   ├── email_triage/
│   ├── meeting_intelligence/
│   ├── crm_hygiene/
│   ├── competitor_intelligence/
│   └── hr_onboarding/
├── api/
│   ├── main.py
│   ├── database.py
│   ├── middleware/
│   └── routers/
├── dashboard/          ← Local development copy
├── docs/               ← GitHub Pages deployment
├── n8n/workflows/
├── supabase/
├── tests/
├── Dockerfile
└── docker-compose.yml
```

---

## Key Design Decisions

**Dual LLM routing** — Groq is used in production for speed. Ollama support is built in for local GDPR-compliant deployments where sensitive data should not leave the machine. Configure via DEFAULT_LLM_PROVIDER in .env.

**Human-in-the-loop everywhere** — Zero autonomous outbound. Every email, Slack message, and provisioning action requires human approval.

**Rule-based where possible** — CRM Hygiene uses pure Python logic, not LLM. Faster, cheaper, deterministic, and auditable.

**State persistence** — HR Onboarding saves full state to PostgreSQL after planning. Provisioning retrieves it by request_id after manager approves — no data passed through Slack messages.

**n8n for orchestration** — Agents handle intelligence, n8n handles triggers, scheduling, approval routing, and human-in-the-loop workflows.

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Environment Variables

See `.env.example` for all required variables.

| Variable | Description |
|---|---|
| GROQ_API_KEY | Groq API key for LLM calls |
| LANGCHAIN_API_KEY | LangSmith monitoring |
| SLACK_BOT_TOKEN | Slack bot token for notifications |
| DATABASE_URL | PostgreSQL connection string |
| DEFAULT_LLM_PROVIDER | groq or ollama |

---

---

## Evaluation

GTM Ops Agent uses a functional evaluation pipeline to validate agent output quality against golden datasets. Each agent is tested by calling the live GCP API and comparing structured outputs against expected values.

Why functional testing and not RAGAS: GTM Ops Agent is an agentic reasoning system, not a RAG pipeline. RAGAS metrics require retrieved context chunks which agentic systems do not expose. Functional testing is the correct evaluation approach for agentic systems.

Run evaluation against the live GCP API:

```bash
source evaluation/venv/bin/activate
python3 evaluation/evaluate_functional.py
```

Latest results:

| Agent | Test Cases | Result |
|---|---|---|
| Lead Intelligence | 5 | 5/5 passed |
| Email Triage | 5 | 5/5 passed |
| Meeting Intelligence | 3 | 3/3 passed |
| CRM Hygiene | 1 | 1/1 passed |
| **Overall** | **14** | **14/14 passed** |

Golden datasets are in `evaluation/datasets/`. Results are saved to `evaluation/report.json` after each run.

**Note:** Evaluation runs in an isolated virtual environment (`evaluation/venv/`) to avoid dependency conflicts with the main project.


## Author

Keshav Jha — AI Engineer, Erlangen Germany
GitHub: https://github.com/Keshav0781
Email: itskeshavjha1996@gmail.com
