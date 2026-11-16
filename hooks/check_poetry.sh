#!/bin/bash
cd "$(dirname "$(dirname "$0")")/${1:-api}"
poetry check
