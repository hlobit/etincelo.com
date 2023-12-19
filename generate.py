import os
import pathlib
import re
import concurrent.futures

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
        if block_id not in ('-13', '1', '2', '7', '8', '16', '21', '28', '32', '36', '37', '41', '44', '46', '55'):
            continue
        block.extract()
    for block in soup.select('colgroup'):
        block.extract()
    # TWEAKS
    return str(soup.body) \
        .replace('background-color: #ffffff;', '') \
        .replace('background-color:#ffffff;', '') \
        .replace('background-color: rgb(250, 250, 250);', '') \
        .replace('background-color:white;', '') \
        .replace('background-color:white', '') \
        .replace('background-color:#f4ddba;padding-top:12px;padding-bottom:12px;', '') \
        .replace('max-width:660px', '') \
        .replace('padding-right:24px;padding-left:24px', '') \
        .replace('padding-top:20px;padding-bottom:20px;', '') \
        .replace('border-top:20px solid transparent', '') \
        .replace('border-style:solid;border-color:rgba(36, 28, 21, 0.3);border-width:1px', '') \
        .replace(' ;', '&nbsp;;') \
        .replace(' :', '&nbsp;:') \
        .replace(' ?', '&nbsp;?') \
        .replace(' !', '&nbsp;!') \
        .replace('’', "'") \
        .replace('src="https://mcusercontent.com', 'loading="lazy" src="https://mcusercontent.com') \
        .replace('src="https://storage.googleapis.com', 'loading="lazy" src="https://storage.googleapis.com') \
        .replace('Avec chant', 'Avec le chant')

def fetch_contents(*campaign_ids):
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_campaign_id = {executor.submit(fetch_content, campaign_id=campaign_id): campaign_id for campaign_id in campaign_ids}
        for future in concurrent.futures.as_completed(future_to_campaign_id):
            campaign_id = future_to_campaign_id[future]
            try:
                yield campaign_id, future.result()
            except Exception as exc:
                yield campaign_id, exc

def main():
    newsletters = fetch_newsletters(list_id=config['MAILCHIMP_LIST_ID'], count=4)

    output_from_parsed_template = env.get_template('index.jinja').render(newsletters=newsletters)
    with open("public/index.html", "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", "public/index.html")

    audio_button = env.get_template('audio-button.jinja').render()
    songpaths = songs.glob('*.html')
    titles = {}
    paths = {}
    for path in sorted(songpaths):
        content = path.read_text()
        m = re.search('<h2 id="title">(.*)</h2>', content)
        title = m.group(1)
        titles[path.stem] = title
        paths[title] = path.stem
        content = content.replace('%AUDIO_BUTTON%', audio_button)
        output_from_parsed_template = env.get_template('chant.jinja').render(title=title, content=content)
        with open(f'public/{path.stem}.html', "w") as f:
            f.write(output_from_parsed_template)
        print("Generated : ", f'public/{path.stem}.html')

    output_from_parsed_template = env.get_template('chants.jinja').render(titles=titles)
    with open(f'public/chants.html', "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", f'public/chants.html')

    newsletters = fetch_newsletters(list_id=config['MAILCHIMP_CALENDAR_LIST_ID'], count=25)
    campaigns = {n['campaign_id']: n['id'] for n in newsletters}
    contents = {campaigns[campaign_id]: content for campaign_id, content in fetch_contents(*campaigns.keys())}

    for newsletter_id in contents:
        s = re.search('🎧 Chant&nbsp;: ([^<]*)', contents[newsletter_id])
        replacement = s.group(0).replace(s.group(1), f'<a href="/{paths[s.group(1)]}">{s.group(1)}</a>')
        contents[newsletter_id] = contents[newsletter_id].replace(s.group(0), replacement)

    output_from_parsed_template = env.get_template('calendrier.jinja').render(newsletters=newsletters, contents=contents)
    with open("public/calendrier.html", "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", "public/calendrier.html")


if __name__ == '__main__':
    main()
