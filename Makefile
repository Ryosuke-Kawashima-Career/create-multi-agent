UV ?= uv
UV_RUN := $(UV) run

.PHONY: setup lock lint run run-specialists run-coordinator run-ag-ui deploy-all web clean

setup:
	$(UV) sync --extra dev

lock:
	$(UV) lock

lint:
	$(UV_RUN) --extra dev ruff check .

run:
	@trap 'trap - INT TERM; pids=$$(jobs -p); [ -n "$$pids" ] && kill $$pids 2>/dev/null; wait 2>/dev/null; exit 0' INT TERM; \
	$(MAKE) --no-print-directory web & web_pid=$$!; \
	$(MAKE) --no-print-directory run-specialists & \
	$(MAKE) --no-print-directory run-coordinator & \
	echo "Specialists, coordinator, and ADK Web are starting."; \
	wait $$web_pid

run-specialists:
	@trap 'trap - INT TERM; pids=$$(jobs -p); [ -n "$$pids" ] && kill $$pids 2>/dev/null; wait 2>/dev/null; exit 0' INT TERM; \
	PYTHONPATH=. $(UV_RUN) uvicorn agents.comfort.agent:app --host 0.0.0.0 --port 8101 & \
	PYTHONPATH=. $(UV_RUN) uvicorn agents.risk.agent:app --host 0.0.0.0 --port 8102 & \
	PYTHONPATH=. $(UV_RUN) uvicorn agents.experience.agent:app --host 0.0.0.0 --port 8103 & \
	echo "Specialist A2A agents are running on ports 8101-8103."; \
	wait

run-coordinator:
	PYTHONPATH=. $(UV_RUN) uvicorn agents.coordinator.agent:app --host 0.0.0.0 --port 8100

run-ag-ui:
	PYTHONPATH=. $(UV_RUN) uvicorn agents.coordinator.ag_ui_app:app --host 0.0.0.0 --port 8200

deploy-all:
	./scripts/deploy_all.sh

web:
	PYTHONPATH=. $(UV_RUN) adk web agents --port 8080

clean:
	rm -rf .venv .ruff_cache .agent-runtime-temp .agent-engine-temp build dist *.egg-info
