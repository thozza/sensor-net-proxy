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

import os
import select

from sensor_net_proxy.logger import logger, LoggerHelper, logging
from sensor_net_proxy.my_sensors import MySensorsEthernetProxy
from sensor_net_proxy.zmq_proxy import ZmqProxy


class Application(object):

    def __init__(self, cli_conf=None):
        """
        Initialize the application

        :param cli_conf: ArgsParser object with configuration gathered from commandline
        :return:
        """
        self._conf = cli_conf
        self._debug_log_file = self._add_debug_log_file()

        if self._conf.verbose:
            LoggerHelper.add_stream_handler(logger, logging.DEBUG)
        else:
            LoggerHelper.add_stream_handler(logger, logging.INFO)

        self._add_debug_log_file()

    def _add_debug_log_file(self):
        """
        Add the application wide debug log file
        :return:
        """
        debug_log_file = os.path.join(os.getcwd(), 'sensor-net-proxy-debug.log')
        try:
            LoggerHelper.add_file_handler(logger,
                                          debug_log_file,
                                          logging.Formatter("%(asctime)s %(levelname)s %(message)s"),
                                          logging.DEBUG)
        except (IOError, OSError):
            logger.warning("Can not create debug log '{0}'".format(debug_log_file))
        else:
            return debug_log_file

    def run(self):
        logger.info('Sensor Net Proxy staring')

        mysensors_proxy = MySensorsEthernetProxy(self._conf.interface, self._conf.port, self._conf.dynamic_discovery)
        zmq_proxy = ZmqProxy()

        try:
            sockets = mysensors_proxy.get_sockets()

            while True:
                ready_r, ready_w, _ = select.select(sockets, [], [])
                for s in ready_r:
                    if mysensors_proxy.is_socket_broadcast(s):
                        mysensors_proxy.handle_dynamic_discovery(s)
                    else:
                        msg, client = mysensors_proxy.handle_incoming_msg(s)
                        zmq_proxy.publish(msg)
        finally:
            mysensors_proxy.close_sockets()
            zmq_proxy.close_sockets()

