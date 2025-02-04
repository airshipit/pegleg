#!/bin/bash
git config --global --add safe.directory "*"
exec "$@"