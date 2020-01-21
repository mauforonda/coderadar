#!/usr/bin/env python3

import requests
import json
from datetime import datetime, timedelta, timezone
from feedgen.feed import FeedGenerator

def load_config(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
        return config['github'], config['search'], config['rss']

def save(data, rss):
    data_sorted = sorted(data, key=lambda k: k['updated'])
    fg = FeedGenerator()
    fg.id(rss['link'])
    fg.title(rss['title'])
    fg.author( {'name':rss['author'], 'email':rss['email']} )
    fg.description(rss['description'])
    fg.link( href=rss['link'], rel='alternate' )
    for i in data_sorted:
        fe = fg.add_entry()
        fe.id(i['link'])
        fe.title(i['name'])
        fe.link(href=i['link'])
        fe.published(i['updated'])
        fe.description('<p>made by <a href="https://github.com/{o}">{o}</p><p>{d}</p> <img src="{img}"></img><p>{u}</p>'.format(d=i['description'], o=i['owner'], img=i['img'], u=i['updated'].strftime('updated %B %d, %Y at %H:%M')))
    fg.rss_file(rss['output'], pretty=True)

def get_users(github, locations, exclude, page):
    query = '+'.join(['location:"'+l+'"' for l in locations]) + ''.join(['-location:"'+e+'"' for e in exclude])
    url = "https://api.github.com/search/users?sort=repositories&order=desc&q={}&per_page=100&page=".format(query)
    response = requests.get(url + str(page), auth=(github['username'], github['token'])).json()
    return {'users': [u['login'] for u in response['items']],
            'total': response['total_count']}

def get_repos(github, users, since):
    query = 'per_page=100&order=desc&sort=updated&q=pushed:>'+since['string']+'+'+'+'.join(['user:'+u for u in users])
    response = requests.get('https://api.github.com/search/repositories?'+query, auth=(github['username'], github['token'])).json()
    filtered = []
    for item in response['items']:
        pushed = datetime.strptime(item['updated_at']+'+0000', '%Y-%m-%dT%H:%M:%fZ%z')
        if pushed > since['datetime']:
            filtered.append({'name':item['name'],
                             'owner':item['owner']['login'],
                             'img': item['owner']['avatar_url'],
                             'description': item['description'],
                             'link': item['html_url'],
                             'updated': pushed})
    return filtered

def get_since(days):
    day = datetime.now(timezone.utc) - timedelta(days=days)
    return {'datetime': day,
            'string': datetime.strftime(day, '%Y-%m-%d')}

def get_data(github, search, page, since):
    users = get_users(github, search['locations'], search['exclude'], page)
    repos = get_repos(github, users['users'], since)
    return {'repos': repos, 'total_users': users['total']}

github, search, rss = load_config('config.json')
feed = []
since  = get_since(search['days'])

for p in range(1,11): # The Github API only allows us to retrieve the first 1000 results
    data = get_data(github, search, p, since)
    feed.extend(data['repos'])

save(feed, rss)
