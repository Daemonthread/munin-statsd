#!/usr/bin/env python
#
#   Copyright Toby Sears 2013
#  
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
"""
A script to be run periodically on a server, runs all configured munin plugins and returns 
the data to a remote statsd host via UDP.

Heavily influenced by https://github.com/jforman/munin-graphite/blob/master/m2g-poller.py 
but without the multithreading.
"""

import argparse
import logging
import socket
import sys

logging_format = "%(asctime)s:%(levelname)s:%(message)s"

class MuninStatsd():
    def __init__(self, hostname="localhost", port=4949, args=None):
        """Initialize the class."""
        self.hostname = hostname
        self.port = port
        self.args = args
        try:
            self.statsd_host, self.statsd_port = self.args.statsd.split(":")
            self.statsd_ip = socket.gethostbyname(self.statsd_host)
        except:
            print "ERROR: No host:port supplied for statsd, use \"munin-statsd -h\" to see the help, exiting."
            sys.exit(1)

    def _readline(self):
        """Read over each line, stripping leading and trailing characters."""
        return self._conn.readline().strip()

    def _iterline(self):
        """Iterate over Munin output."""
        while True:
            current_line = self._readline()
            logging.debug("Iterating over line: %s", current_line)
            if not current_line:
                break
            if current_line.startswith("#"):
                continue
            if current_line == ".":
                break
            yield current_line

    def _format_hostname(self, hostname):
        """Replace dots in a hostname with underscores."""
        hostname = hostname.replace(".", "_")
        return hostname

    def go(self):
        """Starts off the process."""
        self.open_connection()
        for plugin in self.list_plugins():
            self.get_data(plugin)

    def open_connection(self):
        """Open a connection to the munin host."""
        logging.debug("Creating socket connection to host: {0}, port: {1}".format(
                      self.hostname, self.port))
        try:
            self._sock = socket.create_connection((self.hostname, self.port),10)
        except socket.error:
            logging.exception("Unable to connect to Munin host {0}, port: {1}".format(
                             self.hostname, self.port))
            sys.exit(1)

        self._conn = self._sock.makefile()
        self.hello_string = self._readline()

    def close_connection(self):
        """Close the connection to the munin host."""
        self._sock.close()

    def list_plugins(self):
        """Return a list of all configured Munin plugins."""
        self._sock.sendall("list\n")
        plugin_list = self._readline().split(" ")
        return plugin_list

    def get_data(self, plugin):
        """Get the data from the plugin."""
        logging.debug("Getting data for plugin: {0}".format(plugin))
        self._sock.sendall("fetch {0}\n".format(plugin))
        for current_line in self._iterline():
            logging.debug("Processing data: {0}".format(current_line))
            data = self.process_data(plugin, current_line)

    def process_data(self, plugin, raw_data):
        """Create the message to put in the UDP packet."""
        prefix = self.args.prefix
        metric_type = self.args.metric
        hostname = self._format_hostname(socket.gethostname())
        plugin = plugin.replace(".", "_")
        try:
            key_name, key_value = raw_data.split(" ")
            key_name = key_name.split(".")[0]
            data = "{0}.{1}.{2}.{3}-1m:{4}|{5}".format(prefix,
                                                 hostname,
                                                 plugin,
                                                 key_name,
                                                 key_value,
                                                 metric_type)
            # If everything is successfull then send off the packet.
            self.send_data(data)

        except:
            logging.exception("Unpacking of raw_data for {0} failed, skipping.".format(raw_data))
            pass

    def send_data(self,data):
        """Send UDP packet to statsd."""
        try:
            logging.debug("Sending: {0}, to host: {1}, port: {2}".format(
                           data, self.statsd_ip, self.statsd_port))
            sock = socket.socket(socket.AF_INET,
                                 socket.SOCK_DGRAM)
            sock.sendto(data, (self.statsd_ip, int(self.statsd_port)))
        except socket.error:
            logging.exception("Error sending UDP packet to: {0}:{1}".format(
                               self.statsd_ip, self.statsd_port))
            sys.exit(1)

def parse_args():
    """Command line arguments are parsed here."""
    parser = argparse.ArgumentParser(description="Munin-statsd, send your munin plugin data to statsd.")
    parser.add_argument("-s","--statsd",
                        action="store",
                        help="Statsd host and port, for example: statsd.example.org:9001")
    parser.add_argument("-v","--verbose",
                        choices=[1,2,3],
                        default=1,
                        type=int,
                        help="Verbosity level. 1=Quiet(default), 2=Debug, 3=Error.")
    parser.add_argument("-m","--metric",
                        choices=["c","g","h","m"],
                        default="c",
                        help="Metric type. c=Counter(default), g=Gauge, h=Histogram, m=Meter.")
    parser.add_argument("-p","--prefix",
                        default="servers",
                        help="The prefix you'd like to send to statsd. Default is servers.")
    args = parser.parse_args()
    return args

def main():
    args = parse_args()
    if args.verbose == 2:
        logging_level = logging.DEBUG
    elif args.verbose == 3:
        logging_level = logging.ERROR
    else:
        logging_level = logging.CRITICAL

    logging.basicConfig(format=logging_format, 
                        level=logging_level)
    ms = MuninStatsd(args=args)
    ms.go()

if __name__ == '__main__':
    main()