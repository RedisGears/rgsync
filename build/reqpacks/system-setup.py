#!/usr/bin/env python3

import sys
import os
from subprocess import Popen, PIPE
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../deps/readies"))
import paella

#----------------------------------------------------------------------------------------------

class ReqPacksSetup(paella.Setup):
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
        self.install("build-essential")
        self.install("python3-psutil")
        self.install("libsqlite3-dev")

    def redhat_compat(self):
        # enable en_US.utf8 locale
        self.run("sed -i 's/^\(override_install_langs=\)/# \1/' /etc/yum.conf")
        self.run("yum reinstall -y glibc-common")
        
        self.group_install("'Development Tools'")
        self.install("redhat-lsb-core")
        self.install("libsqlite3x-devel")

    def fedora(self):
        self.group_install("'Development Tools'")

    def macosx(self):
        p = Popen('xcode-select -p', stdout=PIPE, close_fds=True, shell=True)
        out, _ = p.communicate()
        if out.splitlines() == []:
            fatal("Xcode tools are not installed. Please run xcode-select --install.")
        self.install_gnu_utils()

    def common_last(self):
        self.pip3_install("git+https://github.com/RedisGears/gears-cli.git")

#----------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description='Set up system for build.')
parser.add_argument('-n', '--nop', action="store_true", help='no operation')
args = parser.parse_args()

ReqPacksSetup(nop=args.nop).setup()
