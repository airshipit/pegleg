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

PEGLEG_BUILD_CTX  ?= src/bin/pegleg
IMAGE_NAME        ?= pegleg
IMAGE_PREFIX      ?= airshipit
DOCKER_REGISTRY   ?= quay.io
IMAGE_TAG         ?= latest
HELM              ?= helm
PROXY             ?= http://proxy.foo.com:8000
NO_PROXY          ?= localhost,127.0.0.1,.svc.cluster.local
USE_PROXY         ?= false
PUSH_IMAGE        ?= false
LABEL             ?= commit-id
IMAGE             ?= $(DOCKER_REGISTRY)/$(IMAGE_PREFIX)/$(IMAGE_NAME):$(IMAGE_TAG)
PYTHON_BASE_IMAGE ?= python:3.6
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
	tools/pegleg.sh --help

.PHONY: tests
tests: run_tests

.PHONY: security
security:
	tox -c src/bin/pegleg/tox.ini -e bandit

# Run all unit tests under src/bin/pegleg
.PHONY: run_tests
run_tests:
	tox -c src/bin/pegleg/tox.ini -e py35

# Perform Linting
.PHONY: lint
lint: py_lint

# Perform auto formatting
.PHONY: format
format: py_format

.PHONY: build_pegleg
build_pegleg:
ifeq ($(USE_PROXY), true)
	docker build -t $(IMAGE) --network=host --label $(LABEL) -f images/pegleg/Dockerfile \
		--build-arg FROM=$(PYTHON_BASE_IMAGE) \
		--build-arg http_proxy=$(PROXY) \
		--build-arg https_proxy=$(PROXY) \
		--build-arg HTTP_PROXY=$(PROXY) \
		--build-arg HTTPS_PROXY=$(PROXY) \
		--build-arg no_proxy=$(NO_PROXY) \
		--build-arg NO_PROXY=$(NO_PROXY) \
		--build-arg ctx_base=$(PEGLEG_BUILD_CTX) .
else
	docker build -t $(IMAGE) --network=host --label $(LABEL) -f images/pegleg/Dockerfile \
		--build-arg FROM=$(PYTHON_BASE_IMAGE) \
		--build-arg ctx_base=$(PEGLEG_BUILD_CTX) .
endif
ifeq ($(PUSH_IMAGE), true)
	docker push $(IMAGE)
endif

.PHONY: docs
docs: clean
	tox -edocs

.PHONY: clean
clean:
	rm -rf build

.PHONY: py_lint
py_lint:
	cd src/bin/pegleg;tox -e pep8

.PHONY: py_format
py_format:
	cd src/bin/pegleg;tox -e fmt
