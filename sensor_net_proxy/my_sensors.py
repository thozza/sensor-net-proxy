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

import netifaces
import socket

from sensor_net_proxy.logger import logger
from sensor_net_proxy.exceptions import SensorNetProxyError


class MySensorsEthernetProxy(object):
    """
    Class representing a proxy for MySensors Ethernet Gateway.
    """

    def __init__(self, interface, port=5003, dynamic_discovery=True):
        """

        :param interface:
        :param dynamic_discovery:
        :return None
        """
        self._listen_sockets = []
        self._listen_brcast_sockets = []
        self._ethernet_gateways_addresses = []
        self._bcast_addr_to_listen_addr = {}
        self._interface = interface
        self._port = port
        self._dynamic_discovery = dynamic_discovery

        if interface not in netifaces.interfaces():
            raise SensorNetProxyError("Interface '{0}' does not exist. Existing interfaces are '{1}'".format(
                interface,
                str(netifaces.interfaces())))

        self._create_listening_sockets()

    def _create_listening_sockets(self):
        """
        Creates listening UDP socket for all addresses on the particular interface.
        """
        logger.debug("Creating listening sockets interface '{0}'".format(self._interface))
        # go through IPv4 addresses only
        try:
            for addrs in netifaces.ifaddresses(self._interface)[netifaces.AF_INET]:
                logger.debug("Interface addresses '{0}'".format(addrs))
                listen_sock = MySensorsEthernetProxy.create_listening_udp_socket(addrs['addr'], self._port)
                self._listen_sockets.append(listen_sock)

                if self._dynamic_discovery:
                    try:
                        self._listen_brcast_sockets.append(MySensorsEthernetProxy.create_listening_udp_socket(
                            addrs['broadcast'], self._port))
                        # mapping of broadcast address to the listening address
                        self._bcast_addr_to_listen_addr[addrs['broadcast']] = (addrs['addr'], listen_sock)
                    except KeyError:
                        raise SensorNetProxyError("Using dynamic discovery, but the selected interface does not support"
                                                  "broadcast!")
        except KeyError:
            raise SensorNetProxyError("The selected interface '{0}' does not have any "
                                      "IPv4 address".format(self._interface))

    @staticmethod
    def create_listening_udp_socket(address, port):
        """
        Create listening UDP socket and return it
        """
        logger.debug("Creating listening socket on address:port '{0}:{1}'".format(address, port))
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # reuse address and port to prevent errors when kernel didn't free the FD yet
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
            sock.bind((address, port))
        except socket.error as e:
            raise SensorNetProxyError(e.strerror)

        return sock

    def close_sockets(self):
        """
        Close all opened sockets
        """
        logger.debug("Closing all sockets")
        for s in self._listen_sockets:
            s.close()
        for s in self._listen_brcast_sockets:
            s.close()

    def get_sockets(self):
        """
        Return all listening sockets created by the proxy
        """
        return self._listen_sockets + self._listen_brcast_sockets

    def is_socket_broadcast(self, sock):
        """
        Returns true if the socket is listening on a broadcast address, otherwise False.
        """
        return sock in self._listen_brcast_sockets

    def handle_dynamic_discovery(self, sock):
        """
        Handle the dynamic discovery request.
        """
        raw_msg, client = sock.recvfrom(2**16)
        logger.info("Received dynamic discovery request from '{0}'".format(client))

        logger.debug("Received raw message '{0}'".format(raw_msg.strip()))
        msg = MySensorsMsg.from_serial_msg(raw_msg.strip())

        if msg.message_type != MySensorsMsg.MSG_TYPE_INTERNAL or msg.sub_type != MySensorsMsg.INTERNAL_TYPE_CONTROLLER_DISCOVERY:
            logger.warning("Bogus msg received... type='{0}'".format(
                MySensorsMsg.msg_type_to_str(msg.message_type)))
            return

        listen_addr, listen_sock = self._bcast_addr_to_listen_addr[sock.getsockname()[0]]
        msg.payload = '{0}'.format(listen_addr)

        logger.debug("Sending raw message '{0}' to '{1}'".format(msg.to_serial_msg().strip(), client))
        listen_sock.sendto(msg.to_serial_msg(), client)

        # add the gateway address to the list of gateways
        self._ethernet_gateways_addresses.append((client, listen_sock))

    def handle_incoming_msg(self, sock):
        """
        Handle the incoming message.
        """
        # TODO: move this to separate method?
        raw_msg, client = sock.recvfrom(2**16)
        logger.info("Received message from '{0}'".format(client))

        logger.debug("Received raw message '{0}'".format(raw_msg.strip()))
        msg = MySensorsMsg.from_serial_msg(raw_msg.strip())

        return msg, client

    def send_msg_to_gateway(self, msg):
        """
        Send MySensorsMsg to the gateway
        """
        logger.info("Sending message '{0}' to gateways".format(msg.to_serial_msg().strip()))
        for gw_addr, proxy_socket in self._ethernet_gateways_addresses:
            logger.info("Sending message to gateway '{0}'".format(gw_addr))
            proxy_socket.sendto(msg.to_serial_msg(), gw_addr)


class MySensorsMsg(object):
    """
    Class representing MySensors message (v1.4)
    http://www.mysensors.org/download/serial_api_14
    """

    # Message Type
    MSG_TYPE_PRESENTATION = 0
    MSG_TYPE_SET = 1
    MSG_TYPE_REQ = 2
    MSG_TYPE_INTERNAL = 3
    MSG_TYPE_STREAM = 4

    # Type of sensor data for SET/REQ/ACK messages
    SET_REQ_VALUE_TEMP = 0
    SET_REQ_VALUE_HUM = 1
    SET_REQ_VALUE_LIGHT = 2
    SET_REQ_VALUE_DIMMER = 3
    SET_REQ_VALUE_PRESSURE = 4
    SET_REQ_VALUE_FORECAST = 5
    SET_REQ_VALUE_RAIN = 6
    SET_REQ_VALUE_RAINRATE = 7
    SET_REQ_VALUE_WIND = 8
    SET_REQ_VALUE_GUST = 9
    SET_REQ_VALUE_DIRECTION = 10
    SET_REQ_VALUE_UV = 11
    SET_REQ_VALUE_WEIGHT = 12
    SET_REQ_VALUE_DISTANCE = 13
    SET_REQ_VALUE_IMPEDANCE = 14
    SET_REQ_VALUE_ARMED = 15
    SET_REQ_VALUE_TRIPPED = 16
    SET_REQ_VALUE_WATT = 17
    SET_REQ_VALUE_KWH = 18
    SET_REQ_VALUE_SCENE_ON = 19
    SET_REQ_VALUE_SCENE_OFF = 20
    SET_REQ_VALUE_HEATER = 21
    SET_REQ_VALUE_HEATER_SW = 22
    SET_REQ_VALUE_LIGHT_LEVEL = 23
    SET_REQ_VALUE_VAR1 = 24
    SET_REQ_VALUE_VAR2 = 25
    SET_REQ_VALUE_VAR3 = 26
    SET_REQ_VALUE_VAR4 = 27
    SET_REQ_VALUE_VAR5 = 28
    SET_REQ_VALUE_UP = 29
    SET_REQ_VALUE_DOWN = 30
    SET_REQ_VALUE_STOP = 31
    SET_REQ_VALUE_IR_SEND = 32
    SET_REQ_VALUE_IR_RECEIVE = 33
    SET_REQ_VALUE_FLOW = 34
    SET_REQ_VALUE_VOLUME = 35
    SET_REQ_VALUE_LOCK_STATUS = 36
    SET_REQ_VALUE_DUST_LEVEL = 37
    SET_REQ_VALUE_VOLTAGE = 38
    SET_REQ_VALUE_CURRENT = 39

    # Internal message type
    INTERNAL_TYPE_BATTERY_LEVEL = 0
    INTERNAL_TYPE_TIME = 1
    INTERNAL_TYPE_VERSION = 2
    INTERNAL_TYPE_ID_REQUEST = 3
    INTERNAL_TYPE_ID_RESPONSE = 4
    INTERNAL_TYPE_INCLUSION_MODE = 5
    INTERNAL_TYPE_CONFIG = 6
    INTERNAL_TYPE_FIND_PARENT = 7
    INTERNAL_TYPE_FIND_PARENT_RESPONSE = 8
    INTERNAL_TYPE_LOG_MESSAGE = 9
    INTERNAL_TYPE_CHILDREN = 10
    INTERNAL_TYPE_SKETCH_NAME = 11
    INTERNAL_TYPE_SKETCH_VERSION = 12
    INTERNAL_TYPE_REBOOT = 13
    INTERNAL_TYPE_GATEWAY_READY = 14
    INTERNAL_TYPE_CONTROLLER_DISCOVERY = 15

    # Sensor type - presentation
    SENSOR_TYPE_DOOR = 0
    SENSOR_TYPE_MOTION = 1
    SENSOR_TYPE_SMOKE = 2
    SENSOR_TYPE_LIGHT = 3
    SENSOR_TYPE_DIMMER = 4
    SENSOR_TYPE_COVER = 5
    SENSOR_TYPE_TEMP = 6
    SENSOR_TYPE_HUM = 7
    SENSOR_TYPE_BARO = 8
    SENSOR_TYPE_WIND = 9
    SENSOR_TYPE_RAIN = 10
    SENSOR_TYPE_UV = 11
    SENSOR_TYPE_WEIGHT = 12
    SENSOR_TYPE_POWER = 13
    SENSOR_TYPE_HEATER = 14
    SENSOR_TYPE_DISTANCE = 15
    SENSOR_TYPE_LIGHT_LEVEL = 16
    SENSOR_TYPE_ARDUINO_NODE = 17
    SENSOR_TYPE_ARDUINO_REPEATER_NODE = 18
    SENSOR_TYPE_LOCK = 19
    SENSOR_TYPE_IR = 20
    SENSOR_TYPE_WATER = 21
    SENSOR_TYPE_AIR_QUALITY = 22
    SENSOR_TYPE_CUSTOM = 23
    SENSOR_TYPE_DUST = 24
    SENSOR_TYPE_SCENE_CONTROLLER = 25

    # Type of Stream
    STREAM_TYPE_FIRMWARE_CONFIG_REQUEST = 0
    STREAM_TYPE_FIRMWARE_CONFIG_RESPONSE = 1
    STREAM_TYPE_FIRMWARE_REQUEST = 2
    STREAM_TYPE_FIRMWARE_RESPONSE = 3
    STREAM_TYPE_SOUND = 4
    STREAM_TYPE_IMAGE = 5

    # Payload type
    PAYLOAD_STRING = 0
    PAYLOAD_BYTE = 1
    PAYLOAD_INT16 = 2
    PAYLOAD_UINT16 = 3
    PAYLOAD_LONG32 = 4
    PAYLOAD_ULONG32 = 5
    PAYLOAD_CUSTOM = 6
    PAYLOAD_FLOAT32 = 7

    def __init__(self, node_id, child_sensor_id, message_type, ack, sub_type, payload):
        self.node_id = int(node_id)
        self.child_sensor_id = int(child_sensor_id)
        self.message_type = int(message_type)
        self.ack = int(ack)
        self.sub_type = int(sub_type)
        self.payload = payload.decode()

    def to_serial_msg(self):
        """
        Construct the serial message

        :return: string with serial message
        """
        return bytes('{node_id};{child_sensor_id};{message_type};{ack};{sub_type};{payload}\n'.format(**self.__dict__),
                     'utf-8')

    @staticmethod
    def from_serial_msg(message):
        """
        Parses the serial message

        :param message: string with serial message 'node-id;child-sensor-id;message-type;ack;sub-type;payload\n'
        :return: MySensorsMsg object
        """
        logger.debug("Parsing MySensors message '{0}'".format(message.strip()))
        return MySensorsMsg(*message.strip().split(b';'))

    @staticmethod
    def msg_type_to_str(msg_type):
        string = {MySensorsMsg.MSG_TYPE_INTERNAL: 'Internal',
                  MySensorsMsg.MSG_TYPE_PRESENTATION: 'Presentation',
                  MySensorsMsg.MSG_TYPE_REQ: 'Req',
                  MySensorsMsg.MSG_TYPE_SET: 'Set',
                  MySensorsMsg.MSG_TYPE_STREAM: 'Stream'}

        try:
            return string[msg_type]
        except KeyError:
            return 'Bogus type'

    @staticmethod
    def msg_internal_type_to_str(msg_type):
        string = {MySensorsMsg.INTERNAL_TYPE_BATTERY_LEVEL: 'Battery level',
                  MySensorsMsg.INTERNAL_TYPE_TIME: 'Time',
                  MySensorsMsg.INTERNAL_TYPE_VERSION: 'Version',
                  MySensorsMsg.INTERNAL_TYPE_ID_REQUEST: 'ID Request',
                  MySensorsMsg.INTERNAL_TYPE_ID_RESPONSE: 'ID Response',
                  MySensorsMsg.INTERNAL_TYPE_INCLUSION_MODE: 'Inclusion mode',
                  MySensorsMsg.INTERNAL_TYPE_CONFIG: 'Config',
                  MySensorsMsg.INTERNAL_TYPE_FIND_PARENT: 'Find parent',
                  MySensorsMsg.INTERNAL_TYPE_FIND_PARENT_RESPONSE: 'Find parent response',
                  MySensorsMsg.INTERNAL_TYPE_LOG_MESSAGE: 'Log message',
                  MySensorsMsg.INTERNAL_TYPE_CHILDREN: 'Children',
                  MySensorsMsg.INTERNAL_TYPE_SKETCH_NAME: 'Sketch name',
                  MySensorsMsg.INTERNAL_TYPE_SKETCH_VERSION: 'Sketch version',
                  MySensorsMsg.INTERNAL_TYPE_REBOOT: 'Reboot',
                  MySensorsMsg.INTERNAL_TYPE_GATEWAY_READY: 'Gateway ready',
                  MySensorsMsg.INTERNAL_TYPE_CONTROLLER_DISCOVERY: 'Controller Discovery'}

        try:
            return string[msg_type]
        except KeyError:
            return 'Bogus type'
