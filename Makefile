# Copyright 2017 AT&T Intellectual Property.  All other rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

include vcs-requirements.env

PEGLEG_BUILD_CTX  ?= pegleg
IMAGE_NAME        ?= pegleg
IMAGE_PREFIX      ?= airshipit
DOCKER_REGISTRY   ?= quay.io
IMAGE_TAG         ?= latest
HELM              ?= helm
PROXY             ?= http://proxy.foo.com:8000
NO_PROXY          ?= localhost,127.0.0.1,.svc.cluster.local
USE_PROXY         ?= false
PUSH_IMAGE        ?= false
# use this variable for image labels added in internal build process
LABEL             ?= org.airshipit.build=community
COMMIT            ?= $(shell git rev-parse HEAD)
DISTRO             ?= ubuntu_noble
DISTRO_ALIAS	   ?= ubuntu_noble
IMAGE             ?= $(DOCKER_REGISTRY)/$(IMAGE_PREFIX)/$(IMAGE_NAME):$(IMAGE_TAG)-${DISTRO}
IMAGE_ALIAS              := ${DOCKER_REGISTRY}/${IMAGE_PREFIX}/${IMAGE_NAME}:${IMAGE_TAG}-${DISTRO_ALIAS}
PYTHON_BASE_IMAGE ?= python:3.8
BASE_IMAGE        ?=

export

# Build all docker images for this project
.PHONY: images
images: build_pegleg

# Run an image locally and exercise simple tests
.PHONY: run_images
run_images: run_pegleg

# Run the Pegleg container and exercise simple tests
.PHONY: run_pegleg
run_pegleg: build_pegleg
	IMAGE=quay.io/airshipit/pegleg:latest-${DISTRO} tools/pegleg.sh --help

.PHONY: tests
tests: run_tests

.PHONY: security
security:
	tox -e bandit

# Run all unit tests under pegleg
.PHONY: run_tests
run_tests:
	tox -e py36

# Perform Linting
.PHONY: lint
lint: py_lint

# Perform auto formatting
.PHONY: format
format:
	tox -e fmt

_BASE_IMAGE_ARG := $(if $(BASE_IMAGE),--build-arg FROM="${BASE_IMAGE}" ,)

.PHONY: build_pegleg
build_pegleg:
ifeq ($(USE_PROXY), true)
	docker build -t $(IMAGE) --network=host --label $(LABEL) \
		--label "org.opencontainers.image.revision=$(COMMIT)" \
		--label "org.opencontainers.image.created=$(shell date --rfc-3339=seconds --utc)" \
		--label "org.opencontainers.image.title=$(IMAGE_NAME)" \
		-f images/pegleg/Dockerfile.${DISTRO} \
		$(_BASE_IMAGE_ARG) \
		--build-arg http_proxy=$(PROXY) \
		--build-arg https_proxy=$(PROXY) \
		--build-arg HTTP_PROXY=$(PROXY) \
		--build-arg HTTPS_PROXY=$(PROXY) \
		--build-arg no_proxy=$(NO_PROXY) \
		--build-arg NO_PROXY=$(NO_PROXY) \
		--build-arg ctx_base=$(PEGLEG_BUILD_CTX) . \
		--build-arg DECKHAND_VERSION=${DECKHAND_VERSION} \
		--build-arg PROMENADE_VERSION=${PROMENADE_VERSION} \
		--build-arg SHIPYARD_VERSION=${SHIPYARD_VERSION}
else
	docker build -t $(IMAGE) --network=host --label $(LABEL) \
		--label "org.opencontainers.image.revision=$(COMMIT)" \
		--label "org.opencontainers.image.created=$(shell date --rfc-3339=seconds --utc)" \
		--label "org.opencontainers.image.title=$(IMAGE_NAME)" \
		-f images/pegleg/Dockerfile.${DISTRO} \
		$(_BASE_IMAGE_ARG) \
		--build-arg ctx_base=$(PEGLEG_BUILD_CTX) . \
		--build-arg DECKHAND_VERSION=${DECKHAND_VERSION} \
		--build-arg PROMENADE_VERSION=${PROMENADE_VERSION} \
		--build-arg SHIPYARD_VERSION=${SHIPYARD_VERSION}
endif
ifneq ($(DISTRO), $(DISTRO_ALIAS))
	docker tag $(IMAGE) $(IMAGE_ALIAS)
ifeq ($(DOCKER_REGISTRY), localhost:5000)
	docker push $(IMAGE_ALIAS)
endif
endif
ifeq ($(DOCKER_REGISTRY), localhost:5000)
	docker push $(IMAGE)
endif
ifeq ($(PUSH_IMAGE), true)
	docker push $(IMAGE)
endif

.PHONY: docs
docs: clean
	tox -e docs

.PHONY: clean
clean:
	rm -rf build
	rm -rf doc/build

.PHONY: py_lint
py_lint:
	tox -e pep8