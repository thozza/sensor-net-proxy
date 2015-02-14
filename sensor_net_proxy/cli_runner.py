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

import sys

from sensor_net_proxy.logger import logger
from sensor_net_proxy.exceptions import SensorNetProxyError
from sensor_net_proxy.args_parser import ArgsParser
from sensor_net_proxy.application import Application


class CliRunner(object):

    @staticmethod
    def run():
        try:
            args = ArgsParser(sys.argv[1:])
            app = Application(args)
            app.run()
        except KeyboardInterrupt:
            logger.info('\nInterrupted by user')
        except SensorNetProxyError as e:
            logger.error('\n{0}'.format(e))
            sys.exit(1)

        sys.exit(0)