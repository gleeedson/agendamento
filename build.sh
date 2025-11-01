#!/usr/bin/env bash
# exit on error
set -o errexit

pip install poetry
poetry config virtualenvs.create false
poetry install --only main

# Criar tabelas e admin
poetry run python create_admin.py