# Hyojin Distribution AI Agent Team Build Plan

**Version:** v3.0 | **Date:** February 2026  
**Infrastructure:** Oracle Cloud A1.Flex (Always Free) | **Agent Platform:** OpenClaw | **LLM:** Google Gemini API  
**Monthly Budget Limit:** $450 (Strict maximum) | **Daily Budget Limit:** $15 (Strict maximum)

---

## 1. Project Overview

We are building a multi-AI agent team to automate and intelligently manage all operations for Hyojin Distribution. A "Chief Secretary" agent will communicate 1:1 with the CEO via Telegram and oversee the entire agent team, while individual team agents will handle practical tasks. All agents will be implemented on the OpenClaw platform and dynamically call the Google Gemini API when needed.

> **Phase 1 Goal:** Completing the creation of agents and deployment of the basic architecture. Establishing specific routines and delegating precise tasks will be done in later stages.

| Item | Details |
|------|---------|
| Purpose | AI automation of operations & decision support for the CEO. |
| Scope | 5 Teams (Management, Marketing, Design, Finance, CS) + 1 Chief Secretary |
| Interface | Telegram (CEO ↔ Chief Secretary 1:1 Chat) |
| Monthly Budget Limit | **$450 (Strict maximum, never exceed)** |
| Daily Budget Limit | **$15 (Strict maximum, never exceed)** |
| Dev Tools | Claude Code (Automated Coding) & Google Antigravity (Automated Coding) |

---

## 2. System Architecture

### 2.1 Overall Structure

CEO (Telegram) ↔ Chief Secretary Agent (OpenClaw / Oracle Cloud A1) ↔ 5 Team Agents ↔ Google Gemini API (gemini-3-flash, gemini-3.1-pro) ↔ PostgreSQL on A1 (Data Storage)

### 2.2 Request Processing Flow (Example)

1. CEO → "Analyze this month's ROAS"
2. → Chief Secretary (Uses Gemini to grasp intent + Routes to corresponding team)
3. → Marketer Agent (Uses Gemini to collect and analyze ad data)
4. → Queries ad data from PostgreSQL
5. → Chief Secretary (Uses Gemini to compile report)
6. → Telegram response to CEO

### 2.3 Infrastructure Components

| Element | Analogy | Actual Role |
|---------|---------|-------------|
| OpenClaw | Body | Agent execution engine — creation, routing, message processing |
| Google Gemini API | Brain | Actual thinking, judgment, analysis (gemini-3-flash, gemini-3.1-pro dynamic allocation) |
| PostgreSQL (A1 Internally) | Memory | Persistent storage for chat history, analysis results, files, agent memories |
| Oracle Cloud A1 | Infrastructure | 24/7 Server hosting — running OpenClaw + DB via Docker |

---

## 3. Oracle Cloud A1.Flex — Always Free Infrastructure

> **Absolute Principle:** We must NEVER exceed Oracle Cloud's Always Free tier limits. We will not use paid resources under any circumstances, operating strictly at the maximum free limit.

### 3.1 Always Free A1.Flex Limits

| Resource | Free Limit (Max) | Notes |
|----------|----------------|-------|
| OCPU (ARM) | **Max 4 OCPU** | Flexibly allocated |
| Memory | **Max 24 GB RAM** | Flexibly allocated |
| Boot Volume + Block Storage| **Max 200 GB** | Minimum 50GB required for boot volume |
| Object Storage | Max 20 GB | For backups |
| Outbound Data Transfer | 10 TB / Month | Plenty of allowance |
| Public IPv4 Address | Max 6 | We will use 1 |

### 3.2 Rules to Prevent Going Over Free Tier

| Rule | Details |
|------|---------|
| Instance Count Limits | Create ONLY 1 A1.Flex instance. |
| Block Volume | NEVER exceed 200GB. |
| Network | Use ONLY 1 free Load Balancer. |
| Object Storage | Must stay under 20GB. Archive if exceeded. |
| Budget Alerts | Use OCI Budget feature to set a $0 threshold alert — notify immediately if any charge occurs. |
| Shape Changes | NEVER change from A1.Flex to a paid shape. |

### 3.3 Preventing Free Instance Reclamation

> ⚠️ Oracle can reclaim idle instances if CPU/Network/RAM usage remains below 20% for 7 days.

**Countermeasures:**
- Basic activity is naturally maintained by OpenClaw + PostgreSQL running 24/7.
- Safety net: Run a Cron Job health check every 5 minutes to generate baseline activity.
- Set up OCI monitoring alerts — notify via Telegram immediately upon reclamation warning.

### 3.4 Internal A1 Service Configuration

All services operate via Docker Compose on a single A1.Flex instance. 

| Service | Role |
|---------|------|
| OpenClaw | Agent Engine + Telegram Bot |
| PostgreSQL | Data, analytics, expenses, memory storage |
| Nginx (Reverse Proxy) | HTTPS Termination, Webhook receptor, security gateway |
| Monitoring/Healthcheck | Self-health check + budget check |

---

## 4. OpenClaw Platform Details

> OpenClaw is currently the most popular open-source AI agent platform. It integrates natively with 50+ messengers and can run locally or on a server.

### 4.1 Core Features
- Any Chat App support
- Persistent Memory
- Browser Control
- Full System Access (Sandboxed)
- Skills & Plugins

### 4.2 Cost Breakdown

| Item | Cost |
|------|------|
| OpenClaw Software | **$0 (Free Open Source)** |
| LLM API Cost | Separate (Billed via Google Gemini API) |
| Hosting | Oracle Cloud A1.Flex (Always Free — $0) |

### 4.3 OpenClaw Security and Known Vulnerabilities

| Vulnerability | Severity | Details |
|---------------|----------|---------|
| CVE-2026-25253 (RCE)| Critical (8.8)| Unauthenticated attackers can take over gateway. Patched in v2026.1.29 |
| Prompt Injection | High | Instructions hidden in malicious content can hijack agent operations |
| Unauthenticated Dev Instances | High | Do not expose gateway to public internet |

> ⚠️ OpenClaw MUST be updated to the latest version (v2026.1.29+) and all security measures in Section 12 must be applied.

---

## 5. AI Agent Team Structure

> **Current Phase Policy:** Create agents and configure basic prompts only. Complex routines will be added in later phases.

### Chief Secretary (General Manager)
- 1:1 Telegram communication with CEO.
- Has authority to command team leaders on behalf of the CEO.
- Consolidates reports from each team and presents them to the CEO.
- Uses `gemini-3-flash` for daily communication, `gemini-3.1-pro` for delegating tasks and important decisions.

### Team Agents (Phase 1: Creation Only)
- Management Team: **Planning PM**
- Marketing Team: **Marketer**
- Design Team: **Designer**
- Finance Team: **Finance Manager**
- CS Team: **CS Manager**

---

## 6. LLM Dynamic Allocation Strategy

### 6.1 Model Routing Rules

| Agent | Practical Tasks | Reporting to Chief Sec. | Final Decisions |
|-------|-----------------|-------------------------|-----------------|
| Chief Sec | gemini-3-flash | — | gemini-3.1-pro |
| Planning PM | gemini-3-flash ~ pro | gemini-3.1-pro | — |
| Marketer | gemini-3-flash ~ pro | gemini-3.1-pro | — |
| Designer | gemini-3-flash ~ pro | gemini-3.1-pro | — |
| Finance | gemini-3-flash ~ pro | gemini-3.1-pro | — |
| CS | gemini-3-flash ~ pro | gemini-3.1-pro | — |

> Sub-agents use `gemini-3-flash` by default but dynamically upgrade to `gemini-3.1-pro` for complex analysis. This is strictly subject to the BudgetGuard daily limits.

### 6.2 Model Versioning & Extensibility

1. **Guaranteed Stability**: To prevent sudden parsing errors or prompt mismatches caused by provider background updates, **always use pinned model versions** (e.g., `gemini-3.1-pro-001`, `gemini-3.0-flash-001`). NEVER use `latest` tags in production.
2. **Future Extensibility**: To ensure the LLM can be easily swapped out if a better frontier model is released in the future, **never hardcode model providers or specific model specs into the core business logic.**
   - Manage all LLM-related variables (Provider, Model Name, endpoints) strictly through environment variables (`.env`).
   - Use modular configurations or universal adapters (like OpenClaw's native provider mapping) so that switching LLMs is purely a configuration update without requiring code rewrites.

---

## 7. Strict Budget Control Strategy (Absolutely No Exceptions)

> **Core Principle:** Never exceed $450/month and $15/day. Implement triple safety layers.

### 7.1 Budget Structure
- Monthly Max Limit: **$450**
- Daily Max Limit: **$15** (Blocks entire agent network if exceeded)
- Infrastructure Target Cost: **$0**

### 7.2 Triple Safety Layers

**Layer 1 — Google Gemini API Console Hard Limit**
- Set Monthly Spend Limit to **$450** directly in the Google Gemini Console.

**Layer 2 — Server-Level Daily Budget Blocker (BudgetGuard)**
- Implement middleware in the OpenClaw server.
- Before every API call, query today/month usage from the `api_usage_log` PostgreSQL table.
- If $15 daily or $450 monthly limit is reached, BLOCK API calls completely and alert CEO.
- After every API call, precisely record model name, input/output tokens, and cost.

**Layer 3 — Real-Time Telegram Alerts**
- 🟡 70% ($10.50): "Daily cost at 70%. $4.50 remaining."
- 🟠 90% ($13.50): "Daily cost at 90%. Switching to gemini-3-flash only mode."
- 🔴 100% ($15.00): "Daily API limit reached. Agents suspended until midnight."

---

## 8. Technology Stack

- **Agent Platform:** OpenClaw (Free Open Source)
- **LLM:** Google Gemini API (Pinned versions: `gemini-3.0-flash-001` / `gemini-3.1-pro-001`)
- **Server:** Oracle Cloud A1.Flex (Always Free)
- **Database:** PostgreSQL (Docker)
- **Reverse Proxy:** Nginx (Docker)
- **Messenger:** Telegram Bot API
- **Coding Tool:** Claude Code & Antigravity

---

## 9. 24-Hour Operation Guarantee

**Preventing Idle Reclamation:**
- OpenClaw + PostgreSQL run natively 24/7.
- Cron Job checks health every 5 minutes and logs service status.
- Monitor OCI resource usage to maintain >20% metrics.

---

## 10. Implementation Steps

> **Phase 1 Deployment Target:** Oracle Cloud A1 Setup + 6 Agents Created + Telegram Integrated + Budget Blocker active + Strict Security Guidelines applied.

1. **Oracle Cloud A1 Setup:** Instance creation (4OCPU/24GB) + Security Group rules + SSH keys.
2. **Docker Setup:** Install Docker & Compose. Configure Nginx, PostgreSQL, OpenClaw.
3. **SSL/Domain:** HTTPS Let's Encrypt config with domain (or OCI public IP).
4. **Telegram Bot:** Bot creation, Webhook routing.
5. **Chief Secretary Agent:** Create in OpenClaw, prompt, routing logic.
6. **5 Team Agents:** Creation and base prompt configs.
7. **PostgreSQL Link:** Attach storage logic for chats, memory, and cost logs.
8. **BudgetGuard Middleware:** Implement daily/monthly block logic and notifications.
9. **Security Hardening:** Docker sandboxing, network isolation, skill auditing.
10. **Final Audit & Deployment:** Confirm OCI budget alerts ($0 target).

---

## 12. Security Strategies (Required)

### 12.1 Oracle Cloud Infra Security
- **VCN Security List:** Inbound SSH (22) for admin IPs only. HTTPS (443) for Telegram webhook IPs only. Block all others.
- **Gateway Port (18789):** NEVER expose to the public internet. Access behind Nginx only.
- Set OCI budget alert for $0 threshold.

### 12.2 OpenClaw Patching & Config
- Use **v2026.1.29+** (Addresses RCE CVE-2026-25253).
- Do not use `latest` Docker image tag; use fixed digest.
- `auth: none` must be disabled. Generate strict Gateway Token.
- Telegram `chat_id` whitelist applied (Drop everything except CEO's ID).

### 12.3 Docker / Network Context
- Run containers as non-root (UID 1000).
- Strip all Linux kernel caps (`cap_drop: ALL`).
- Limit OpenClaw container to 1 CPU core and 512MB RAM if feasible.
- Nginx Firewall: Block all outbound traffic unless directed at Gemini API endpoints.

### 12.4 Sensitive Keys
- Provide via environment variables only (`GEMINI_API_KEY`, Telegram Bot Token).
- NEVER hardcode keys in `.py` or config files. Provide robust `.env` parsing, and ensure `.gitignore` lists `.env`.

---

## 16. Developer Guidelines for Claude Code (AI Developer)

**As the AI Assistant assigned to build this system, you must strictly follow these instructions:**

1. **Phased Implementation:** Do not attempt to code the whole repository in a single shot. Split work into logical phases, create a plan, and ask for confirmation before switching contexts.
   - **Phase 1:** Project initialization, `.env.example`, `docker-compose.yml`, structure planning.
   - **Phase 2:** Nginx reverse proxy routing and PostgreSQL schema structures (especially the token usage log).
   - **Phase 3:** OpenClaw base setup + Gateway Token security + Telegram Bot webhook integration.
   - **Phase 4:** **BudgetGuard Middleware (CRITICAL).** Implement the cost-counting and blocking logic BEFORE you execute LLM API calls.
   - **Phase 5:** Chief Secretary Agent specific prompting and routing logic.
2. **Absolute Strict Budget Limit:** The business will die if API costs spike. Implement `BudgetGuard` safely. Query the database before sending any generation request to Gemini. Block operations without exception if the $15 daily limit is breached.
3. **Security-First Coding:** Follow every point in Section 12. No hardcoding secrets, strict input validation, non-root execution.
4. **Interactive Confirmation:** Whenever you write a crucial piece of infrastructure (like the DB schemas or docker configurations), notify the user, show them the code, and ask if they are ready to run it before proceeding independently. Do not rush.
5. **Extensible LLM Integration:** Design the system anticipating future LLM swaps. Do not hardcode "Gemini" specific parsing deep into the central logic; rely on modular provider interfaces and keep all model strings in the `.env` file.
