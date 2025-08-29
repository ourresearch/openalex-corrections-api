from dotenv import load_dotenv
load_dotenv()

import requests
import json
from datetime import datetime, timezone

from app import app, db
from models import Curation


def check_for_live():
    """Check approved curations to see if they've gone live in the OpenAlex API"""
    
    with app.app_context():
        try:
            # Get all approved curations that aren't live yet
            waiting_for_live = Curation.query.filter_by(status="approved", is_live=False).all()
            
            if not waiting_for_live:
                print("No approved curations waiting to go live.")
                return
            
            print(f"Checking {len(waiting_for_live)} approved curations...")
            
            updated_count = 0
            
            # Process each curation
            for curation in waiting_for_live:
                try:
                    # Make API call to check current value
                    api_url = f"https://api.openalex.org/{curation.entity}/{curation.entity_id}?data-version=2"
                    response = requests.get(api_url, timeout=10)
                    response.raise_for_status()
                    api_data = response.json()
                    
                    if curation.entity == "locations":
                        # For locations, check against location object on Work API
                        work_url = api_data["work_id"].replace("://", "://api.") + "?data-version=2"
                        work_response = requests.get(work_url, timeout=10)
                        response.raise_for_status()
                        work_data = work_response.json()
                        location = next((loc for loc in work_data["locations"] if loc["id"] == curation.entity_id), None)

                        api_data = location

                    if not api_data:
                        is_live = False

                    elif curation.create_new:
                        # Check all fields in JSON
                        new_data = json.loads(curation.property_value)
                        is_live = all(api_data.get(key) == value for key, value in new_data.items())
                       
                    else:
                        # Check if the property value matches what was submitted
                        current_value = api_data.get(curation.property)
                        current_value = "true" if current_value == True else current_value
                        current_value = "false" if current_value == False else current_value
                        is_live = str(current_value) == str(curation.property_value)
                    

                    if is_live:
                        # Update to live status
                        curation.is_live = True
                        curation.live_date = datetime.now(timezone.utc)
                        updated_count += 1
                        print(f" Curation {curation.id} for {curation.entity_id} is now live!")
                    else:
                        print(f"- Curation {curation.id} for {curation.entity_id} still waiting (current: {current_value}, expected: {curation.property_value})")
                        
                except requests.RequestException as e:
                    print(f" API error for curation {curation.id}: {e}")
                    continue
                except Exception as e:
                    print(f" Error processing curation {curation.id}: {e}")
                    continue
            
            # Commit all changes at once
            if updated_count > 0:
                db.session.commit()
                print(f"Successfully updated {updated_count} curations to live status.")
            else:
                print("No curations were updated.")
                
        except Exception as e:
            print(f"Database error: {e}")
            db.session.rollback()
        finally:
            db.session.close()


if __name__ == "__main__":
    check_for_live()