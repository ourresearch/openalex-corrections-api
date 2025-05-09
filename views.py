import logging
import os
import json
import gspread
from datetime import datetime
from flask import request, jsonify
from app import app
from flask_cors import CORS
import os
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds_info = json.loads(os.environ["GOOGLE_CREDS_JSON"])
# Fix escaped newlines in private_key for PEM parsing
creds_info['private_key'] = creds_info['private_key'].replace('\\n', '\n')
creds = Credentials.from_service_account_info(creds_info, scopes=SCOPES)
gc = gspread.Client(auth=creds)
gc.session = AuthorizedSession(creds)
sheet = gc.open_by_key(os.environ["GOOGLE_SHEET_UNPAYWALL_ID"])
works_sheet = sheet.worksheet("Works")
journals_sheet = sheet.worksheet("Journals")

logger = logging.getLogger("corrections-api")

# Set up CORS
ENVIRONMENT = os.environ.get("ENVIRONMENT", "development")
if ENVIRONMENT == "production":
    CORS(
        app,
        origins=["https://unpaywall.org"],
        allow_headers=["Content-Type"],
        methods=["GET", "POST", "OPTIONS"]
    )
else:
    CORS(app)

@app.route("/corrections", methods=["POST"])
def corrections():
    data = request.get_json()
    if not data:
        logger.warning("No JSON data provided in request")
        return jsonify({"error": "No data provided"}), 400

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = ["", "", "", timestamp]

    if data["type"] == "doi":
        row.append(data["id"])
        row.append(data["New url"])
        row.append(data["New host_type"])
        row.append(data["Previous url"])
        row.append(data["Previous host_type"])
        row.append(data["email"])
        print("Posting to Works:")
        print(row)
        works_sheet.append_row(row, value_input_option="USER_ENTERED")

    elif data["type"] == "journal":
        row.append(data["id"])
        row.append(data["New is_oa"])
        row.append(data["New oa_date"])
        row.append(data["Previous is_oa"])
        row.append(data["Previous oa_date"])
        row.append(data["email"])
        print("Posting to Journals:")
        print(row)
        journals_sheet.append_row(row, value_input_option="USER_ENTERED")
    
    else:
        logger.warning("Invalid type provided in request")
        return jsonify({"error": "Invalid type provided"}), 400

    return jsonify({"status": "success"}), 201

@app.route("/", methods=["GET"])
def base_endpoint():
    return jsonify({
        "msg": "Don't panic"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5106))
    app.run(host="0.0.0.0", port=port)
