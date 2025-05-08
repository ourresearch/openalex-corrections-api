import logging
import os
import sys
import warnings

from flask import Flask, request, jsonify
from flask_compress import Compress

# Logging setup (following team pattern)
logging.basicConfig(
    stream=sys.stdout,
    level=logging.DEBUG,
    format='%(thread)d: %(message)s'
)
logger = logging.getLogger("corrections-api")

# Suppress noisy libraries if needed
libraries_to_mum = []
for library in libraries_to_mum:
    library_logger = logging.getLogger(library)
    library_logger.setLevel(logging.WARNING)
    library_logger.propagate = True
    warnings.filterwarnings("ignore", category=UserWarning, module=library)

# Flask app setup
app = Flask(__name__)
Compress(app)

# Example: load config from environment variables
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON", "")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
