#!/bin/bash

if [ ! -d venv ]; then
    python3 -m venv venv
    venv/bin/pip install --upgrade pip
    venv/bin/pip install -r requirements.txt
fi

venv/bin/python3 main.py