import subprocess
import sys
import logging
import time

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    logger.info("Starting Main Bot (main.py)...")
    main_bot = subprocess.Popen([sys.executable, "main.py"])

    logger.info("Starting Cashier Bot (cashier.py)...")
    cashier_bot = subprocess.Popen([sys.executable, "cashier.py"])

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
            # Check if either process crashed
            if main_bot.poll() is not None:
                logger.error("Main Bot crashed! Shutting down...")
                cashier_bot.terminate()
                sys.exit(1)
                
            if cashier_bot.poll() is not None:
                logger.error("Cashier Bot crashed! Shutting down...")
                main_bot.terminate()
                sys.exit(1)
                
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Stopping both bots...")
        main_bot.terminate()
        cashier_bot.terminate()
        
        main_bot.wait()
        cashier_bot.wait()
        logger.info("Both bots stopped successfully.")

if __name__ == "__main__":
    main()
