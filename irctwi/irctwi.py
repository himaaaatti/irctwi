#!/usr/bin/env python

import socket
import select


class IrcTwi(object):
    """irc to twitter gateway server"""

    __DEFAULT_HOST = '127.0.0.1'
    __DEFAULT_PORT = '26667'
    buffer_size = 1024

    def __init__(self, host = __DEFAULT_HOST, port = __DEFAULT_PORT):
        self.__server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        readfds = set([server_sock])

    def run(self):
        pass

    def __login(self, user_name, host_name, server_name, real_name):
        self.__server_sock.recv(buffer_size)


if __name__ == '__main__':
    irctwi = IrcTwi()
    irctwi.run()
