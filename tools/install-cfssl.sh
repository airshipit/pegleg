#!/usr/bin/env bash

set -ex

if [ $# -eq 1 ]; then
  CFSSLURL=$1
else
  CFSSLURL=${CFSSLURL:="http://pkg.cfssl.org/R1.2/cfssl_linux-amd64"}
fi

if [ -z $(which cfssl) ]; then
  if [ $(whoami) == "root" ]; then
    curl -Lo /usr/local/bin/cfssl ${CFSSLURL}
    chmod 555 /usr/local/bin/cfssl
  else
    if [ ! -d ~/.local/bin ]; then
      mkdir -p ~/.local/bin
    fi
    curl -Lo ~/.local/bin/cfssl ${CFSSLURL}
    chmod 555 ~/.local/bin/cfssl
  fi
fi
