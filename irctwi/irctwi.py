#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket
import select
import string

import threading
import tweepy


class IrcTwi(object):
    """irc to twitter gateway server"""

    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_PORT = 26668

    buffer_size = 1024
    concurrent_connection_number = 1

    def __init__(self, tokens, host = DEFAULT_HOST, port = DEFAULT_PORT):
        self.__server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__readfds = set([self.__server_sock])
        self.__host = host
        self.__port = port

        self.__user_name = ''
        self.__streams = []

        self.__auth = tweepy.OAuthHandler(
                tokens['consumer_key'], tokens['consumer_secret'])

        self.__auth.set_access_token(
                tokens['access_token'], tokens['access_token_secret'])


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
                            sock.send('PONG {host}\n'.format(host=message[1]))
                            print('PONG')


                        if 'LIST' == message[0]:
                            self.__list_response(sock)
                            print('LIST')

                        if 'JOIN' == message[0]:
                            self.__confirmation(sock, message)
                            self.__topic_response(sock, message[1])
                            self.__name_response(sock, message[1])


        except KeyboardInterrupt:
            pass
        finally:
            UserStreamListener.CONTINURE_FLAG = False
            for stream in self.__streams:
                stream.join()
#              for sock in self.__readfds:
#                  sock.close()


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
        if len(message) > 3:
            user = message[2]
        else :
            buf = connection.recv(IrcTwi.buffer_size)
            message = string.split(buf)
            user = message[1]

        self.__user_name = user

        if 'USER' != message[0]:
            raise NotImplementedError

        print(message)
        # 001 RPL_WELCOME
        connection.send(\
                ':irctwi 001 {user} :Wellcome irc and twitter gateway server!\n'\
                    .format(user=self.__user_name))
        # 002 RPL_YOURHOST
        connection.send(':irctwi 002 {user} :Your host is\n'.format(user=self.__user_name))
#       connection.send(':irctwi 002 ' + nick + ':Your host is ' + server_name + 'running version ' + ver)
        # 003 RPL_CREATED
        connection.send(':irctwi 003 {user} :This server was created\n'.format(user=self.__user_name))
#         connection.send(':irctwi 003 ' + nick + ':This server was created ' + date)
        # 004 RPL_MYINOF
        connection.send(':irctwi 004 {user} :server_name\n'.format(user=self.__user_name))
#         connection.send(':irctwi 004 ' + nick + ':' + server_name + ' ' +)

    def __confirmation(self, socket, message):
#          print(':{0}!{1} {2}\n'.format('hima', 'localhost', ' '.join(message)))
#          print(':{user}!{user}@{host} {message0} :{message1}\n'\
#                  .format(user=self.__user_name, host='localhost',\
#                  message0=message[0], message1=message[1]))
        socket.send(':{user}!{user}@{host} {message0} :{message1}\n'\
                .format(user=self.__user_name, host='localhost',\
                message0=message[0], message1=message[1]))


    def __list_response(self, socket):
        """
            322 RPL_LIST
            323 RPL_LISTEND
        """

        socket.send(':irctwi 322 {user} #timeline 1 :user stream\n'.format(user=self.__user_name))
        socket.send(':irctwi 323 {user} :End of LIST\n'.format(user=self.__user_name))

    def __topic_response(self, socket, channel):
        """
            332 RPL_TOPIC
        """

        socket.send(':irctwi 332 {user} {channel} :user stream\n'\
                .format(user=self.__user_name, channel=channel))
#          print(':irctwi 332 {user} {channel} :user stream\n'\
#                  .format(user=self.__user_name, channel=channel))

    def __name_response(self, socket, channel):
        """
            353 RPL_NAMREPLY
            366 RPL_ENDOFNAMES
        """

        socket.send(':irctwi 353 {user} = {channel} :{us} {user}\n'\
                .format(user=self.__user_name, channel=channel, us='us'))
#          print(':irctwi 353 {} = {1} :{2} {3}\n'.format('hima', channel, 'us', 'hima'))

        socket.send(\
                ':irctwi 366 {user} {channel} :End of NAMES list\n'\
                .format(user=self.__user_name, channel=channel))
#          print(':irctwi 366 {user} {} :End of NAMES list\n'.format('hima', channel))

        #:irc.example.net 366 hama #test :End of NAMES list

class UserStreamThread(threading.Thread):
    """ receive userstream data and post to irc"""

    def __init__(self, socket, auth):
        threading.Thread.__init__(self)
        self.stream = tweepy.Stream(auth, UserStreamListener(socket))

    def run(self):
        self.stream.userstream()
        self.stream.close()

class UserStreamListener(tweepy.StreamListener):
    """ stream listener """

    CONTINURE_FLAG = True

    def __init__(self, socket):
        tweepy.StreamListener.__init__(self)
        self.__socket = socket


    def on_status(self, status):
#          print(status.text)#.decode('utf-8')
        title = '{name}({screen_name})'\
                .format(screen_name=status.author.screen_name,\
                name=status.author.name.encode('utf-8'))

        text = '{text}'\
                .format(name=status.author.name.encode('utf-8'), \
                screen_name=status.author.screen_name, text=status.text.encode('utf-8'))

        self.__socket.send(':{us}!{us}@{host} PRIVMSG #{channel} :{title}\n'\
                .format(us='us', host='localhost', channel='timeline', \
                title=title))

        self.__socket.send(':{us}!{us}@{host} PRIVMSG #{channel} :{text}\n'\
                .format(us='us', host='localhost', channel='timeline', \
                text=text))

        bar = '-------------------'
        self.__socket.send(':{us}!{us}@{host} PRIVMSG #{channel} :{bar}\n'\
                .format(us='us', host='localhost', channel='timeline', \
                bar=bar))


        return UserStreamListener.CONTINURE_FLAG

    def close(self):
        self.__socket.close()

if __name__ == '__main__':
    tokens = {}
    tokens['consumer_key'] = 'HdTL890BiQTtiWulpyxmw'
    tokens['consumer_secret'] = '73WAKBfPjHcXKglBWY9YuALxQVl6ZKq95ucctCyg9iQ'
    tokens['access_token'] = '182691245-bfBUbk66c6UegewWW09xUVnpt2yPdQEtzDmfYwBq'
    tokens['access_token_secret'] = 'SvFhjl1ziN8sAECUZLdxiSvkxIDMT5M1Ax9KX1a6w'
    irctwi = IrcTwi(tokens=tokens)
    irctwi.run()
