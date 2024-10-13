#!/usr/bin/python

# Copyright 2018 Genesis Elliott <genesis DOT elliott AT gmail DOT com>. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

# SVN related libraries for svnmdump.

import os
import re
import sys
import subprocess

def run(args, execShell=False):
  """Runs a command, returning the return code, standard output and standard error
  
  arguments:
  args - A list or string of the command to execute and it's arguments
  execShell - Execute the command using the underlying shell, useful when redirecting output of a command or piping

  returns:
  
  """

  proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=execShell)

  stdout, stderr = proc.communicate()

  status = proc.wait()

  return (status, stdout, stderr)

def getYoungest(path):
  (status, stdout, stderr) = run(['svnlook', 'youngest', path])

  if status != 0:
    sys.stderr.write(stderr)
    sys.exit(1)

  for line in stdout.split("\n"):
    line = line.strip()
    if line:
      return int(line)