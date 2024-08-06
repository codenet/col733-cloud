import json
import os


def read_config(file_path):
    """Read and return the content of a JSON configuration file."""
    with open(file_path, "r") as file:
        config = json.load(file)
    return config


# Path to your configuration JSON file
CONFIG_FILE_PATH = os.getenv("WC_CONFIG", "config.json")

# Load the configuration
config = read_config(CONFIG_FILE_PATH)
