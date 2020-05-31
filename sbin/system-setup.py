#!/usr/bin/env python3

import sys
import os
from subprocess import Popen, PIPE
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../deps/readies"))
import paella

#----------------------------------------------------------------------------------------------

class RGSyncSetup(paella.Setup):
    def __init__(self, nop=False):
        paella.Setup.__init__(self, nop)

    def common_first(self):
        self.install_downloaders()
        self.setup_pip()
        self.pip3_install("wheel virtualenv")
        self.pip3_install("setuptools --upgrade")
        
        self.pip3_install("-r deps/readies/paella/requirements.txt")
        self.install("git zip unzip")

    def debian_compat(self):
        self.install("python3-psutil")

    def redhat_compat(self):
        self.install("redhat-lsb-core")

        # enable en_US.utf8 locale
        self.run("sed -i 's/^\(override_install_langs=\)/# \1/' /etc/yum.conf")
        self.run("yum reinstall -y glibc-common")

    def fedora(self):
        pass

    def macosx(self):
        self.install_gnu_utils()

    def common_last(self):
        self.pip3_install("git+https://github.com/RedisGears/gears-cli.git@requirement_import_export")

#----------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description='Set up system for build.')
parser.add_argument('-n', '--nop', action="store_true", help='no operation')
args = parser.parse_args()

RGSyncSetup(nop=args.nop).setup()
