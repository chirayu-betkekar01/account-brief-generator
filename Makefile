# Developer entry points. Needs: GNU make, Terraform >= 1.9, Python 3, and AWS credentials
# via AWS_PROFILE (see .env.example). Recipes avoid shell features (pipes, &&) so they work
# in both cmd.exe and bash; `terraform -chdir` replaces `cd`.
#
# Guard-rails baked into the targets:
#   * apply/destroy are interactive: Terraform prints the plan and waits for you to type
#     "yes". There is deliberately no -auto-approve anywhere.
#   * The budget lives in its own stack and is applied first.

.DEFAULT_GOAL := help
BOOT := terraform -chdir=infra/bootstrap

.PHONY: help bootstrap-init bootstrap-plan bootstrap-apply bootstrap-destroy price-check fmt lint

help:
	@echo Targets:
	@echo   bootstrap-init      terraform init for the budget stack
	@echo   bootstrap-plan      show what the budget stack would create (free, read-only)
	@echo   bootstrap-apply     create the budget alarm (shows the plan, asks for yes)
	@echo   bootstrap-destroy   remove the budget alarm
	@echo   price-check         verify unit prices against the AWS Price List API
	@echo   fmt                 terraform fmt
	@echo   lint                run the pre-commit checks on all files
	@echo More targets (plan, apply, destroy, test, eval) arrive with the later phases.
	@echo REMINDER: run make destroy when you pause, and check the AWS bill the next day.

bootstrap-init:
	$(BOOT) init

bootstrap-plan: bootstrap-init
	$(BOOT) plan

bootstrap-apply: bootstrap-init
	$(BOOT) apply

bootstrap-destroy:
	$(BOOT) destroy

price-check:
	python scripts/price_check.py

fmt:
	terraform fmt -recursive infra

lint:
	pre-commit run --all-files
