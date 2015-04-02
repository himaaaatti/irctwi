#!/usr/bin/env python

import socket
import select


class IrcTwi(object):
    """irc to twitter gateway server"""

    __DEFAULT_HOST = '127.0.0.1'
    __DEFAULT_PORT = 26667
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
                        self.__readfds.add(connection)


                    else:
                        pass
    #                      command = sock.recv(1024)
    #                      print(command)
    #                      if command.decode().split(' ')[0] == 'USER':
    #                          message = bytes('001', 'utf-8')
    #                          sock.send(message)
        except KeyboardInterrupt:
            pass
        finally:
            for sock in self.__readfds:
                sock.close()


    def __login(selp):
        """receive USER and NICK command"""
        message = self.__server_sock.recv(buffer_size)
        print(message)
        message = self.



if __name__ == '__main__':
    irctwi = IrcTwi()
    irctwi.run()
