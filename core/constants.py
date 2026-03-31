import os
from dotenv import load_dotenv

# Load .env located in the same directory as this file
HERE = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(HERE, ".env"))

WATER_FEE = int(os.getenv("WATER_FEE", "50000"))
PRICE_PER_KWH = int(os.getenv("PRICE_PER_KWH", "3000"))
