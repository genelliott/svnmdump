# svnmdump
## **Warning and License Notice**

**Warning:**

The `svnmdump` tool and its associated `svnmdump_worker.py` script are designed for specific use cases and may require modifications or adjustments to suit your particular environment. **Use these tools at your own risk.** The author is not responsible for any damages or losses that may result from the use or misuse of these tools.

**License:**

Both `svnmdump` and `svnmdump_worker.py` are licensed under the BSD 3-Clause License. Please read the included LICENSE file for more details.

**Important Notes:**

* Ensure you have the necessary permissions and access to the Subversion repositories you intend to dump.
* Review and customize the configuration files (`svnmdump.toml` and per-repo `.svnmdump.toml` files) to match your specific requirements.
* Always test the tools in a development or staging environment before applying them to production systems.
* Consider using version control for your configuration files to track changes and facilitate backups.
* Regularly update the `svnlib` module and the `svnmdump` tool to ensure compatibility with the latest versions of Subversion.

By following these guidelines and carefully reviewing the code and documentation, you can use the `svnmdump` tool effectively and safely.


Dumping multiple SVN repos at the same time.  This tool can be configured to increase and decrease the number of concurrent dumps that are running at the same time.  Making sure that we don't exhaust all our CPUs just for dumping svn repositories.  

This also means that the repositories to be dumped are queued.  If for example we have 50 fairly large svn repositories, and svnmdump is configured to run with 5 concurrent dumps at the same time.  When we start svnmdump, it will dump the first 5 repositories, if 1 (or any number) dump finishes then another will take over, maintaining 5 concurrent dumps until all repositories have finished dumping.

svnmdump can also be used to dump svn repositories in FULL or INCREMENTAL mode.  Useful for dumping FULL on Weekends (Saturday or Sunday) when there's less user activity and INCREMENTAL on the weekdays.

## Prerequisite

- Operating System - Linux, tested on Ubuntu and CentOS.
- Google Go - Requires version at least 1.10.1 or later, with GOPATH configured.  [See Install Instruction Here](https://golang.org/doc/install).
- Subversion - Needs svnadmin for generating svn repo dumps and svnlook for querying svn repos youngest revision.  Currently tested on version 1.9.7.
- Python - Tested on 2.7.15rc1.

## Installation

First create a user for svnmdump.  Make sure this user has ***Read-Only*** access to the svn repos that needs to be dumped.  

    useradd -c "SVN Dump User" svnmdump

Create the directory that will house our tool.

    mkdir -p /data

Give our svnmdump user full access to it.

    chown -Rv svnmdump:svnmdump /data
      changed ownership of '/data' from root:root to svnmdump:svnmdump

Become svnmdump.

    sudo su - svnmdump

Clone svnmdump from gitlab.

    cd /data
    git clone https://gitlab.com/genesis.elliott/svnmdump.git/

## Compiling

Download the toml library.

    go get 

Compile.
    
    cd /data/svnmdump
    go build svnmdump.go 

## Main Configuration

Create the directory for storing the dump files, logs and configuration for the individual svn repositories.  
  
    mkdir /data/{dump_store,log,repos}

Edit the main configuration and adjust the values to your preference.

    vim /data/svnmdump/svnmdump.toml

      repos="/data/svnmdump/repos"
      log="/data/svnmdump/log/svnmdump.log"
      dump_store="/data/svnmdump/dump_store"
      workers=3
      worker_script="/data/svnmdump/svnmdump_worker.py"

- ***repos***, Where we'll store the configuration of each individual svn repos.
- ***log***, Our main log file.
- ***dump_store***, Where svnmdump will store all the dump files for each svn repo.
- ***workers***, How many workers are gonna be dumping at the same time.
- ***worker_script***, The path to our svnmdump_worker.py.

Note that string values has to be double quoted.

## Configuration for our SVN Repos

We create a configuration for every svn repository that needs to be dumped.  As an example, our svn repository named ***repo01***, which is located at ***/svn/repo01***.  We want this dumped to ***/data/svnmdump/dump_store/repo01*** regularly.  Our configuration for this repo will be at ***/data/svnmdump/repos/repo01.svnmdump.toml***.  And contains the following:

    root="/svn/repo01"
    dump="/data/svnmdump/dump_store/repo01"

## Running our svnmdump tool
### FULL Dump

    ./svnmdump --full svnmdump.toml

This will create a full dump file /data/svnmdump/dump_store/repo01/FULL.dump and will update the state file /data/svnmdump/dump_store/repo01/state.full to the value of the youngest revision of the repo that was just dumped.

This will also remove the incremental dump INC.dump and state.inc file if they exist.

### INCREMENTAL Dump

    ./svnmdump --inc svnmdump.toml

This will read the /data/svnmdump/dump_store/repo01/state.full for the revision of the last full dump, and will create an incremental dump from the next revision of the last full dump to the youngest revision of the repo.

This will create a dump file /data/svnmdump/dump_store/repo01/INC.dump and update the /data/svnmdump/dump_store/repo01/state.inc with the range of revision that was dumped.  For example, say our last dumped revision from state.full was 100, and our repos youngest revision is 300.  svnmdump will dump the revisions 101 to 300 and will update the state.inc with the values:

    101-300

## Test Cases

Here are some of the behaviours of svnmdump.

**repo directory doesn't exist:**

2018/10/07 22:14:53 !! Worker 1: Error Encountered

2018/10/07 22:14:53 !! Worker 1: Repo /svn/repo01 does not exist

**repo directory is empty or wrong format:**

2018/10/07 22:16:45 !! Worker 1: Error Encountered

2018/10/07 22:16:45 !! Worker 1: svnlook: E000002: Can't open file '/svn/repo01/format': No such file or directory

**repo dump directory doesn't exist:**

2018/10/07 22:19:09 >> Worker 1: Creating "/data/svnmdump/dump_store/repo01"

2018/10/07 22:19:09 >> Worker 1: No record of FULL dump, switching method from INCREMENTAL to FULL

2018/10/07 22:19:09 >> Worker 1: Performing FULL dump of /svn/repo01 to /data/svnmdump/dump_store/repo01/FULL.dump from Revision 0 to 7471

**incremental mode but state.full doesn't exist:**

2018/10/07 22:21:31 >> Worker 1: No record of FULL dump, switching method from INCREMENTAL to FULL

2018/10/07 22:21:31 >> Worker 1: Performing FULL dump of /svn/repo01 to /data/svnmdump/dump_store/repo01/FULL.dump from Revision 0 to 7471

**incremental mode, state.full exists but is empty:**

2018/10/07 22:22:37 >> Worker 1: No record of FULL dump on /data/svnmdump/dump_store/repo01/state.full, switching method from INCREMENTAL to FULL

2018/10/07 22:22:37 >> Worker 1: Performing FULL dump of /svn/repo01 to /data/svnmdump/dump_store/repo01/FULL.dump from Revision 0 to 7471

**incremental mode, repos youngest rev is the same as in the state.full:**

2018/10/07 22:23:28 >> Worker 1: Latest FULL Dump Revision is already same as Youngest Revision 7471, nothing to increment

**incremental mode, rev in state.full is greater than repos youngest rev:**

2018/10/07 22:24:08 !! Worker 1: Error Encountered

2018/10/07 22:24:08 !! Worker 1: svnadmin: E205000: Try 'svnadmin help' for more info

2018/10/07 22:24:08 !! Worker 1: svnadmin: E205000: Revisions must not be greater than the youngest revision (7471)

**incremental mode, repos youngest rev is greater than in the state.full:**

2018/10/07 22:28:52 >> Worker 1: Performing INCREMENTAL dump of /svn/repo01 to /data/svnmdump/dump_store/repo01/INC.dump from Revision 741 to 7471

**full mode, state.full exist, state.inc exist, INC.dump exist, FULL.dump exist:**

2018/10/07 22:30:48 >> Worker 1: Performing FULL dump of /svn/repo01 to /data/svnmdump/dump_store/repo01/FULL.dump from Revision 0 to 7471

2018/10/07 22:30:48 >> Worker 1: 

2018/10/07 22:30:48 >> Worker 1: Removing previous INCREMENTAL /data/svnmdump/dump_store/repo01/INC.dump

2018/10/07 22:30:48 >> Worker 1: Removing INCREMENTAL state file /data/svnmdump/dump_store/repo01/state.inc
