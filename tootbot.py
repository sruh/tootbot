#!/usr/bin/env python3
import os.path, sys, re, sqlite3, requests, feedparser, configparser

from datetime import datetime, timedelta
from mastodon import Mastodon
from twitter_scraper import get_tweets

config = configparser.ConfigParser()
try:
    config.read_file(open('tootbot.cfg'))
except:
    print("Please create a config file (tootbot.cfg)")
    sys.exit(1)

# sqlite db to store processed tweets (and corresponding toots ids)
sql = sqlite3.connect('tootbot.db')
db = sql.cursor()
db.execute('''CREATE TABLE IF NOT EXISTS tweets (tweet text, toot text,
           twitter text, mastodon text, instance text)''')

source = config['DEFAULT']['twitter_handle']
mastodon = config['DEFAULT']['mastodon_email']
passwd = config['DEFAULT']['mastodon_password']
instance = config['DEFAULT']['mastodon_instance']
tags = config['DEFAULT']['custom_tags']
days = int(config['DEFAULT']['days'])

mastodon_api = None

posts = []
ts = get_tweets(source, pages=1)
for t in ts:
    posts.append({'id': 'https://twitter.com/' + source + '/status/' + t['tweetId'], 'author': '(@' + source + ')', 'published_parsed': t['time'], 'title': t['text'], 'media': t['entries']['photos']})
twitter = source

for t in reversed(posts):
    # check if this tweet has been processed
    db.execute('SELECT * FROM tweets WHERE tweet = ? AND twitter = ?  and mastodon = ? and instance = ?', (t['id'], source, mastodon, instance))  # noqa
    last = db.fetchone()
    dt = t['published_parsed']
    age = datetime.now()-datetime(dt.year, dt.month, dt.day,
                                  dt.hour, dt.minute, dt.second)
    # process only unprocessed tweets less than 1 day old
    if last is None and age < timedelta(days=days):
        if mastodon_api is None:
            # Create application if it does not exist
            if not os.path.isfile(instance+'.secret'):
                if Mastodon.create_app(
                    'tootbot',
                    api_base_url='https://'+instance,
                    to_file=instance+'.secret'
                ):
                    print('tootbot app created on instance '+instance)
                else:
                    print('failed to create app on instance '+instance)
                    sys.exit(1)

            try:
                mastodon_api = Mastodon(
                  client_id=instance+'.secret',
                  api_base_url='https://'+instance
                )
                mastodon_api.log_in(
                    username=mastodon,
                    password=passwd,
                    scopes=['read', 'write'],
                    to_file=mastodon+".secret"
                )
            except:
                print("ERROR: First Login Failed!")
                sys.exit(1)

        c = t['title']
        if twitter and t['author'].lower() != ('(@%s)' % twitter).lower():
            c = ("RT https://twitter.com/%s\n" % t['author'][2:-1]) + c
        toot_media = []
        for p in t['media']:
            media = requests.get(p)
            media_posted = mastodon_api.media_post(media.content, mime_type=media.headers.get('content-type'))
            toot_media.append(media_posted['id'])

        # replace short links by original URL
        m = re.search(r"http[^ \xa0]*", c)
        if m is not None:
            l = m.group(0)
            r = requests.get(l, allow_redirects=False)
            if r.status_code in {301, 302}:
                c = c.replace(l, r.headers.get('Location'))

        # remove pic.twitter.com links
        m = re.search(r"pic.twitter.com[^ \xa0]*", c)
        if m is not None:
            l = m.group(0)
            c = c.replace(l, ' ')

        # remove ellipsis
        c = c.replace('\xa0…', ' ')

        # remove reference to own account
        c = c.replace('@' + source, '@' + source + '@twitter.com')

        if twitter is None:
            c = c + '\nSource: '+ t.authors[0].name +'\n\n' + t.link

        if tags:
            c = c + '\n' + tags

        if toot_media is not None:
            toot = mastodon_api.status_post(c, in_reply_to_id=None,
                                            media_ids=toot_media,
                                            sensitive=False,
                                            visibility='public',
                                            spoiler_text=None)
            if "id" in toot:
                db.execute("INSERT INTO tweets VALUES ( ? , ? , ? , ? , ? )",
                           (t['id'], toot["id"], source, mastodon, instance))
                sql.commit()
