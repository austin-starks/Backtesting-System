import sys
import logging
import traceback


def log_error(msg):
    """
    Logs errors to the console and the logs. 
    
    This function prints the error msg and saves the message to the log. It then closes
    the system. The log in the terminal will have the stacktrace for the error.
    """
    for line in traceback.format_stack():
        print(line.strip())
    print("ERROR:", msg)
    logging.error(msg)
    sys.exit(0)

def log_info(*msg):
    """
    Logs info to the console and to the logs

    This function prints the message and saves the message to the log
    """
    if len(msg) == 1:
        msg = msg[0]
    print("INFO: ", msg)
    logging.info(msg)