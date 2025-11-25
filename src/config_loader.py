import yaml
import os
import shutil
from .logger import setup_logger

logger = setup_logger("config_loader")

def load_config(config_path="config.yaml", default_path="config.default.yaml"):
    """
    Loads configuration from config.yaml.
    If config.yaml does not exist, copies from config.default.yaml.
    """
    if not os.path.exists(config_path):
        if os.path.exists(default_path):
            logger.warning(f"{config_path} not found. Creating from {default_path}...")
            shutil.copy(default_path, config_path)
        else:
            logger.error(f"Neither {config_path} nor {default_path} found.")
            raise FileNotFoundError("Configuration file not found.")
            
    with open(config_path, 'r', encoding='utf-8') as f:
        try:
            config = yaml.safe_load(f)
            logger.info("Configuration loaded successfully.")
            return config
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML: {e}")
            raise
