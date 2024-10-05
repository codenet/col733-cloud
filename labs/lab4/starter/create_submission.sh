#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: $0 entry_num"
  exit 1
fi

entry_num=$1
zip -r "${entry_num}.zip" bayou/app.py bayou/storage.py bayou/server.py

