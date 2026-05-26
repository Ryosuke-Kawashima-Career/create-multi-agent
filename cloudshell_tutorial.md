# Multi-Agent AI Hands-on

## Set up the environment

Run the setup script and enter your connpass ID when prompted.

```bash
./scripts/setup.sh
```

The script creates `.env`, stores your participant ID in `scripts/.state`, and installs dependencies with `uv sync --extra dev`.

## Deploy to Agent Runtime

Deploy your agents with your connpass ID prefix.

```bash
./scripts/deploy_all.sh
```

## Clean up

Delete only your own deployed agents.

```bash
./scripts/cleanup.sh
```
