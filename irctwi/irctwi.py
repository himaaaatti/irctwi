#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import select
import string
import datetime
from logging import getLogger
import threading
import ConfigParser
import sys
import traceback

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

        self.logger = getLogger(__name__)
        self.logger.info('start server')

        self.__server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__readfds = set([self.__server_sock])

        self.__host = host
        self.__port = port
        IrcTwi.timeline_ids_size = number_of_save_tweet

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
                        peer = sock.getpeername()
                        self.logger.info('from {address}, {port}: {message}'\
                                .format(address = peer[0], port = (str(peer[1])), \
                                message = ' '.join(message)))


                        if 'PING' == message[0]:
                            self.logger.debug('received PING command from ' + message[1])
                            self.__send_message(sock, 'PONG ' + message[1])

                        if 'LIST' == message[0]:
                            self.logger.debug('received LIST command')
                            self.__list_response(sock)

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

                                self.__api.update_status(status = ' '.join(text)[1:])
                                self.logger.info('tweet text: ' + ' '.join(text)[1:])

                        if 'NOTICE' == message[0]:

                            if message[1] in IrcTwi.channel_info['#timeline']['users'] and 3 == len(message):
                                tweet_id = IrcTwi.get_tweet_id(int(message[2][1:]))
                                if not tweet_id:
                                    self.logger.warn('tweet_id is not correct') #FIXME
                                    continue

                                if 'rt' == message[1]:
                                    #TODO: loggin response data
                                    self.__api.retweet(tweet_id)
                                    self.logger.info('retweet id is : ' + str(tweet_id))

                                elif 'fav' == message[1]:
                                    #TODO: loggin response data
                                    self.__api.create_favorite(tweet_id)
                                    self.logger.info('favorite id is : ' + str(tweet_id))

        except KeyboardInterrupt:
            pass
        except:
            self.logger.critical(traceback.format_exc())
            raise
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

        self.logger.info('login user: ' + self.__user_name)

        # 001 RPL_WELCOME
        self.__send_message(connection,
                self.__create_responce_head(001) + ':Wellcome irc and twitter gateway server!')
        self.logger.debug('sent 001 RPL_WELCOME')

        # 002 RPL_YOURHOST
        self.__send_message(connection,
                self.__create_responce_head(002) + ':Yout host is ')
        self.logger.debug('sent 002 RPL_YOURHOST')

        # 003 RPL_CREATED
        self.__send_message(connection,
                self.__create_responce_head(003) + \
                        ':This server was created at ' + self.__server_created_at)
        self.logger.debug('sent 003 RPL_CREATED')

        # 004 RPL_MYINOF
        self.__send_message(connection,
                self.__create_responce_head(004) + ':')
        self.logger.debug('sent 004 RPL_MYINFO')

    def __confirmation(self, socket, message):
        """ """

        self.__send_message(socket, ':{user}!{user}@{host} {message0} :{message1}'\
                .format(user = self.__user_name, host = 'localhost',\
                message0 = message[0], message1 = message[1]))
        self.logger.debug('sent confirmation')


    def __list_response(self, socket):
        """
            322 RPL_LIST
            323 RPL_LISTEND
        """

        for channel, val in IrcTwi.channel_info.iteritems():
            self.__send_message(socket, self.__create_responce_head(322) + \
                    '{channel} {visible} :{topic}'\
                    .format(channel = channel, visible = str(val['visible']), topic = val['topic']))

        socket.send(':irctwi 323 {user} :End of LIST\n'.format(user = self.__user_name))
        self.logger.debug('send 322 RPL_LIST')
        self.logger.debug('send 323 RPL_LISTEND')

    def __topic_response(self, socket, channel):
        """
            332 RPL_TOPIC
        """

        info = IrcTwi.channel_info[channel]
        self.__send_message(socket, self.__create_responce_head(332) + \
                '{channel} :{topic}'.format(channel = channel, topic = info['topic']))
        self.logger.debug('sent 332 RPL_TOPIC')

    def __name_response(self, socket, channel):
        """
            353 RPL_NAMREPLY
            366 RPL_ENDOFNAMES
        """

        users = map(lambda x: '@'+x, IrcTwi.channel_info[channel]['users'])
        users.append(self.__user_name)
#         print(users)

        self.__send_message(socket,
                self.__create_responce_head(353) + '= {channel} :{user}'\
                        .format(channel = channel, user = ' '.join(users)))
        self.logger.debug('sent 353 RPPL_NAMREPLY')

        self.__send_message(socket,
                self.__create_responce_head(366) + \
                        '{channel} :End of NAMES list'.format(channel = channel))

        self.logger.debug('send 356 RPL_ENDOFNAMES')

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
        getLogger(__name__).debug('in save_tweet: index is ' + str(index))
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
        self.logger = getLogger(__name__)

        self.stream = tweepy.Stream(auth, UserStreamListener(socket))

    def run(self):
        try:
            while UserStreamThread.continue_flag:
                self.logger.info('start userstream')
                self.stream.userstream()
        except:
            self.logger.critical(traceback.format_exc())
            raise

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

    log_file_path = config.get('log', 'directory_path')

    tokens['consumer_key'] = config.get('tokens', 'consumer_key')
    tokens['consumer_secret'] = config.get('tokens', 'consumer_secret')
    tokens['access_token'] = config.get('tokens', 'access_token')
    tokens['access_token_secret'] = config.get('tokens', 'access_token_secret')

    import logging
    import logging.handlers
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    rotating_file_handler = logging.handlers.RotatingFileHandler(
            filename = 'irctwi.log',
            maxBytes = 1024 * 1024,
            backupCount = 5
            )
    rotating_file_handler.setLevel(logging.DEBUG)
    rotating_file_handler.setFormatter(formatter)

    logger.addHandler(rotating_file_handler)

    for name, val in tokens.iteritems():
        logger.debug(name + ' : ' + val)

    irctwi = IrcTwi(tokens = tokens)
    try:
        irctwi.run()
    except:
#         print(sys.exc_info())
#         error_info = sys.exc_info()
#         logger.critical(error_info[1])
#         print(help(error_info[2]))
#         for line in error_info[2].format_exc().split('\n'):
#             logger.critical(line)
#         logger.critical(error_info[2])
        logger.critical(traceback.format_exc())
