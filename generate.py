import os

import requests
from requests.auth import HTTPBasicAuth
from jinja2 import Template, Environment, FileSystemLoader
from dotenv import dotenv_values

env = Environment(loader=FileSystemLoader('templates'))
index_template = env.get_template('index.jinja')

config = dotenv_values('.env')

def fetch_newsletters():
    r = requests.get(
        f"https://{config['MAILCHIMP_DATA_CENTER']}.api.mailchimp.com/3.0/campaigns?list_id={config['MAILCHIMP_LIST_ID']}&status=sent&sort_field=send_time&sort_dir=DESC",
        headers={'Accept': 'application/json'},
        auth=HTTPBasicAuth(config['MAILCHIMP_USERNAME'], config['MAILCHIMP_API_KEY']),
    )
    return [{
      'send_time': e['send_time'],
      'subject': e['settings']['subject_line'],
      'archive_url_long': e['long_archive_url'],
    } for e in r.json()['campaigns'] if not e['recipients']['segment_text']]

def main():
    print(fetch_newsletters())

    output_from_parsed_template = index_template.render()
    with open("public/index.html", "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", "public/index.html")

if __name__ == '__main__':
    main()
