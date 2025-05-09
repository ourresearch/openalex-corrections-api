import logging
from flask import request, jsonify
from app import app
import os

logger = logging.getLogger("corrections-api")

@app.route("/", methods=["GET"])
def base_endpoint():
    return jsonify({
        "msg": "Don't panic"
    })

@app.route("/corrections", methods=["POST"])
def corrections():
    data = request.get_json()
    if not data:
        logger.warning("No JSON data provided in request")
        return jsonify({"error": "No data provided"}), 400

    # TODO: Add your processing logic here
    logger.info(f"Received correction: {data}")

    # TODO: Send data to Google Sheets (placeholder)
    # Example: send_to_google_sheets(data)
    logger.info("Would send to Google Sheets here.")

    return jsonify({"status": "success"}), 201

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5106))
    app.run(host="0.0.0.0", port=port)
