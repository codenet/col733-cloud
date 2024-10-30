#!/bin/bash

# Directory containing the submissions
SUBMISSION_DIR="/home/baadalvm/lab4_sub"

# Path to your Python file
PYTHON_FILE="evaluate.py"

# Check if the Python file exists
if [[ ! -f "$PYTHON_FILE" ]]; then
    echo "Python file $PYTHON_FILE not found!"
    exit 1
fi

Loop through all .zip files in the directory
for submission in "$SUBMISSION_DIR"/*.zip; do
    # Check if the file exists to avoid errors
    if [[ -f "$submission" ]]; then
        # Call the Python script with the submission file as an argument
        python3.12 "$PYTHON_FILE" "$submission"
    else
        echo "No zip files found in the directory."
    fi
done


