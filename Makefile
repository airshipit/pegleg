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

PEGLEG_BUILD_CTX           ?= src/bin/pegleg
IMAGE_NAME                 ?= pegleg
IMAGE_PREFIX               ?= attcomdev
DOCKER_REGISTRY            ?= quay.io
IMAGE_TAG                  ?= latest
HELM                       ?= helm
PROXY                      ?= http://proxy_url
USE_PROXY                  ?= false
PUSH_IMAGE                 ?= false
LABEL                      ?= commit-id
IMAGE                      ?= $(DOCKER_REGISTRY)/$(IMAGE_PREFIX)/$(IMAGE_NAME):$(IMAGE_TAG)
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
	docker build -t $(IMAGE) --network=host --label $(LABEL) -f images/pegleg/Dockerfile --build-arg ctx_base=$(PEGLEG_BUILD_CTX) --build-arg http_proxy=$(PROXY) --build-arg https_proxy=$(PROXY) .
else
	docker build -t $(IMAGE) --network=host --label $(LABEL) -f images/pegleg/Dockerfile --build-arg ctx_base=$(PEGLEG_BUILD_CTX) .
endif
ifeq ($(PUSH_IMAGE), true)
	docker push $(IMAGE)
endif

.PHONY: clean
clean:
	rm -rf build

.PHONY: py_lint
py_lint:
	cd src/bin/pegleg;tox -e lint

.PHONY: py_format
py_format:
	cd src/bin/pegleg;tox -e fmt
