#!/usr/bin/env python

import socket
import select
import string


class IrcTwi(object):
    """irc to twitter gateway server"""

    DEFAULT_HOST = '127.0.0.1'
    DEFAULT_PORT = 26668
    buffer_size = 1024
    concurrent_connection_number = 5

    def __init__(self, host = DEFAULT_HOST, port = DEFAULT_PORT):
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

                        if 'PING' == message[0]:
                            sock.send('PONG ' + message[1] + '\n')
                            print('PONG')


                        if 'LIST' == message[0]:
                            self.__list_response(sock)
                            print('LIST')

                        if 'JOIN' == message[0]:
                            self.__confirmation(sock, message)
                            self.__topic_response(sock, message[1])
                            self.__name_response(sock, message[1])

                            sock.send(':us!~us@localhost PRIVMSG timeline :us\n')
                            print(':us!~us@localhost PRIVMSG timeline :us\n')

                        print(message)


        except KeyboardInterrupt:
            pass
        finally:
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
        if message[0] != 'NICK':
            connection.send('please NICK command\n')
            self.__login(connection)
            return

        print(message)
        if len(message) > 3:
            user = message[2]
        else :
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
#       connection.send(':irctwi 002 ' + nick + ':Your host is ' + server_name + 'running version ' + ver)
        # 003 RPL_CREATED
        connection.send(':irctwi 003 ' + nick + ' :This server was created\n')
#         connection.send(':irctwi 003 ' + nick + ':This server was created ' + date)
        # 004 RPL_MYINOF
        connection.send(':irctwi 004 ' + nick + ' :server_name\n')
#         connection.send(':irctwi 004 ' + nick + ':' + server_name + ' ' +)

    def __confirmation(self, socket, message):
#          print(':{0}!{1} {2}\n'.format('hima', 'localhost', ' '.join(message)))
        print(':{0}!{0}@{1} {2} :{3}\n'.format('hima', 'localhost', message[0], message[1]))
        socket.send(':{0}!{0}@{1} {2} :#{3}\n'.format('hima', 'localhost', message[0], message[1]))


    def __list_response(self, socket):
        """
            322 RPL_LIST
            323 RPL_LISTEND
        """
        socket.send(':irctwi 322 {0} #timeline 1 :user stream\n'.format('hima'))
        socket.send(':irctwi 323 {0} :End of LIST\n'.format('hima'))

    def __topic_response(self, socket, channel):
        """
            332 RPL_TOPIC
        """
        socket.send(':irctwi 332 {0} {1} :user stream\n'.format('hima', channel))
        print(':irctwi 332 {0} {1} :user stream\n'.format('hima', channel))

    def __name_response(self, socket, channel):
        """
            353 RPL_NAMREPLY
            366 RPL_ENDOFNAMES
        """
        socket.send(':irctwi 353 {0} = {1} :{2} {3}\n'.format('hima', channel, 'us', 'hima'))
        print(':irctwi 353 {0} = {1} :{2} {3}\n'.format('hima', channel, 'us', 'hima'))
        socket.send(':irctwi 366 {0} {1} :End of NAMES list\n'.format('', channel))
        print(':irctwi 366 {0} {1} :End of NAMES list\n'.format('hima', channel))

        #:irc.example.net 366 hama #test :End of NAMES list



if __name__ == '__main__':
    irctwi = IrcTwi()
    irctwi.run()
