# Variables.
ENVIRONMENT             ?=
IMAGE_TAG               ?= latest
REGISTRY_HOST           ?= ghcr.io/utexo-protocol
CURRENT_DATE_TIME       := $(shell date +'%Y-%m-%d')
LATEST_COMMIT           := $$(git rev-parse --short HEAD)

# Image names.
RLN_TELEGRAM_BOT_IMAGE := rln-telegram-bot

# Variables for build — RLN Telegram Bot.
IMAGE_RLN_TELEGRAM_BOT_BACKUP = $(REGISTRY_HOST)/$(RLN_TELEGRAM_BOT_IMAGE)$(ENVIRONMENT):$(CURRENT_DATE_TIME)-$(LATEST_COMMIT)
IMAGE_RLN_TELEGRAM_BOT_LATEST = $(REGISTRY_HOST)/$(RLN_TELEGRAM_BOT_IMAGE)$(ENVIRONMENT):$(IMAGE_TAG)
