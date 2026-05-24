# Makefile Variables.
include config.mk

# Docker's BuildKit feature.
export DOCKER_BUILDKIT=1

.PHONY: build push docker help

build: ## Build rln-telegram-bot docker image.
	docker build -f ./Dockerfile -t $(IMAGE_RLN_TELEGRAM_BOT_BACKUP) . && \
	docker build -f ./Dockerfile -t $(IMAGE_RLN_TELEGRAM_BOT_LATEST) .

push: ## Push rln-telegram-bot docker image.
	docker push $(IMAGE_RLN_TELEGRAM_BOT_BACKUP) && \
	docker push $(IMAGE_RLN_TELEGRAM_BOT_LATEST)

docker: ## Build and push rln-telegram-bot docker images.
	make build push

help: ## Show this help.
	@grep -hE '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
