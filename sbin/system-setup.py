#!/usr/bin/env python3

import sys
import os
import argparse

HERE = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
READIES = os.path.join(ROOT, "deps/readies")
sys.path.insert(0, READIES)
import paella

#----------------------------------------------------------------------------------------------

class RGSyncSetup(paella.Setup):
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
        self.install("python3-psutil")
        if self.osnick == 'bionic':
            self.install("mysql-server")

    def redhat_compat(self):
        self.install("redhat-lsb-core")
        self.run("%s/bin/enable-utf8" % READIES)
        self.run("yum reinstall -y glibc-common")

    def fedora(self):
        pass

    def macosx(self):
        self.install_gnu_utils()

    def common_last(self):
        self.pip_install("--no-cache-dir git+https://github.com/Grokzen/redis-py-cluster.git@master")
        self.pip_install("--no-cache-dir git+https://github.com/RedisLabsModules/RLTest.git@master")
        self.pip_install("git+https://github.com/RedisGears/gears-cli.git")
        self.pip_install("-r %s/requirements.txt" % ROOT)
        self.pip_install("PyMySQL")

#----------------------------------------------------------------------------------------------

parser = argparse.ArgumentParser(description='Set up system for build.')
parser.add_argument('-n', '--nop', action="store_true", help='no operation')
args = parser.parse_args()

RGSyncSetup(nop=args.nop).setup()
