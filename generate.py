import os

from datetime import datetime

import bs4
import requests
from requests.auth import HTTPBasicAuth
from jinja2 import Template, Environment, FileSystemLoader
from dotenv import dotenv_values

songs = pathlib.Path('songs')
env = Environment(loader=FileSystemLoader('templates'))

config = dotenv_values('.env')

def fetch_newsletters(*, list_id, count=10):
    r = requests.get(
        f"https://{config['MAILCHIMP_DATA_CENTER']}.api.mailchimp.com/3.0/campaigns?list_id={list_id}&status=sent,schedule&sort_field=send_time&sort_dir=DESC&count={count*2}",
        headers={'Accept': 'application/json'},
        auth=HTTPBasicAuth(config['MAILCHIMP_USERNAME'], config['MAILCHIMP_API_KEY']),
    )
    # NOTE: if there is segment_text, the campaign target was not all subscribers, omit them
    return [{
      'id': e['long_archive_url'].split('/')[-1],
      'campaign_id': e['id'],
      'send_time': datetime.fromisoformat(e['send_time']).strftime('%d/%m/%Y'),
      'subject': e['settings']['subject_line'],
      'archive_url_long': e['long_archive_url'],
    } for e in r.json()['campaigns']
            if not e['recipients']['segment_text']
            and not e['settings']['subject_line'].startswith('Rappel :')][:count]

def fetch_content(*, campaign_id):
    r = requests.get(
        f"https://{config['MAILCHIMP_DATA_CENTER']}.api.mailchimp.com/3.0/campaigns/{campaign_id}/content",
        headers={'Accept': 'application/json'},
        auth=HTTPBasicAuth(config['MAILCHIMP_USERNAME'], config['MAILCHIMP_API_KEY']),
    )
    soup = bs4.BeautifulSoup(r.json()['html'], "html.parser")
    for block in soup.select('[data-block-id]'):
        block_id = block.attrs['data-block-id']
        if block_id not in ('1', '2', '7', '8', '16', '21', '28', '32', '36', '37', '41', '44', '46',):
            continue
        block.extract()
    return str(soup.body) \
        .replace('background-color: #ffffff;', '') \
        .replace('background-color:#ffffff;', '') \
        .replace('background-color: rgb(250, 250, 250);', '') \
        .replace('background-color:white;', '') \
        .replace('background-color:white', '') \
        .replace('max-width:660px', '') \
        .replace('padding-right:24px;padding-left:24px', '')

def main():
    newsletters = fetch_newsletters(list_id=config['MAILCHIMP_LIST_ID'], count=4)

    output_from_parsed_template = index_template.render(newsletters=newsletters)
    with open("public/index.html", "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", "public/index.html")

    newsletters = fetch_newsletters(list_id=config['MAILCHIMP_CALENDAR_LIST_ID'], count=25)
    contents = [{ 'id': n['id'], 'html': fetch_content(campaign_id=n['campaign_id'])} for n in newsletters]

    output_from_parsed_template = env.get_template('calendrier.jinja').render(newsletters=newsletters, contents=contents)
    with open("public/calendrier.html", "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", "public/calendrier.html")

if __name__ == '__main__':
    main()
