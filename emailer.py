
import os
import jinja2
import requests

from app import logger

mailgun_api_key = os.getenv('MAILGUN_API_KEY')


def send_moderation_email(curation):

  return

  api_data = requests.get(f"https://api.openalex.org/{curation.entity}/{curation.entity_id}?data-version=2").json()

  entity_singular = curation.entity.rstrip('s')
  
  data = {
    "entity": entity_singular,
    "display_name": api_data.get("display_name", ""),
    "url": f"https://api.openalex.org/{curation.entity}/{curation.entity_id}?data-version=2",
    "property": curation.property,
    "property_value": curation.property_value
  }

  if curation.approved:
    send_email(curation.email, "Your curation request has been approved.", "curation_approved", data)
  else:
    send_email(curation.email, "Your curation request has been denied.", "curation_denied", data)


def send_email(to_address, subject, template_name, template_data, test=False):
    template_loader = jinja2.FileSystemLoader(searchpath='templates')
    template_env = jinja2.Environment(loader=template_loader)
    html_template = template_env.get_template(template_name + '.html')

    html = html_template.render(template_data)

    mailgun_url = f"https://api.mailgun.net/v3/ourresearch.org/messages"

    mailgun_auth = ("api", mailgun_api_key)

    mailgun_data = {
        "from": "OurResearch Team <team@ourresearch.org>",
        "to": [to_address],
        "subject": subject,
        "html": html
    }

    logger.info(f'sending email "{subject}" to {to_address}')

    if not test:
        requests.post(mailgun_url, auth=mailgun_auth, data=mailgun_data)
    else:
        print(mailgun_data)
