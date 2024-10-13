#!/usr/bin/python

# Copyright 2018 Genesis Elliott <genesis DOT elliott AT gmail DOT com>. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

# Worker script for svnmdump tool, this script does the actual dumping of the repo.

import os
import re
import sys
import time
import random

def usage():
  sys.stderr.write("svnmdump_worker.py v0.1\nusage: {0} --full|--inc /path/to/svn/repo /path/to/backup/dir\n".format(sys.argv[0]))

if len(sys.argv) != 4:
  usage()
  sys.exit(1)

# We only allow --full or --inc to be the first argument
# if not splash our usage
if sys.argv[1] == "--full":
  method = "FULL"
elif sys.argv[1] == "--inc":
  method = "INCREMENTAL"
else:
  usage()
  sys.exit(1)

# Our 2nd argument is the svn path
# 3rd argument is the path to where our dumps will live
repoPath = sys.argv[2]
dumpPath = sys.argv[3]

# Display our usage and exit if we weren't provided with repository path and dump path
if not repoPath or not dumpPath:
  usage()
  sys.exit(1)

# state.full records the youngest revision at the time of full dump
# state.inc records the range  revisions that were dumped during incremental dump
stateFileFull = "{0}/state.full".format(dumpPath)
stateFileInc = "{0}/state.inc".format(dumpPath)

# the location of the lib directory so we can import the svnlib below
libPath = "{0}/lib".format(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(libPath)

import svnlib

# If the repository directory does not exist, then exit with error
if not os.path.isdir(repoPath):
  sys.stderr.write("Repo {0} does not exist".format(repoPath))
  sys.exit(2)

# Create the dump directory if not already exist
if not os.path.isdir(dumpPath):
  print("Creating \"{0}\"".format(dumpPath))
  os.makedirs(dumpPath)

# Let's get the youngest revision of the repo at the time of the scripts execution
youngestRev = svnlib.getYoungest(repoPath)
# Used by the incremental dump, will be set to the value that's in state.full, which indicates the revision of the repo at the time of FULL dump
youngestFullRev = None
# Used only on Full dump and always set to 0
oldestRev = 0

if method == "INCREMENTAL":
  # If we're in INCREMENTAL mode but the state.full file does not exist
  # Then let's force a FULL dump
  if not os.path.isfile(stateFileFull):
    print("No record of FULL dump, switching method from INCREMENTAL to FULL")
    method = "FULL"
  else:
    # If the state.full exist, read the revision and store it on
    # youngestFullRev
    with open(stateFileFull) as fd:
      for line in fd.readlines():
        line = line.strip()
        if line and re.search("^\\d+$", line):
          youngestFullRev = int(line)
          break

    # If youngestFullRev was not updated, this means there are no records of FULL dump
    # Force a FULL  dump
    if youngestFullRev == None:
      print("No record of FULL dump on {0}, switching method from INCREMENTAL to FULL".format(stateFileFull))
      method = "FULL"

# This will contain our svnadmin command 
cmd = ""

# Location of our FULL.dump and INC.dump respectively
fullDumpPath = "{0}/FULL.dump".format(dumpPath)
incDumpPath = "{0}/INC.dump".format(dumpPath)

if method == "FULL":
  # If we're dumping in FULL mode, here's our command
  # Note that we redirect the output of svnadmin dump to our FULL.dump
  cmd = "svnadmin dump -q -r {0}:{1} {2} > {3}".format(oldestRev, youngestRev, repoPath, fullDumpPath)
  print("Performing FULL dump of {0} to {1} from Revision 0 to {2}".format(repoPath, fullDumpPath, youngestRev))
else:
  # INCREMENTAL mode, let's compare the youngest revision for our repo, 
  # with that of the revision for our last FULL dump
  # If they're the same then exit
  if youngestFullRev == youngestRev:
    print("Latest FULL Dump Revision is already same as Youngest Revision {0}, nothing to increment".format(youngestFullRev))
    sys.exit(0)
  else:
    # Our command for dumping INCREMENTAL mode
    cmd = "svnadmin dump -q --incremental -r {0}:{1} {2} > {3}".format(youngestFullRev+1, youngestRev, repoPath, incDumpPath)
    print("Performing INCREMENTAL dump of {0} to {1} from Revision {2} to {3}".format(repoPath, incDumpPath, youngestFullRev+1, youngestRev))

# Let's run the commands
(status, stdout, stderr) = svnlib.run(cmd, True)
# Print any standard output from svnadmin
print(stdout)

# If we had errors, print them then exit with error code
if status != 0:
  sys.stderr.write(stderr)
  sys.exit(3)

if method == "FULL":
  # If we just did a FULL dump
  # Update our state.full file
  open(stateFileFull, 'w').write("{0}".format(youngestRev))

  # If there are any INC.full and state.inc then remove them as we 
  # don't need them anymore since we have the latest FULL dump
  if os.path.isfile(incDumpPath):
    print("Removing previous INCREMENTAL {0}".format(incDumpPath))
    os.unlink(incDumpPath)
  if os.path.isfile(stateFileInc):
    print("Removing INCREMENTAL state file {0}".format(stateFileInc))
    os.unlink(stateFileInc)
else:
  # Else, we just did an INCREMENTAL dump
  # let's update  our state.inc
  open(stateFileInc, 'w').write("{0}-{1}".format(youngestFullRev+1, youngestRev))