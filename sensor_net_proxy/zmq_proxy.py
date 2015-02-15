# -*- coding: utf-8 -*-
#
# Modular sensors network <-> controller proxy
# Copyright (C) 2014-2015  Tomas Hozza <thozza@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# he Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import zmq

from sensor_net_proxy.logger import logger
from sensor_net_proxy.exceptions import SensorNetProxyError


class ZmqProxy(object):
    """
    Class representing ZMQ I/O process
    """

    def __init__(self):
        self._zmq_ctx = zmq.Context()
        # publisher socket
        self._publisher_socket = self._zmq_ctx.socket(zmq.PUB)
        self._publisher_socket.bind('tcp://*:5556')
        # subscriber socket
        #self._subscriber_socket = self._zmq_ctx.socket(zmq.SUB)
        #self._subscriber_socket.connect()

    def publish(self, msg):
        """
        Publish MySensorsMsg

        :param msg: MySensorsMsg
        :return:
        """
        # TODO: log message
        self._publisher_socket.send_json(msg.__dict__)

    def handle_incoming_msg(self, sock):
        """
        Handle incoming message on ZMQ socket.
        """
        pass

    def get_sockets(self):
        """
        Return sockets on which we can expect incoming messages
        """
        return [self._subscriber_socket]

    def close_sockets(self):
        self._publisher_socket.close()
        #self._subscriber_socket.close()

    def is_zmq_socket(self, sock):
        return self._subscriber_socket == sock