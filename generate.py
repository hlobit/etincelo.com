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

# FROM: https://github.com/luyves/kmeans-dominant-colours
import numpy as np
import pandas as pd

from PIL import Image

from sklearn.cluster import KMeans

def resize(imgfile, basewidth=200):
    img = Image.open(imgfile, 'r')
    wpercent = (basewidth / float(img.size[0]))
    hsize = int((float(img.size[1]) * float(wpercent)))
    img = img.resize((basewidth, hsize), Image.ANTIALIAS)
    return np.array(img)

def hexify(palette):
    return['#%s' % ''.join(('%02x' % round(p) for p in colour)) for colour in palette]

def KMeansModel(imgfile, n_clusters=3):
    # Loading and resizing the selected image. It is necessary to reshape the numpy array to train our model.
    img = resize(imgfile, 200)
    img_arr = img.reshape((img.shape[0] * img.shape[1], img.shape[2]))
    cluster = KMeans(n_clusters=n_clusters, init='random', n_init=10, max_iter=300, random_state=0)
    cluster.fit_predict(img_arr)
    return cluster, img

def palette(imgfile, n_clusters=3):
    cluster, img = KMeansModel(imgfile, n_clusters=n_clusters)
    colours = np.int_(cluster.cluster_centers_.round())
    return hexify(colours)
#

songs = pathlib.Path('songs')
templates = pathlib.Path('templates')
env = Environment(loader=FileSystemLoader('templates'))

config = dotenv_values('.env')

def fetch_newsletters(*, list_id, count=10, since_send_time=None, match=None):
    params = {
            'list_id': list_id,
            'status': 'sent,schedule',
            'sort_field': 'send_time',
            'sort_dir': 'DESC',
    }
    if count:
        params['count'] = count*2
    if since_send_time:
        params['since_send_time'] = since_send_time
    r = requests.get(
        f"https://{config['MAILCHIMP_DATA_CENTER']}.api.mailchimp.com/3.0/campaigns",
        headers={'Accept': 'application/json'},
        auth=HTTPBasicAuth(config['MAILCHIMP_USERNAME'], config['MAILCHIMP_API_KEY']),
        params=params,
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
            and not e['settings']['subject_line'].startswith('Rappel :')
            and (not match or match(e))][:count]

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
    other_contents = [
        'message-20240407',
        'insta-20240408',
        'newsletter-20240430',
        'annulation-commande',
        'confirmation-commande',
    ]

    for item in other_contents:
        output_from_parsed_template = env.get_template(f'{item}.jinja').render()
        with open(f'public/{item}.html', 'w') as f:
            f.write(output_from_parsed_template)
        print('Generated : ', f'public/{item}.html')

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
        output_from_parsed_template = env.get_template('chant.jinja').render(selected='chants', title=title, content=content)
        with open(f'public/{path.stem}.html', "w") as f:
            f.write(output_from_parsed_template)
        print("Generated : ", f'public/{path.stem}.html')

    output_from_parsed_template = env.get_template('chants.jinja').render(selected='chants', titles=titles)
    with open(f'public/chants.html', "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", f'public/chants.html')

    output_from_parsed_template = env.get_template('qui-sommes-nous.jinja').render(selected='qui-sommes-nous')
    with open("public/qui-sommes-nous.html", "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", "public/qui-sommes-nous.html")

    items = [
        {
            'button_id': 'HZVP6ZRBXVDYC',
            'palette': palette('public/images/nazareenne.artwork.jpg'),
            'template': 'articles/nazareenne.jinja',
            'price': 18,
            'available': False,
        },
        {
            'button_id': 'LKM9L3J27J3QC',
            'palette': palette('public/images/leepn.artwork.png'),
            'template': 'articles/leepn.jinja',
            'price': 8,
            'available': True,
        },
        {
            'button_id': 'Z54DR2AW8SV6N',
            'palette': palette('public/images/uatj.artwork.png'),
            'template': 'articles/uatj.jinja',
            'price': 15,
            'available': True,
        },
        {
            'button_id': 'JVTAM7ZCNJLVJ',
            'palette': [c[:7] for c in palette('public/images/leepn-uatj.pack.png')],
            'template': 'articles/leepn-uatj.jinja',
            'price': 20,
            'available': True,
        },
        {
            'button_id': 'RGWLWRP8CWLAG',
            'palette': palette('public/images/tapm.artwork.png'),
            'template': 'articles/tapm.jinja',
            'price': 4,
            'available': False,
        }
    ]
    articles = []
    for item in items:
        contents = env.get_template(item['template']).render(item=item)
        articles.append({**item, 'contents': contents})
    output_from_parsed_template = env.get_template('boutique.jinja').render(selected='boutique', articles=articles)
    with open("public/boutique.html", "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", "public/boutique.html")

    templatepaths = templates.glob('parcours-nazareenne/*.jinja')
    nazareenne_posts = []
    for item in sorted(templatepaths, reverse=True):
        path = str(item).removeprefix('templates/')
        contents = env.get_template(path).render()
        date = item.stem
        m = re.search('<h3>(.*)</h3>', contents)
        title = m.group(1)
        nazareenne_posts.append({
            'id': date,
            'send_time': datetime.strptime(date, '%Y%m%d').strftime('%d/%m/%Y'),
            'subject': title,
            'contents': contents,
        })
    output_from_parsed_template = env.get_template('parcours-nazareenne.jinja').render(selected='parcours-nazareenne', posts=nazareenne_posts)
    with open("public/parcours-nazareenne.html", "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", "public/parcours-nazareenne.html")

    newsletters = fetch_newsletters(list_id=config['MAILCHIMP_LIST_ID'], count=10, since_send_time='2023-10-04T00:00:00+00:00',
                                    match=lambda e: not e['settings']['subject_line'].startswith('Parcours de mai Nazaréenne'))

    output_from_parsed_template = env.get_template('index.jinja').render(selected='index', newsletters=newsletters)
    with open("public/index.html", "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", "public/index.html")

    etince10_posts = fetch_newsletters(list_id=config['MAILCHIMP_CALENDAR_LIST_ID'], count=25,
                                       match=lambda e: e['settings']['title'].startswith('Jour '))
    campaigns = {n['campaign_id']: n['id'] for n in etince10_posts}
    contents = {campaigns[campaign_id]: content for campaign_id, content in fetch_contents(*campaigns.keys())}

    for newsletter_id in contents:
        s = re.search('🎧 Chant&nbsp;: ([^<]*)', contents[newsletter_id])
        replacement = s.group(0).replace(s.group(1), f'<a href="/{paths[s.group(1)]}">{s.group(1)}</a>')
        contents[newsletter_id] = contents[newsletter_id].replace(s.group(0), replacement)

    output_from_parsed_template = env.get_template('calendrier.jinja').render(selected='calendrier', posts=etince10_posts, contents=contents)
    with open("public/calendrier.html", "w") as f:
        f.write(output_from_parsed_template)
    print("Generated : ", "public/calendrier.html")


if __name__ == '__main__':
    main()
