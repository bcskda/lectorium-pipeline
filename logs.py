import logging
import logging.config


def setup_logger(logger):
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    handler.setLevel(logging.INFO)
    
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
