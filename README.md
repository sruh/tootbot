# TootBot

A small python 3 script to replicate tweets on a mastodon account.

The script only need mastodon login/pass to post toots.

It gets the tweets from Twitter's JS API, then does some cleanup on the content:
- twitter tracking links (t.co) are dereferenced
- twitter hosted pictures are retrieved and uploaded to mastodon

A sqlite database is used to keep track of tweets than have been tooted.

This script is in use for this account:
- a_watch -> https://botsin.space/@a_watch

The script can be simply called by a cron job and can run on any server (does not have to be on the mastodon instance server).

## Setup

```
# clone this repo
git clone https://github.com/cquest/tootbot.git
cd tootbot

# install required python modules
pip3 install -r requirements.txt
```

## Usage

Create a config file, see example.
`python3 tootbot.py`