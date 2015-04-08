#!/usr/bin/env python

import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../irctwi')

import unittest
import mox
import socket

import irctwi

class IrcTwiTestCase(unittest.TestCase):

    def setUp(self):
        self.mocker = mox.Mox()

    def testHandler(self):

        client_socket_mock = self.mocker.CreateMock(socket.socket(socket.AF_INET, socket.SOCK_STREAM))

#          client_socket_mock.shutdown(socket.SHUT_RDWR)

#          client_socket_mock.close()

        server_socket_mock = self.mocker.CreateMock(socket.socket(socket.AF_INET, socket.SOCK_STREAM))

#          client_socket_mock.send('NICK helo\n').AndReturn()

        server = irctwi.IrcTwi()


        client_socket_mock.connect((irctwi.IrcTwi.DEFAULT_HOST, irctwi.IrcTwi.DEFAULT_PORT))
        client_socket_mock.send('USER helo localhost * :helo\n')

        server.run()
        self.mocker.ReplayAll()
        self.mocker.VerifyAll()

    def run_test():
        pass



if __name__ == '__main__':
    unittest.main()
