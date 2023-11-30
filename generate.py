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

def fetch_newsletters(*, list_id, count=10):
    r = requests.get(
        f"https://{config['MAILCHIMP_DATA_CENTER']}.api.mailchimp.com/3.0/campaigns?list_id={list_id}&status=sent&sort_field=send_time&sort_dir=DESC&count={count*2}",
        headers={'Accept': 'application/json'},
        auth=HTTPBasicAuth(config['MAILCHIMP_USERNAME'], config['MAILCHIMP_API_KEY']),
    )
    # NOTE: if there is segment_text, the campaign target was not all subscribers, omit them
    return [{
      'send_time': datetime.fromisoformat(e['send_time']).strftime('%d/%m/%Y'),
      'subject': e['settings']['subject_line'],
      'archive_url_long': e['long_archive_url'],
    } for e in r.json()['campaigns']
            if not e['recipients']['segment_text']
            and not e['settings']['subject_line'].startswith('Rappel :')][:count]

def main():
    newsletters = fetch_newsletters(list_id=config['MAILCHIMP_LIST_ID'], count=4)

    output_from_parsed_template = index_template.render(newsletters=newsletters)
    with open("public/index.html", "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", "public/index.html")

    newsletters = fetch_newsletters(list_id=config['MAILCHIMP_CALENDAR_LIST_ID'], count=25)

    output_from_parsed_template = calendrier_template.render(newsletters=newsletters)
    with open("public/calendrier.html", "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", "public/calendrier.html")

if __name__ == '__main__':
    main()
