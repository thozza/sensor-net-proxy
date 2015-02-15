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

import argparse


class ArgsParser(object):
    """ Class for processing data from commandline """

    def __init__(self, args=None):
        """ parse arguments """
        self.parser = argparse.ArgumentParser(description='Simple sensors network <-> controller proxy',
                                              formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        self.add_args()
        self.args = self.parser.parse_args(args)

    def add_args(self):
        self.parser.add_argument(
            '-v',
            '--verbose',
            default=False,
            action='store_true',
            help='Output is more verbose'
        )
        self.parser.add_argument(
            '-i',
            '--interface',
            default='lo',
            help='Name of the interface on which IPv4 address to listen'
        )
        self.parser.add_argument(
            '-p',
            '--port',
            default=5003,
            help='Port on which to listen'
        )
        self.parser.add_argument(
            '--no-dynamic-discovery',
            default=True,
            action='store_false',
            dest='dynamic_discovery',
            help='Whether to turn off dynamic discovery (means listening also on interface subnet broadcast address)'
        )

    def __getattr__(self, name):
        try:
            return getattr(self.args, name)
        except AttributeError:
            return object.__getattribute__(self, name)
