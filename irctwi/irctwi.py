#!/usr/bin/env python

import socket
import select
import string


class IrcTwi(object):
    """irc to twitter gateway server"""

    __DEFAULT_HOST = '127.0.0.1'
    __DEFAULT_PORT = 26668
    buffer_size = 1024
    concurrent_connection_number = 5

    def __init__(self, host = __DEFAULT_HOST, port = __DEFAULT_PORT):
        self.__server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__readfds = set([self.__server_sock])
        self.__host = host
        self.__port = port


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

                        self.test_message(connection)

                        self.__readfds.add(connection)
                    else:
                        message = string.split(sock.recv(1024))
                        print(message)
#                         if 0 == len(message):
#                             sock.close()

                        if 'PING' == message[0]:
                            sock.send('PONG ' + message[1] + '\n')
                            print('PONG')



        except KeyboardInterrupt:
            pass
        finally:
            for sock in self.__readfds:
                sock.close()


    def __login(self, connection):
        """receive USER and NICK command"""
        buf = connection.recv(IrcTwi.buffer_size)
        message = string.split(buf)
        nick = message[1]
        if message[0] != 'NICK':
            connection.send('please NICK command\n')
            self.__login(connection)

        print(message)
        buf = connection.recv(IrcTwi.buffer_size)
        message = string.split(buf)
        user = message[1]
        if 'USER' != message[0]:
            connection.send('please USER command\n')
            self.__login(connection)

        print(message)
        # 001 RPL_WELCOME
        connection.send(':irctwi 001 ' + nick + ' :Wellcome irc and twitter gateway server!\n')
        # 002 RPL_YOURHOST
        connection.send(':irctwi 002 ' + nick + ' :Your host is\n')
#         connection.send(':irctwi 002 ' + nick + ':Your host is ' + server_name + 'running version ' + ver)
        # 003 RPL_CREATED
        connection.send(':irctwi 003 ' + nick + ' :This server was created\n')
#         connection.send(':irctwi 003 ' + nick + ':This server was created ' + date)
        # 004 RPL_MYINOF
        connection.send(':irctwi 004 ' + nick + ' :server_name\n')
#         connection.send(':irctwi 004 ' + nick + ':' + server_name + ' ' +)


    def test_message(self, connection):
        connection.send(':owner NJOIN #user_stream\n')
#         connection.send(':owner PRIVMSG #userstrem :user stream start!!\n')
#       :hima!~hima@localhost PRIVMSG #good :ok!

if __name__ == '__main__':
    irctwi = IrcTwi()
    irctwi.run()
