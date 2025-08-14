import logging
import os
import sys
import warnings

from flask import Flask, request, jsonify
from flask_compress import Compress
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.pool import NullPool


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
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL').replace('postgres://', 'postgresql://')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config['SQLALCHEMY_ECHO'] = (os.getenv('SQLALCHEMY_ECHO', False) == 'True')

class NullPoolSQLAlchemy(SQLAlchemy):
    def apply_driver_hacks(self, flask_app, info, options):
        options['poolclass'] = NullPool
        return super(NullPoolSQLAlchemy, self).apply_driver_hacks(flask_app, info, options)

db = NullPoolSQLAlchemy(app, session_options={"autoflush": False})
Compress(app)
