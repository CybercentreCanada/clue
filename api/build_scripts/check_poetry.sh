#!/bin/bash
cd $(dirname $(dirname $0))
poetry check
