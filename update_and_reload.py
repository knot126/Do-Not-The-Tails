#!/usr/bin/env python3
from os import system as cmd

assert(cmd("git pull") == 0 and cmd("systemctl --user restart TailsBot") == 0)
