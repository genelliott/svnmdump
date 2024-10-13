// Copyright 2018 Genesis Elliott <genesis DOT elliott AT gmail DOT com>. All rights reserved.
// Use of this source code is governed by a BSD-style
// license that can be found in the LICENSE file.

// Dumps multiple SVN Repos at the same time.

package main

import (
	"bufio"
	"bytes"
	"fmt"
	"github.com/BurntSushi/toml"
	"io/ioutil"
	"log"
	"os"
	"os/exec"
	"regexp"
	"runtime"
	"sync"
	"time"
)

// repo_conf_dir="/data/svnmdump/repos"
// log="/data/svnmdump/log/svnmdump.log"
// dump_store="/data/svndump/dump_store"
// workers=5
// worker_script="./svnmdump_worker.py"
type config struct {
	Repos        string `toml:"repos"`
	Log          string `toml:"log"`
	DumpStore    string `toml:"dump_store"`
	Workers      int    `toml:"workers"`
	WorkerScript string `toml:"worker_script"`
}

type repoConfig struct {
	Root     string `toml:"root"`
	Dump     string `toml:"dump"`
	ConfPath string
}

var (
	conf       config // Our programs main config data
	method     string // FULL (Full dump) or INC (Incremental)
	configPath string
	wg         sync.WaitGroup
	logger     *log.Logger     // We'll use this to log everything
	chWork     chan repoConfig // Our main channel where our workers will receive work
	version    string
)

func main() {
	version = "0.1"

	if len(os.Args) != 3 {
		usage()
		os.Exit(0)
	}

	if os.Args[1] == "--full" {
		method = "--full"
	} else if os.Args[1] == "--inc" {
		method = "--inc"
	} else {
		usage()
		os.Exit(1)
	}

	configPath = os.Args[2]
	// Let's make sure our main configuration file exists
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		log.Fatalf("%s does not exist!\n", configPath)
	}

	// Let's read the main config file to our conf variable
	if _, err := toml.DecodeFile(configPath, &conf); err != nil {
		log.Fatal(err)
	}

	// Let's use the same amount of CPUs as there are workers
	runtime.GOMAXPROCS(conf.Workers)

	// Initialise our channel, we'll use this to assign work to workers
	chWork = make(chan repoConfig, conf.Workers)

	// Run our workers as go routines and let them wait for work to be sent via the channel
	for count := 0; count < conf.Workers; count++ {
		// Add our worker to the wait group
		wg.Add(1)
		go worker(count + 1)
	}

	// Check for the existence of our dump store, this is where we'll store the svn dump files per repo
	if pathStat, err := os.Stat(conf.DumpStore); err != nil {
		log.Fatal(err)
	} else {
		if pathStat.IsDir() == false {
			log.Fatalf("%s is not a directory\n", conf.DumpStore)
		}
	}

	// open up a file handle for our log file
	fd, err := os.OpenFile(conf.Log, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0644)

	if err != nil {
		log.Fatal(err)
	}

	defer fd.Close()

	// we'll use the cool log module for our logging, so it has date stamping
	logger = log.New(fd, "", log.LstdFlags)

	logger.Printf(":: Starting SVN Multi Dump Tool v%s ::", version)
	startTime := time.Now()

	// Terminate the program if our worker script does not exist
	if _, err := os.Stat(conf.WorkerScript); os.IsNotExist(err) {
		logger.Fatalf("!! %s does not exist!\n", conf.WorkerScript)
	}

	// Check for the existence of our repos config directory
	if pathStat, err := os.Stat(conf.Repos); err != nil {
		logger.Fatal(err)
	} else {
		if pathStat.IsDir() == false {
			logger.Fatalf("%s is not a directory\n", conf.Repos)
		}
	}

	// Read the configurations per repo
	files, err := ioutil.ReadDir(conf.Repos)
	if err != nil {
		logger.Fatal(err)
	}

	// We'll use this regex to make sure we filter only files that has the extension svnmdump.toml
	rgx, err := regexp.Compile(`\.svnmdump\.toml$`)
	if err != nil {
		logger.Fatal(err)
	}

	// Let's read the repo configs one by one and pass the details to the workers via a channel
	for _, file := range files {
		if rgx.MatchString(file.Name()) && !file.IsDir() {

			repoConfPath := fmt.Sprintf("%s/%s", conf.Repos, file.Name())
			repoConf := repoConfig{}

			if _, err := toml.DecodeFile(repoConfPath, &repoConf); err != nil {
				logger.Fatal(err)
			}

			// Send our worker some work
			repoConf.ConfPath = repoConfPath
			chWork <- repoConf
		}

	}

	close(chWork)
	wg.Wait()

	logger.Printf(":: All Done - runtime %v ::\n", time.Since(startTime))
}

// usage Displays the program usage
func usage() {
	fmt.Printf("svnmdump v%s\nusage: %s --full|--inc /path/to/svnmdump.toml\n", version, os.Args[0])
}

// worker Waits for work to be delivered via the channel and then spawns
// the worker script, passing it the dump method, path of the svn repo and path
// of the dump store
func worker(id int) {
	// Get our work from the chWork channel
	for work := range chWork {
		logger.Printf(">> Worker %d is working on \"%s\"\n", id, work.ConfPath)

		// Execute our worker script
		cmd := exec.Command(conf.WorkerScript, method, work.Root, work.Dump)

		// Create a buffer for our worker scripts stdout/stderr output
		// we'll use it to the output to our log file
		cmdErr := &bytes.Buffer{}
		cmdOut := &bytes.Buffer{}

		cmd.Stderr = cmdErr
		cmd.Stdout = cmdOut

		// Run the worker script
		dumpStart := time.Now()
		err := cmd.Run()

		// Log everything that our worker script printed on stdout before the stderr output
		scanner := bufio.NewScanner(cmdOut)
		for scanner.Scan() {
			logger.Printf(">> Worker %d: %s\n", id, scanner.Text())
		}

		if err != nil {
			logger.Printf("!! Worker %d: Error Encountered\n", id)
			scanner := bufio.NewScanner(cmdErr)
			for scanner.Scan() {
				logger.Printf("!! Worker %d: %s\n", id, scanner.Text())
			}
		}

		logger.Printf(">> Worker %d has finished with \"%s\" - runtime %v\n", id, work.ConfPath, time.Since(dumpStart))

	}

	logger.Printf(">> Worker %d has exited\n", id)
	wg.Done()
}
