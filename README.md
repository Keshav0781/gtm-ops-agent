# GTM Ops Agent

Production-grade GTM (Go-To-Market) operations automation using LangGraph, n8n, and MCP integration. A multi-agent system that automates the complete GTM operations loop for a B2B SaaS startup.

---

## What It Does

Automates 5 daily manual operations that waste 3-4 hours every day:

| Agent | What it automates |
|---|---|
| Lead Intelligence | New lead → research → score → draft email → Slack approval |
| Email Triage | Email arrives → classify → draft reply → route to team |
| Meeting Intelligence | Meeting ends → extract action items → summary → Slack + Notion |
| CRM Hygiene | Daily 9am scan → flag stale deals → alert owners via Slack |
| Competitor Intelligence | Weekly Monday scan → detect changes → report to Slack |
| HR Onboarding | Natural language request → plan → manager approval → provision systems |

---

## Live Demo

API is deployed and running on Google Cloud Run (Frankfurt, Germany):

```
https://gtm-ops-agent-324111066236.europe-west3.run.app
```

API Documentation: https://gtm-ops-agent-324111066236.europe-west3.run.app/docs

### Test the live API

```bash
# Health check
curl https://gtm-ops-agent-324111066236.europe-west3.run.app/health

# Test Lead Intelligence
curl -X POST https://gtm-ops-agent-324111066236.europe-west3.run.app/leads/analyze \
  -H "Content-Type: application/json" \
  -d '{"company_name": "BMW Munich", "message": "Interested in analytics platform"}'

# Test Email Triage
curl -X POST https://gtm-ops-agent-324111066236.europe-west3.run.app/emails/triage \
  -H "Content-Type: application/json" \
  -d '{"sender_email": "thomas@bmw.de", "body": "We need analytics support"}'
```

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

---

## Architecture

```
Contact Form / Gmail / Calendar / Slack
            ↓
        n8n Workflows
            ↓
      FastAPI Endpoints
            ↓
    LangGraph Agents (6)
            ↓
  Groq LLM / Ollama (local)
            ↓
    Slack Notifications
```

---

## Quick Start

### Prerequisites
- Python 3.13+
- Docker
- Groq API key (free at console.groq.com)
- LangSmith API key (free at smith.langchain.com)

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

API docs available at: http://localhost:8000/docs

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

## Testing

```bash
# Test Lead Intelligence
curl -X POST http://localhost:8000/leads/analyze \
  -H "Content-Type: application/json" \
  -d '{"company_name": "BMW Munich", "message": "Interested in analytics"}'

# Test Email Triage
curl -X POST http://localhost:8000/emails/triage \
  -H "Content-Type: application/json" \
  -d '{"sender_email": "thomas@bmw.de", "body": "We need analytics support"}'

# Test HR Onboarding
curl -X POST http://localhost:8000/hr/onboard \
  -H "Content-Type: application/json" \
  -d '{"onboarding_request": "Onboard Sarah Chen as Product Designer starting Monday"}'
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
├── n8n/workflows/
├── supabase/
├── tests/
├── Dockerfile
└── docker-compose.yml
```

---

## Key Design Decisions

**Dual LLM routing** — Groq for speed, Ollama for GDPR compliance. Sensitive data (HR, emails) uses local Ollama so data never leaves the machine.

**Human-in-the-loop everywhere** — Zero autonomous outbound. Every email, Slack message, and provisioning action requires human approval.

**Rule-based where possible** — CRM Hygiene uses pure Python logic, no LLM. LLM only used where reasoning is genuinely needed.

**n8n for orchestration** — Agents handle intelligence, n8n handles triggers, scheduling, and routing.

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
| GROQ_API_KEY | Groq API key for LLM |
| LANGCHAIN_API_KEY | LangSmith monitoring |
| SLACK_BOT_TOKEN | Slack bot token for notifications |
| DATABASE_URL | PostgreSQL connection string |
| DEFAULT_LLM_PROVIDER | groq or ollama |

---

## Author

Keshav Jha — AI Engineer
GitHub: https://github.com/Keshav0781
Email: itskeshavjha1996@gmail.com