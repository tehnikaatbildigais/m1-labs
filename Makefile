# Ezermalas iesniegumu sistēma · komandas. Saraksts: make help
SHELL := /bin/bash
TEMPLATE_REPO ?= https://github.com/mleitass/m1-labs.git
# Marķieris (token) tikai OMD imitācijai. Īstus marķierus šeit neraksta.
OMD_API_TOKEN ?= macibu-tokens-tikai-imitacijai
export OMD_API_TOKEN

.PHONY: help run mock test fmt check rung skill vendor-pr

help: ## Parāda komandas
	@awk -F ':.*## ' '/^[a-zA-Z_%-]+:.*## / {printf "  make %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

run: ## Palaiž lietotni (ports 8000: /ui un /docs)
	python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

mock: ## Palaiž OMD reģistra imitāciju (ports 8001)
	python -m uvicorn mock_omd.main:app --host 0.0.0.0 --port 8001

test: ## Palaiž testus
	python -m pytest -q

fmt: ## Formatē kodu un izlabo stila piezīmes
	ruff format .
	ruff check --fix .

check: ## Skeneri: ruff, bandit, pip-audit (lēmumu pieņemat jūs)
	-ruff check .
	-bandit -q -r app mock_omd
	-pip-audit -r requirements.txt

rung: ## Uzvedņu kāpņu pakāpiens: make rung N=1, 2 vai 3
	@case "$(N)" in 1|2|3) ;; *) echo "Norādiet pakāpienu: make rung N=1, N=2 vai N=3"; exit 1;; esac
	git fetch -q origin main
	git checkout -B cr1-r$(N) origin/main
	@if [ "$(N)" != "1" ]; then \
		git fetch -q $(TEMPLATE_REPO) kits && \
		git show FETCH_HEAD:T3/CR-1.md > tracker/CR-1.md && \
		git add tracker/CR-1.md && \
		git commit -q -m "CR-1: pieteikums READY (atkārtots eksports)"; \
	fi
	@if [ "$(N)" = "3" ]; then \
		git show FETCH_HEAD:T4/CLAUDE-rules.md >> CLAUDE.md && \
		git add CLAUDE.md && \
		git commit -q -m "CR-1: darba noteikumi CLAUDE.md"; \
	fi
	@echo ""
	@echo "Zars cr1-r$(N) gatavs. Sāciet JAUNU Claude Code sarunu."

skill: ## Pievieno prasmi ezermala-ui (mapē .claude/skills/)
	git fetch -q $(TEMPLATE_REPO) kits
	mkdir -p .claude/skills/ezermala-ui
	git show FETCH_HEAD:skills/ezermala-ui/SKILL.md > .claude/skills/ezermala-ui/SKILL.md
	@echo "Prasme ezermala-ui pievienota. Sāciet JAUNU Claude Code sarunu."

vendor-pr: ## Piegādātāja izmaiņa CR-3 zarā vendor/cr-3
	git fetch -q $(TEMPLATE_REPO) vendor/cr-3
	git checkout -B vendor/cr-3 FETCH_HEAD
	@echo "Zars vendor/cr-3 gatavs. Palaidiet lietotni: make run"

reset-to-%: ## Aizstāj main ar kontrolpunktu, piemēram: make reset-to-after-cr1
	@echo "Zars main tiks aizstāts ar kontrolpunktu checkpoint/$*. Nesaglabātās izmaiņas pazudīs."
	@read -r -p "Turpināt? (j/n) " answer; [ "$$answer" = "j" ]
	git fetch -q $(TEMPLATE_REPO) checkpoint/$*
	git checkout -f -B main FETCH_HEAD
	git push --force origin main
