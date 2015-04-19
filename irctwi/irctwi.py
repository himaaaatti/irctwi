#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import select
import string
import datetime
import ConfigParser


import threading
import tweepy


class IrcTwi(object):
    """irc to twitter gateway server"""

    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_PORT = 26668

    buffer_size = 1024
    concurrent_connection_number = 1

#     us_channel_users = ['us', 'rt', 'fav']
    channel_info = \
            {'#timeline':
                {'users' :['us', 'rt', 'fav'], 'visible': 3, 'topic': 'userstream timeline'},
            '#notification':
                {'users' :['bot'], 'visible': 1, 'topic': 'notification'},
            }

    timeline_ids = []
    timeline_ids_size = 0


    def __init__(self, tokens, host = DEFAULT_HOST, port = DEFAULT_PORT,
            number_of_save_tweet = 1000):
        self.__server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__readfds = set([self.__server_sock])

        self.__host = host
        self.__port = port

#         self.__channel_info = {'timeline': [3, 'userstream timeline'],
#                     'notification': [1, 'notification']}
#         self.__channel_info = [{'name': 'timeline', 'visible': '3', 'topic': 'timeline'},
#                             {'name': 'notification', 'visible': '1', 'topic': 'notification'}]

        IrcTwi.timeline_ids = [0 for i in range(number_of_save_tweet)]

        self.__user_name = ''
        self.__streams = []

        self.__auth = tweepy.OAuthHandler(
                tokens['consumer_key'], tokens['consumer_secret'])

        self.__auth.set_access_token(
                tokens['access_token'], tokens['access_token_secret'])

        self.__api = tweepy.API(self.__auth)



    def run(self):
        """setup and main loop"""

        self.__server_created_at = datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S')

        self.__server_sock.bind((self.__host, self.__port))
        self.__server_sock.listen(IrcTwi.concurrent_connection_number)

        try:
            while True:
                ready_to_read, ready_to_write, in_error = \
                        select.select(self.__readfds, [], [])
                for sock in ready_to_read:
                    if sock is self.__server_sock:
                        connection, address = self.__server_sock.accept()

                        self.__login(connection)

                        self.__readfds.add(connection)

                        us_thread = UserStreamThread(connection, self.__auth)
                        us_thread.start()
                        self.__streams.append(us_thread)

                    else:
                        message = string.split(sock.recv(1024))
                        print(message)

                        if 'PING' == message[0]:
#                             sock.send('PONG {host}\n'.format(host = message[1]))
                            self.__send_message(sock, 'PONG ' + message[1])
                            print('PONG')

                        if 'LIST' == message[0]:
                            self.__list_response(sock)
                            print('LIST')

                        if 'JOIN' == message[0]:
                            channel = message[1]

                            if not channel in IrcTwi.channel_info.keys():
                                self.__send_message(sock,
                                        self.__create_responce_head(403) + channel + ' :No suck channel')
                                break

                            self.__confirmation(sock, message)
                            self.__topic_response(sock, channel)
                            self.__name_response(sock, channel)

                        if 'PRIVMSG' == message[0]:
                            if '#timeline' == message[1]:
                                text = message[2:]
                                print(' '.join(text)[1:])

                                self.__api.update_status(status = ' '.join(text)[1:])

                        if 'NOTICE' == message[0]:

                            if message[1] in IrcTwi.channel_info['#timeline'] and 3 == len(message):
#                                 print(message[2][1:])
                                tweet_id = IrcTwi.get_tweet_id(int(message[2][1:]))
                                print(message[2][1:], tweet_id)
                                if not tweet_id:
                                    print('tweet_id is not correct')
                                    continue

                                if 'rt' == message[1]:
                                    self.__api.retweet(tweet_id)

                                elif 'fav' == message[1]:
                                    #FIXME: below line
                                    self.__api.create_favorite(tweet_id)

        except KeyboardInterrupt:
            pass
        finally:
            UserStreamThread.continue_flag = False
            for stream in self.__streams:
                stream.join()
            for sock in self.__readfds:
                sock.close()

    def __login(self, connection):
        """
        receive USER and NICK command and replie 001 to 004.

            001 RPL_WELCOME
            002 RPL_YOURHOST
            003 RPL_CREATED
            004 RPL_MYINFO
        """

        buf = connection.recv(IrcTwi.buffer_size)
        message = string.split(buf)
        nick = message[1]
        #TODO: when user post first USER
        if message[0] != 'NICK':
            raise NotImplementedError

#          print(message)
        user_index = 0
        if len(message) > 3:
            user = message[3]
            user_index = 2
        else :
            buf = connection.recv(IrcTwi.buffer_size)
            message = string.split(buf)
            user = message[1]

        self.__user_name = user

        if 'USER' != message[user_index]:
            raise NotImplementedError

        print(message)
        # 001 RPL_WELCOME
        self.__send_message(connection,
                self.__create_responce_head(001) + ':Wellcome irc and twitter gateway server!')

        # 002 RPL_YOURHOST
        self.__send_message(connection,
                self.__create_responce_head(002) + ':Yout host is ')

        # 003 RPL_CREATED
        self.__send_message(connection,
                self.__create_responce_head(003) + \
                        ':This server was created at ' + self.__server_created_at)

        # 004 RPL_MYINOF
        self.__send_message(connection,
                self.__create_responce_head(004) + ':')

    def __confirmation(self, socket, message):
        """ """

        socket.send(':{user}!{user}@{host} {message0} :{message1}\n'\
                .format(user = self.__user_name, host = 'localhost',\
                message0 = message[0], message1 = message[1]))


    def __list_response(self, socket):
        """
            322 RPL_LIST
            323 RPL_LISTEND
        """

        for channel, val in IrcTwi.channel_info.iteritems():
            self.__send_message(socket, self.__create_responce_head(322) + \
                    '{channel} {visible} :{topic}'\
                    .format(channel = channel, visible = str(val['visible']), topic = val['topic']))

#             socket.send(':irctwi 322 {user} #{channel} {visible} :{topic}\n'\
#                     .format(user = self.__user_name, channel = info['name'], \
#                     visible = info['visible'], topic = info['topic']))

        socket.send(':irctwi 323 {user} :End of LIST\n'.format(user = self.__user_name))

    def __topic_response(self, socket, channel):
        """
            332 RPL_TOPIC
        """

#         socket.send(self.__create_responce_head(332) + '{channel} :{topic}')

        info = IrcTwi.channel_info[channel]
        self.__send_message(socket, self.__create_responce_head(332) + \
                '{channel} :{topic}'.format(channel = channel, topic = info['topic']))

#         socket.send(':irctwi 332 {user} {channel} :user stream\n'\
#                 .format(user = self.__user_name, channel = channel))

    def __name_response(self, socket, channel):
        """
            353 RPL_NAMREPLY
            366 RPL_ENDOFNAMES
        """

        users = map(lambda x: '@'+x, IrcTwi.channel_info[channel]['users'])
        users.append(self.__user_name)
        print(users)

        self.__send_message(socket,
                self.__create_responce_head(353) + '= {channel} :{user}'\
                        .format(channel = channel, user = ' '.join(users)))
#         socket.send(':irctwi 353 {user} = {channel} :{us} {user}\n'\
#                 .format(user = self.__user_name, channel = channel, us = ' '.join(users)))

#         self.__send_message(socket,
#                 self.__create_responce_head(366) + \
#                         '{channel} :End of NAMES list'.format(channel = channel))
        socket.send(\
                ':irctwi 366 {user} {channel} :End of NAMES list\n'\
                .format(user = self.__user_name, channel = channel))

    def __create_responce_head(self, response_number):
        return ':irctwi ' + str(format(response_number, '03d')) + ' ' + self.__user_name + ' '

    def __send_message(self, socket,  message):
        socket.send(message + '\n')

    @classmethod
    def save_tweet(cls, tweet_id):
        print(tweet_id)
        index = cls.timeline_ids_size % len(cls.timeline_ids)
        cls.timeline_ids[index] = tweet_id
        cls.timeline_ids_size  += 1
        return index

    @classmethod
    def get_tweet_id(cls, save_number):

        if save_number > len(cls.timeline_ids):
            return False

        return cls.timeline_ids[save_number]

class UserStreamThread(threading.Thread):
    """ receive userstream data and post to irc"""

    continue_flag = True

    def __init__(self, socket, auth):
        threading.Thread.__init__(self)

        self.stream = tweepy.Stream(auth, UserStreamListener(socket))

    def run(self):
        while UserStreamThread.continue_flag:
            self.stream.userstream()

class UserStreamListener(tweepy.StreamListener):
    """ stream listener

    """

    def __init__(self, socket):
        tweepy.StreamListener.__init__(self)
        self.__socket = socket
        self.__timeline_user = 'us'
        self.__host = 'localhost'

        self.__timeline_channel = 'timeline'

    def on_status(self, status):
        """
        ひま(himaaatti)
        hello world.
        ------------------
        """
        save_number = IrcTwi.save_tweet(status.id)

        #TODO: user can change print format
        title = '[{save_number}] {name}({screen_name})'\
                .format(screen_name = status.author.screen_name,\
                name = status.author.name.encode('utf-8'), save_number = save_number)

        self.__send_privmsg(self.__timeline_user, self.__host, self.__timeline_channel, title)

        for line in status.text.split('\n'):
            self.__send_privmsg(self.__timeline_user, self.__host, \
                    self.__timeline_channel, line.encode('utf-8'))

        bar = '-------------------'

        self.__send_privmsg(self.__timeline_user, self.__host, self.__timeline_channel, bar)

        return UserStreamThread.continue_flag

    def on_event(self, status):
        """ on event"""
        return UserStreamThread.continue_flag

    def __send_privmsg(self, user, host, channel, message):
        self.__socket.send(self.__get_message(user, host) + 'PRIVMSG #' + channel + ' :' + message + '\n')

    def __get_message(self, user, host):
        return ':{user}!{user}@{host} '.format(user = user, host = host)

if __name__ == '__main__':
    config = ConfigParser.ConfigParser()
    config.read('config')
    tokens = {}
    tokens['consumer_key'] = config.get('tokens', 'consumer_key')
    tokens['consumer_secret'] = config.get('tokens', 'consumer_secret')
    tokens['access_token'] = config.get('tokens', 'access_token')
    tokens['access_token_secret'] = config.get('tokens', 'access_token_secret')
    print(tokens)

    irctwi = IrcTwi(tokens = tokens, number_of_save_tweet = 10)
    irctwi.run()

