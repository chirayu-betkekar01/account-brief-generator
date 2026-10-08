# Developer entry points. Needs: GNU make, Terraform >= 1.9, Python 3, and AWS credentials
# via AWS_PROFILE (see .env.example). Recipes avoid shell features (pipes, &&) so they work
# in both cmd.exe and bash; `terraform -chdir` replaces `cd`.
#
# Guard-rails baked into the targets:
#   * The main stack is applied from a SAVED plan: `make plan` writes infra/main/tfplan, you
#     read it, and `make apply` executes exactly that file and nothing else.
#   * destroy is interactive: Terraform prints what it will remove and waits for you to type
#     "yes". There is deliberately no -auto-approve anywhere.
#   * The budget lives in its own stack and is applied first; the main stack refuses to plan
#     without it. `make destroy` keeps the budget; `make destroy-all` removes it too.

.DEFAULT_GOAL := help
BOOT := terraform -chdir=infra/bootstrap
MAIN := terraform -chdir=infra/main
PY ?= python

.PHONY: help bootstrap-init bootstrap-plan bootstrap-apply bootstrap-destroy \
        init plan apply ingest destroy destroy-all smoke brief ui test price-check fmt lint

help:
	@echo 'Targets:'
	@echo '  bootstrap-init      terraform init for the budget stack'
	@echo '  bootstrap-plan      show what the budget stack would create (free, read-only)'
	@echo '  bootstrap-apply     create the budget alarm (shows the plan, asks for yes)'
	@echo '  bootstrap-destroy   remove the budget alarm'
	@echo '  init                terraform init for the main stack'
	@echo '  plan                write and show the main-stack plan to infra/main/tfplan (read-only)'
	@echo '  apply               apply exactly the saved plan from make plan'
	@echo '  ingest              load the knowledge documents into the search index (after apply)'
	@echo '  destroy             remove the whole main stack, keep the budget (asks for yes)'
	@echo '  destroy-all         destroy, then remove the budget as well'
	@echo '  smoke               invoke the deployed Lambdas and check their answers'
	@echo '  brief               ask the agent for a brief: make brief COMPANY="Northwind Logistics"'
	@echo '  ui                  open the web page for the agent (needs the stack deployed)'
	@echo '  test                run the unit tests (activate the .venv first, or pass PY=path)'
	@echo '  price-check         verify unit prices against the AWS Price List API'
	@echo '  fmt                 terraform fmt'
	@echo '  lint                run the pre-commit checks on all files'
	@echo 'REMINDER: run make destroy when you pause, and check the AWS bill the next day.'

bootstrap-init:
	$(BOOT) init

bootstrap-plan: bootstrap-init
	$(BOOT) plan

bootstrap-apply: bootstrap-init
	$(BOOT) apply

bootstrap-destroy:
	$(BOOT) destroy

init:
	$(MAIN) init

plan: init
	$(MAIN) plan -out=tfplan

apply:
	$(MAIN) apply tfplan

destroy:
	$(MAIN) destroy

destroy-all: destroy bootstrap-destroy

ingest:
	$(PY) scripts/kb_ingest.py

smoke:
	$(PY) scripts/smoke_test.py

brief:
	$(PY) client/brief.py "$(COMPANY)" $(ARGS)

ui:
	$(PY) -m streamlit run client/app.py

test:
	$(PY) -m pytest

price-check:
	$(PY) scripts/price_check.py

fmt:
	terraform fmt -recursive infra

lint:
	pre-commit run --all-files
