#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import select
import string
import ConfigParser

import threading
import tweepy


class IrcTwi(object):
    """irc to twitter gateway server"""

    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_PORT = 26668

    buffer_size = 1024
    concurrent_connection_number = 1

    us_channel_users = ['us', 'rt', 'fav']

    timeline_ids = []
    timeline_ids_size = 0


    def __init__(self, tokens, host = DEFAULT_HOST, port = DEFAULT_PORT, save_tweet_number = 1000):
        self.__server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__readfds = set([self.__server_sock])
        self.__host = host
        self.__port = port
        IrcTwi.timeline_ids = [0 for i in range(save_tweet_number)]


        self.__user_name = ''
        self.__streams = []

        self.__auth = tweepy.OAuthHandler(
                tokens['consumer_key'], tokens['consumer_secret'])

        self.__auth.set_access_token(
                tokens['access_token'], tokens['access_token_secret'])

        self.__api = tweepy.API(self.__auth)

    def run(self):
        """setup and main loop"""

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
                            sock.send('PONG {host}\n'.format(host = message[1]))
                            print('PONG')

                        if 'LIST' == message[0]:
                            self.__list_response(sock)
                            print('LIST')

                        if 'JOIN' == message[0]:
                            self.__confirmation(sock, message)
                            self.__topic_response(sock, message[1])
                            self.__name_response(sock, message[1])

                        if 'PRIVMSG' == message[0]:
                            if '#timeline' == message[1]:
                                text = message[2:]
                                print(' '.join(text)[1:])

                                self.__api.update_status(status = ' '.join(text)[1:])

                        if 'NOTICE' == message[0]:

                            if message[1] in IrcTwi.us_channel_users and 3 == len(message):
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
            UserStreamListener.CONTINURE_FLAG = False
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
        connection.send(\
                ':irctwi 001 {user} :Wellcome irc and twitter gateway server!\n'\
                    .format(user = self.__user_name))
        # 002 RPL_YOURHOST
        connection.send(':irctwi 002 {user} :Your host is\n'.format(user = self.__user_name))
#       connection.send(':irctwi 002 ' + nick + ':Your host is ' + server_name + 'running version ' + ver)
        # 003 RPL_CREATED
        connection.send(':irctwi 003 {user} :This server was created\n'.format(user = self.__user_name))
#         connection.send(':irctwi 003 ' + nick + ':This server was created ' + date)
        # 004 RPL_MYINOF
        connection.send(':irctwi 004 {user} :server_name\n'.format(user = self.__user_name))
#         connection.send(':irctwi 004 ' + nick + ':' + server_name + ' ' +)

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

        socket.send(':irctwi 322 {user} #timeline 1 :user stream\n'.format(user = self.__user_name))
        socket.send(':irctwi 323 {user} :End of LIST\n'.format(user = self.__user_name))

    def __topic_response(self, socket, channel):
        """
            332 RPL_TOPIC
        """

        socket.send(':irctwi 332 {user} {channel} :user stream\n'\
                .format(user = self.__user_name, channel = channel))

    def __name_response(self, socket, channel):
        """
            353 RPL_NAMREPLY
            366 RPL_ENDOFNAMES
        """

        users = map(lambda x: '@'+x, IrcTwi.us_channel_users)

        socket.send(':irctwi 353 {user} = {channel} :{us} {user}\n'\
                .format(user = self.__user_name, channel = channel, us = ' '.join(users)))

        socket.send(\
                ':irctwi 366 {user} {channel} :End of NAMES list\n'\
                .format(user = self.__user_name, channel = channel))

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

    def __init__(self, socket, auth):
        threading.Thread.__init__(self)
        self.stream = tweepy.Stream(auth, UserStreamListener(socket))

    def run(self):
        self.stream.userstream()
#         self.stream.close()

class UserStreamListener(tweepy.StreamListener):
    """ stream listener

    """

    CONTINURE_FLAG = True

    def __init__(self, socket):
        tweepy.StreamListener.__init__(self)
        self.__socket = socket

    def on_status(self, status):
#         print(status.id)
        save_number = IrcTwi.save_tweet(status.id)
#          print(status.text)#.decode('utf-8')
        """
        ひま(himaaatti)
        hello world.
        ------------------
        """

        #TODO: user can change print format
        title = '[{save_number}] {name}({screen_name})'\
                .format(screen_name = status.author.screen_name,\
                name = status.author.name.encode('utf-8'), save_number = save_number)

        self.__socket.send(':{us}!{us}@{host} PRIVMSG #{channel} :{title}\n'\
                .format(us = 'us', host = 'localhost', channel = 'timeline', \
                title = title))

        for line in status.text.split('\n'):
            self.__socket.send(':{us}!{us}@{host} PRIVMSG #{channel} :{text}\n'\
                    .format(us = 'us', host = 'localhost', channel = 'timeline', \
                    text = line.encode('utf-8')))

        bar = '-------------------'
        self.__socket.send(':{us}!{us}@{host} PRIVMSG #{channel} :{bar}\n'\
                .format(us = 'us', host = 'localhost', channel = 'timeline', \
                bar = bar))

        return UserStreamListener.CONTINURE_FLAG

    def on_event(self, status):
        """ on event"""

        print(status)

        return

    def close(self):
        self.__socket.close()

if __name__ == '__main__':

    config = ConfigParser.ConfigParser()
    config.read('config')
    tokens = {}
    tokens['consumer_key'] = config.get('tokens', 'consumer_key')
    tokens['consumer_secret'] = config.get('tokens', 'consumer_secret')
    tokens['access_token'] = config.get('tokens', 'access_token')
    tokens['access_token_secret'] = config.get('tokens', 'access_token_secret')
    print(tokens)

    irctwi = IrcTwi(tokens = tokens)
    irctwi.run()
