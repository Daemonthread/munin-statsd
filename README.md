munin-statsd
============

A small tool for running munin plugins on a server and sending the data to a statsd server via UDP.

Output from help:

Munin-statsd, send your munin plugin data to statsd

optional arguments:
  -h, --help            show this help message and exit
  -s STATSD, --statsd STATSD
                        Statsd host and port, for example:
                        statsd.example.org:9001
  -v {1,2,3}, --verbose {1,2,3}
                        Verbosity level. 1=Quiet(default), 2=Debug, 3=Error.
  -m {c,g,h,m}, --metric {c,g,h,m}
                        Metric type. c=Counter, g=Gauge, h=Histogram, m=Meter.
  -p PREFIX, --prefix PREFIX
                        The prefix you'd like to send to statsd. Default is
                        servers.
