#!/usr/bin/env python2
#
# Interactive HAL Graph
#
# Copyright 2015 Jakob Flierl
#
# based on https://github.com/MachineryScience/Rockhopper/blob/master/MakeHALGraph.py
#
# this version differs to the above version in the following points:
#
# * it auto-refreshes the HAL data every five seconds
#
# * opens an interactive window (using a slightly modified version of xdot.py)
#
# * uses the pydot lib instead of the pygraphviz lib
#   (pygraphviz export seems to export dot files in a non-deterministic manner)

import os
import sys
import time
import math
import hal
import subprocess
import pydot

import gtk
import gtk.gdk

import xdot

import warnings

from machinekit import hal

class HALAnalyzer( object ):
    def __init__(self ):
        self.Graph = pydot.Dot(graph_type='digraph', name="Hal graph",
                               rankdir='LR',
                               splines='spline',
                               overlap='false',
                               start='regular',
                               #pad=".05",
                               #ranksep="0.75",
                               #nodesep="0.05"
        )

    def groupname(self, pinname):
        pstr = pinname.split('.')
        pin_group_name = pstr[0]
        try:
            if (len(pstr) > 2) and (int(pstr[1] > -1)):
                pin_group_name = pstr[0] + '.' + pstr[1]
        except Exception, err:
            pass
        return pin_group_name

    def todotname(self, name):
        return name.replace(".","_").replace("-", "_")
                
    def parse( self ):
        self.pin_group_dict = {}
        self.sig_dict = {}
        for pin in hal.pins():
            p = hal.Pin(pin)
            if p.signal:
                # if there is a signal listed on this pin, make sure
                # that signal is in our signal dictionary
                if ( p.signal.name in self.sig_dict ):
                    self.sig_dict[ p.signal.name ].append( p )
                else:
                    self.sig_dict[ p.signal.name ] = [ p ]
                    tmp = '<<table border="0" cellspacing="0">\n  <tr><td port="signame" border="1">' + p.signame + '</td></tr>' + \
                          '\n  <tr><td port="signame" border="0">(' + str(p.get()) + ')</td></tr></table>>'
                    self.Graph.add_node(pydot.Node(p.signame,
                                                   label=tmp,
                                                   shape='none'
                                                   ))
                n = self.groupname(p.name)
            
                if n in self.pin_group_dict:
                    self.pin_group_dict[ n ].append( p )
                else:
                    self.pin_group_dict[ n ] = [ p ]

        # Add all the pins into their sub-graphs
        for pin_g_name, pin_g_val_array in self.pin_group_dict.iteritems():
            tmp = '<<table border="0" cellspacing="0">\n  <tr><td port="title" border="1" bgcolor="#FFD75E">' + pin_g_name + '</td></tr>\n'
            for pin in pin_g_val_array:
                label =pin.name.split('.')[-1]
                name = self.todotname(pin.name.split('.')[-1])
                tmp += '  <tr><td port="'+ name + '" border="1">' + label + '</td></tr>\n'
            tmp += "</table>>"
            self.Graph.add_node(pydot.Node(self.todotname(pin_g_name), label=tmp, shape="none"))

        # Add all the edges to and from signals
        sigs = hal.signals()

        for sig in sigs:
            s = hal.Signal(sig)
            for pin in s.pins():
                n1 = self.todotname(self.groupname(pin.name))+":"+self.todotname(pin.name.split(".")[-1])
                n2 = s.name
                if (pin.name == s.writername):
                    self.Graph.add_edge(pydot.Edge( n1, n2, arrowhead="none", penwidth = 2, splines="ortho" ))
                else:
                    self.Graph.add_edge(pydot.Edge( n2, n1, penwidth = 2, splines="ortho" ))
        
    def write_svg( self, filename ):
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore",category=DeprecationWarning)
                output = self.Graph.create_svg(prog='dot' )
                f = open(filename, "w")
                f.write(output)
                f.close()
        except Exception, err:
            print err

    def to_string( self ):
        return self.Graph.to_string()

class HALGraphWindow(xdot.DotWindow):

    def __init__(self):
        xdot.DotWindow.__init__(self)
        self.base_title = "HAL Graph"
        self.set_filter("dot") # 'dot', 'neato', 'twopi', 'circo', 'fdp'
        self.widget.connect('clicked', self.on_url_clicked)
        self.analyzer = None
        self.reload()
        self.widget.zoom_to_fit()
        self.interval = 0

    def timer_interval(self, interval):
        self.interval = interval

    def enable_timer(self):
        if (self.interval > 0):
            self.timer = gtk.timeout_add(self.interval, self.timer_tick)
        
    def reload(self):
        self.analyzer = HALAnalyzer()
        self.analyzer.parse()
        self.set_dotcode(self.analyzer.to_string())
        self.textentry_changed(self.widget, self.textentry)

        self.queue_draw()

    def on_reload(self, action): # reload button
        self.reload()

    def on_url_clicked(self, widget, url, event):
        dialog = gtk.MessageDialog(
                parent = self, 
                buttons = gtk.BUTTONS_OK,
                message_format="%s clicked" % url)
        dialog.connect('response', lambda dialog, response: dialog.destroy())
        dialog.run()
        return True

    def timer_tick(self):
        gtk.timeout_remove(self.timer)
        self.reload()
        self.enable_timer()
        return True

def main():
    if len(sys.argv) == 1:
        w = HALGraphWindow()
        w.connect('destroy', gtk.main_quit)
        w.timer_interval(5000)
        w.enable_timer()
        gtk.main()
    elif len(sys.argv) == 2:
        a = HALAnalyzer()
        a.parse()
        a.write_svg(sys.argv[1])
    else:
        print "usage: hal-graph.py [hal-graph.svg]"

if __name__ == '__main__':
    main()
