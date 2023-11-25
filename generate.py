import os

from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth
from jinja2 import Template, Environment, FileSystemLoader
from dotenv import dotenv_values

env = Environment(loader=FileSystemLoader('templates'))
index_template = env.get_template('index.jinja')
calendrier_template = env.get_template('calendrier.jinja')

config = dotenv_values('.env')

def fetch_newsletters():
    r = requests.get(
        f"https://{config['MAILCHIMP_DATA_CENTER']}.api.mailchimp.com/3.0/campaigns?list_id={config['MAILCHIMP_LIST_ID']}&status=sent&sort_field=send_time&sort_dir=DESC",
        headers={'Accept': 'application/json'},
        auth=HTTPBasicAuth(config['MAILCHIMP_USERNAME'], config['MAILCHIMP_API_KEY']),
    )
    return [{
      'send_time': datetime.fromisoformat(e['send_time']).strftime('%d/%m/%Y'),
      'subject': e['settings']['subject_line'],
      'archive_url_long': e['long_archive_url'],
    } for e in r.json()['campaigns'] if not e['recipients']['segment_text']]

def main():
    newsletters = fetch_newsletters()

    output_from_parsed_template = index_template.render(newsletters=newsletters[:4])
    with open("public/index.html", "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", "public/index.html")

    output_from_parsed_template = calendrier_template.render()
    with open("public/calendrier.html", "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", "public/calendrier.html")

if __name__ == '__main__':
    main()
