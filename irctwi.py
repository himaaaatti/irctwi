#!/usr/bin/env python3


import socket
import select

def main():
    host = '127.0.0.1'
    port = 26668

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    readfds = set([server_sock])

    try:

        server_sock.bind((host, port))
        server_sock.listen(5)

        while True:
            ready_to_read, ready_to_write, in_error = \
                    select.select(readfds, [], [])
            for sock in ready_to_read:
                if sock is server_sock:
                    connection, address = server_sock.accept()
                    readfds.add(connection)

                else:
                    command = sock.recv(1024)
                    print(command)
                    if command.decode().split(' ')[0] == 'USER':
                        message = bytes('001', 'utf-8')
                        sock.send(message)

    except:
        pass

    finally:
        for sock in readfds:
            sock.close()

    return


if __name__ == '__main__':
    main()
