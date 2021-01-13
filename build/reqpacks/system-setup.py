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
        self.setup_pip()
        self.pip_install("wheel virtualenv")
        self.pip_install("setuptools --upgrade")

        self.pip_install("-r %s/paella/requirements.txt" % READIES)
        self.install("git zip unzip")

    def debian_compat(self):
        self.install("build-essential")
        self.install("python3-psutil")
        self.install("libsqlite3-dev")
        self.install("unixodbc-dev")

    def redhat_compat(self):
        self.run("%s/bin/enable-utf8" % READIES)

        self.group_install("'Development Tools'")
        self.install("redhat-lsb-core")
        self.install("libsqlite3x-devel")
        self.install("gcc")
        self.install("gcc-c++")
        self.install("unixODBC-devel")

    def fedora(self):
        self.group_install("'Development Tools'")

    def macos(self):
        self.install_gnu_utils()

    def common_last(self):
        self.pip_install("git+https://github.com/RedisGears/gears-cli.git")

#----------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description='Set up system for build.')
parser.add_argument('-n', '--nop', action="store_true", help='no operation')
args = parser.parse_args()

ReqPacksSetup(nop=args.nop).setup()
