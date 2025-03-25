import logging

def setup_ashari_logger():
    logger = logging.getLogger('ashari')
    
    # Only add handler if there isn't one already
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger

# Create a single instance to be imported elsewhere
ashari_logger = setup_ashari_logger()