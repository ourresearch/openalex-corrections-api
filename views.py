import logging
import os
import json
import requests
import gspread
from datetime import datetime, timezone
from flask import request, jsonify
from app import app, db
from flask_cors import CORS
import os
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession

from models import Curation
from emailer import send_moderation_email


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
        origins=["https://unpaywall.org", "https://openalex.org"],
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
        row.append(data.get("id", ""))
        row.append(data.get("New url", ""))
        row.append(data.get("New host_type", ""))
        row.append(data.get("Previous url", ""))
        row.append(data.get("Previous host_type", ""))
        row.append(data.get("email", ""))
        print("Posting to Works:")
        print(row)
        works_sheet.append_row(row, value_input_option="USER_ENTERED")

    elif data["type"] == "journal":
        row.append(data.get("id", ""))
        row.append(data.get("New is_oa", ""))
        row.append(data.get("New oa_date", ""))
        row.append(data.get("Previous is_oa", ""))
        row.append(data.get("Previous oa_date", ""))
        row.append(data.get("email", ""))

        if data.get("Approved", False):
            row[0] = "yes"

        print("Posting to Journals:")
        print(row)
        journals_sheet.append_row(row, value_input_option="USER_ENTERED")
    
    else:
        logger.warning("Invalid type provided in request")
        return jsonify({"error": "Invalid type provided"}), 400

    return jsonify({"status": "success"}), 201


@app.route("/v2/corrections", methods=["POST"])
def v2_corrections_post():
    data = request.get_json()
    if not data:
        logger.warning("No JSON data provided in request")
        return jsonify({"error": "No data provided"}), 400

    # Validate required fields (must be present and have values)
    required_fields = ["entity", "entity_id", "submitter_email"]
    missing_fields = []
    
    for field in required_fields:
        if not data.get(field):
            missing_fields.append(field)
    
    # Check required fields that can be null
    nullable_required_fields = ["property_value", "property"]
    for field in nullable_required_fields:
        if not field in data:
            missing_fields.append(field)
    
    if missing_fields:
        logger.warning(f"Missing required fields: {missing_fields}")
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    property_value = data.get("property_value", None)
    property_value = property_value if property_value == "" else property_value
    curation = Curation(
        status=data.get("status", "approved"),
        entity=data.get("entity"),
        entity_id=data.get("entity_id"),
        property=data.get("property"),
        property_value=property_value,
        create_new=data.get("create_new", False),
        submitter_email=data.get("submitter_email"),
        submitted_date=datetime.now(timezone.utc),
    )
    if data.get("status") == "approved":
        curation.moderator_email = data.get("moderator_email", "")
        curation.moderated_date = datetime.now(timezone.utc)
    db.session.add(curation)
    db.session.commit()

    return jsonify({"status": "success"}), 201


@app.route("/v2/corrections", methods=["GET"])
def v2_corrections_get():
    from sqlalchemy import desc, asc
    
    # Pagination - support both offset and page parameters
    per_page = min(request.args.get('per_page', 20, type=int), 100)
    offset_param = request.args.get('offset', type=int)
    page = request.args.get('page', 1, type=int)
    
    # Build query with filters
    query = Curation.query
    
    # Apply filters dynamically
    filter_fields = ['status','entity', 'entity_id', 'property', 'submitter_email', 'moderator_email', 'is_live']
    for field in filter_fields:
        if value := request.args.get(field):
            if field == 'is_live':
                is_live_value = value.lower() in ('true', '1', 'yes')
                query = query.filter(Curation.is_live == is_live_value)
            else:
                query = query.filter(getattr(Curation, field) == value)
    
    # Sorting
    sort_by = request.args.get('sort_by', 'submitted_date')
    sort_order = request.args.get('sort_order', 'desc')
    if hasattr(Curation, sort_by):
        sort_func = desc if sort_order.lower() == 'desc' else asc
        query = query.order_by(sort_func(getattr(Curation, sort_by)))
    
    if offset_param is not None:
        # Use offset/limit directly
        total = query.count()
        results = query.offset(offset_param).limit(per_page).all()
        
        return jsonify({
            'results': add_previous_values([c.to_dict() for c in results]),
            'pagination': {
                'offset': offset_param,
                'per_page': per_page,
                'total': total,
                'has_more': (offset_param + per_page) < total
            }
        })
    else:
        # Use page-based pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'results': add_previous_values([c.to_dict() for c in paginated.items]),
            'pagination': {
                'page': page, 'per_page': per_page, 'total': paginated.total,
                'pages': paginated.pages, 'has_next': paginated.has_next, 'has_prev': paginated.has_prev
            }
        })


def add_previous_values(curations):
    location_ids = [c["entity_id"] for c in curations if c["entity"] == "locations" and not c["is_live"]]
    source_ids = [c["entity_id"] for c in curations if c["entity"] == "sources" and not c["is_live"]]

    locations_data = {}
    sources_data = {}
    
    if len(location_ids) > 0:
        locations_data = get_openalex_data("locations", location_ids)
    
    if len(source_ids) > 0:
        sources_data = get_openalex_data("sources", source_ids)

    api_data = {**locations_data, **sources_data}
    
    for curation in curations:
        if curation["entity_id"] in api_data:
            entity_data = api_data[curation["entity_id"]]
            curation["apiData"] = entity_data
            if curation["property"] is not None:
                curation["previous_value"] = entity_data.get(curation["property"], None)

    return curations        


def get_openalex_data(entity, ids):
    filterId = "id:" if entity == "locations" else "ids.openalex:"
    try: 
        url = f"https://api.openalex.org/{entity}?filter={filterId}" + "|".join(ids) + "&data-version=2"
        print("URL:", url, flush=True)
        response = requests.get(url)
        data = response.json()
        return {response["id"].replace("https://openalex.org/", ""): response for response in data["results"]}
    except Exception as e:
        logger.error(f"Error getting OpenAlex data: {e}")
        return {} 

@app.route("/v2/corrections/<id>", methods=["POST"])
def v2_corrections_update(id):
    data = request.get_json()
    if not data:
        logger.warning("No JSON data provided in request")
        return jsonify({"error": "No data provided"}), 400

    curation = Curation.query.get(id)
    if not curation:
        logger.warning(f"Curation with id {id} not found")
        return jsonify({"error": "Curation not found"}), 404

    if "status" in data:
        new_status = data.get("status", None)
        if new_status not in ["needs-moderation", "approved", "denied"]:
            return jsonify({"error": "Invalid status"}), 400

        old_status = curation.status
        curation.status = new_status
        curation.moderator_email = data.get("moderator_email", "")
        curation.moderated_date = datetime.now(timezone.utc)
        db.session.commit()

        if old_status == "needs-moderation" and new_status in ["approved", "denied"]:
            send_moderation_email(curation)

    return jsonify({"status": "success"}), 200



@app.route("/v2/pending", methods=["GET"])
def v2_pending():
    from sqlalchemy import or_
    
    pending_curations = Curation.query.filter(
        or_(
            Curation.status == "needs-moderation",
            Curation.status == "approved"
        ),
        Curation.is_live == False
    ).all()
    
    entity_ids = list(set([f"{curation.entity_id}|{curation.property}" for curation in pending_curations]))
    
    return jsonify(entity_ids)



@app.route("/pending", methods=["GET"])
def pending():
    return jsonify({
        "journals": get_pending_ids(journals_sheet),
        "works": get_pending_ids(works_sheet)
    })


def get_pending_ids(sheet):
    """
    Get values from the fifth column of journal sheet rows where:
    - Second column does not equal "yes"
    - First column does not equal "no"
    
    Returns:
        list: Values from the fifth column of matching rows
    """
    try:
        # Get all values from the sheet
        all_values = sheet.get_all_values()
        
        # Skip header row if it exists (assuming first row is headers)
        data_rows = all_values[1:] if all_values else []
        
        filtered_values = []
        
        for row in data_rows:
            # Ensure row has at least 5 columns
            if len(row) >= 5:
                # Get values from first, second, and fifth columns (0-indexed)
                first_col = row[0].strip().lower() if row[0] else ""
                second_col = row[1].strip().lower() if row[1] else ""
                fifth_col = row[4] if row[4] else ""
                
                # Check conditions: second column != "yes" AND first column != "no"
                if second_col != "yes" and first_col != "no":
                    filtered_values.append(fifth_col)
        
        return filtered_values
        
    except Exception as e:
        logger.error(f"Error filtering journal sheet: {str(e)}")
        return []


@app.route("/", methods=["GET"])
def base_endpoint():
    return jsonify({
        "msg": "Don't panic"
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5106))
    app.run(host="0.0.0.0", port=port)
