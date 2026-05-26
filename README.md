# HireNest Customer Support Escalation Agent

This is the starter repository for the hands-on lab "ADK x A2A x Agent Runtime Customer Support Escalation Agent".

The app models a B2B SaaS support workflow for HireNest ATS, an applicant tracking system for candidate pipelines, public job pages, interview scheduling, scorecards, offers, and recruiting analytics. A Support Coordinator Agent receives a customer support inquiry, runs a generic resolution workflow over specialist agents, and produces a Support Case Resolution Package for support operators.

## Architecture

```text
Support Coordinator Agent
  |- Ticket History Agent        (A2A, port 8101)
  |- Knowledge Base Agent        (A2A, port 8102)
  |- Account Context Agent       (A2A, port 8103)
  |- Incident Status Agent       (A2A, port 8104)
  |- Escalation Policy Agent     (A2A, port 8105)
  `- Diagnostics Agent           (A2A, port 8107)
```

Most specialist agents and deterministic support logic are provided. In the lab,
you implement the ticket-history tool, one specialist agent, structured planning,
human-in-the-loop routing, the coordinator workflow, and Agent Runtime deployment.

## Setup

```bash
make setup
```

The setup script asks for your connpass ID, writes it to `scripts/.state`, creates `.env`, and runs `uv sync --extra dev`.

Optional integrations:

```bash
# Gemini Enterprise Agent Search / Discovery Engine serving config
export HIRENEST_AGENT_SEARCH_SERVING_CONFIG="projects/PROJECT/locations/LOCATION/collections/default_collection/engines/ENGINE/servingConfigs/default_config"

# Discord escalation notifications; without this the tool returns a dry-run payload
export HIRENEST_DISCORD_WEBHOOK_URL="YOUR_DISCORD_WEBHOOK_URL"
```

Important dependency note: ADK 2.1 requires `a2a-sdk>=0.3,<0.4` for the current A2A helper modules. This repo pins `a2a-sdk[http-server]==0.3.26` so the Starlette A2A server can serve agent cards and JSON-RPC routes.

Dependencies are managed with `uv` from `pyproject.toml` and `uv.lock`.

## Run locally

Start the specialists, coordinator, and ADK Web together:

```bash
make run
```

Or run each service group in separate terminals. First start the local A2A
specialist services:

```bash
make run-specialists
```

In another terminal, start the coordinator A2A service:

```bash
make run-coordinator
```

The agent cards are available at:

```text
http://localhost:8101/.well-known/agent-card.json
http://localhost:8102/.well-known/agent-card.json
http://localhost:8103/.well-known/agent-card.json
http://localhost:8104/.well-known/agent-card.json
http://localhost:8105/.well-known/agent-card.json
http://localhost:8107/.well-known/agent-card.json
http://localhost:8100/.well-known/agent-card.json
```

Start ADK Web only:

```bash
make web
```

ADK Web listens on `http://localhost:8000`.

## Test and lint

```bash
make lint
make test
```

Refresh the lockfile after dependency changes:

```bash
make lock
```

## Deploy to Agent Platform Agent Runtime

Use the Google Cloud project provided by the workshop organizers. The deployment
script uses your connpass ID from `scripts/.state` and deploys resources with
display names such as `[alice_123] Support Coordinator Agent`.

Set `TRACE_TO_CLOUD=true` or `HIRENEST_TRACE_TO_CLOUD=true` before deployment to enable Cloud Trace.

Deploy every agent:

```bash
make deploy-all
```

The deployment script loads defaults from `.env`, exports dependencies from the
uv lockfile, deploys specialists in parallel, writes authenticated specialist
A2A card URLs into the coordinator deployment environment, then deploys the
coordinator:

```bash
uv export --format requirements.txt --no-dev --no-hashes --no-emit-project \
  --output-file .agent-runtime-temp/requirements.txt
```

Agents are deployed from source files with the Agent Runtime API. This source-file deployment path does not require a Cloud Storage staging bucket.

For each deployed agent, `scripts/deploy_all.sh` creates a clean temporary source directory outside the repository with a root `agent.py` that re-exports that agent's `root_agent`. Specialist temporary entrypoints wrap the ADK agent in an A2A Runtime `A2aAgent`; the coordinator temporary entrypoint wraps the ADK workflow in an Agent Runtime `AdkApp`.

After the specialist Agent Runtime resources are created, the script writes their authenticated A2A card URLs into the coordinator deployment environment variables.

Agent2Agent on Agent Runtime is currently a preview workflow. Keep local A2A URLs for workshop development and use runtime endpoints for the deployment exercise.

To clean up only your deployed Reasoning Engine resources, use:

```bash
./scripts/cleanup.sh --dry-run
./scripts/cleanup.sh
```

## Repository layout

```text
agents/                  ADK coordinator and specialist agent entrypoints
data/                    Fictional HireNest ATS tickets, accounts, incidents, KB, product, and policy fixtures
scripts/                 Agent Runtime deployment and cleanup helpers
src/hirenest_support/    Deterministic search, policy, diagnostics, communication, and redaction logic
tests/                   Unit and agent-import tests
```
