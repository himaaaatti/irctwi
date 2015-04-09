#!/usr/bin/env python

import tweepy


if __name__ == '__main__':
    tokens = {}
    tokens['consumer_key'] = 'HdTL890BiQTtiWulpyxmw'
    tokens['consumer_secret'] = '73WAKBfPjHcXKglBWY9YuALxQVl6ZKq95ucctCyg9iQ'
    tokens['access_token'] = '182691245-bfBUbk66c6UegewWW09xUVnpt2yPdQEtzDmfYwBq'
    tokens['access_token_secret'] = 'SvFhjl1ziN8sAECUZLdxiSvkxIDMT5M1Ax9KX1a6w'
    auth = tweepy.OAuthHandler(tokens['consumer_key'], tokens['consumer_secret'])

    auth.set_access_token(tokens['access_token'], tokens['access_token_secret'])

    api = tweepy.API(auth_handler=auth, api_root='/1.1')

    api.update_status(status='hello')

