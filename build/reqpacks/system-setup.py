#!/usr/bin/env python3

import sys
import os
import argparse

HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "../.."))
READIES = os.path.join(ROOT, "deps/readies")
sys.path.insert(0, READIES)
import paella

#----------------------------------------------------------------------------------------------

class ReqPacksSetup(paella.Setup):
    def __init__(self, nop=False):
        paella.Setup.__init__(self, nop)

    def common_first(self):
        self.install_downloaders()
        self.pip_install("wheel virtualenv")
        self.pip_install("setuptools --upgrade")

        self.install("git zip unzip libxml2")
        self.run(f"{READIES}/bin/enable-utf8")

    def debian_compat(self):
        self.run(f"{READIES}/bin/getgcc")
        self.install("libsqlite3-dev")
        self.install("unixodbc-dev")

    def redhat_compat(self):
        self.run(f"{READIES}/bin/getgcc")
        self.install("redhat-lsb-core")
        if self.os_version[0] >= 8 and self.dist in ['centos', 'ol']:
            self.install("sqlite-devel")
        else:
            self.install("libsqlite3x-devel")
        self.install("unixODBC-devel")

    def fedora(self):
        self.run(f"{READIES}/bin/getgcc")

    def macos(self):
        self.install_gnu_utils()

    def common_last(self):
        self.pip_install("gears-cli")

#----------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description='Set up system for build.')
parser.add_argument('-n', '--nop', action="store_true", help='no operation')
args = parser.parse_args()

ReqPacksSetup(nop=args.nop).setup()
