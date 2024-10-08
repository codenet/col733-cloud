# SHELL := /bin/bash

# Set the starting port
START_PORT ?= 9900

mypy:
	MYPYPATH=.  mypy --exclude=build/ .

test_storage:
	python -m unittest tests/test_storage.py

test_client:
	python -m unittest tests/test_client.py
