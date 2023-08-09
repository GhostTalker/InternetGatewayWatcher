#!/usr/bin/env /srv/PyVenv/igw/bin/python3
#
# Internet Gateway Watcher (IGW)
# Script to restart Unifi Switch Port if internet is not responsable
#
__author__ = "GhostTalker"
__copyright__ = "Copyright 2023, The GhostTalker project"
__version__ = "1.0.5"
__status__ = "DEV"


# generic/built-in and other libs
import os
import sys
import time
import datetime
import json
import requests
import configparser
import subprocess
import logging
import logging.handlers
import prometheus_client


class igw(object):
    
    ## read config
    _config = configparser.ConfigParser()
    _rootdir = os.path.dirname(os.path.abspath(__file__))
    _config.read(os.path.join(_rootdir, "config.ini"))
    _env_ssh_path = _config.get("ENVIROMENT", "SSH_PATH", fallback='/usr/bin')
    _env_python_path = _config.get("ENVIROMENT", "PYTHON_PATH", fallback='/usr/bin')
    _unifi_host = _config.get("UNIFI", "UNIFI_HOST")
    _unifi_user = _config.get("UNIFI", "UNIFI_USER")
    _unifi_port = _config.get("UNIFI", "UNIFI_PORT")
    _unifi_on_off_sleeptime = _config.get("UNIFI", "UNIFI_OFF_ON_SLEEPTIME")
    _prometheus_enable = _config.getboolean("PROMETHEUS", "PROMETHEUS_ENABLE", fallback=False)
    _prometheus_port = _config.get("PROMETHEUS", "PROMETHEUS_PORT", fallback=8001)
    _sleeptime_between_check = _config.get("RUNTIME_PARAM", "SLEEPTIME_BETWEEN_CHECK", fallback=10)


    def __init__(self):

        # Define variables
        self.internet_status = 0

        # Start up the server to expose the metrics.
        if self._prometheus_enable:
            prometheus_client.start_http_server(int(igw._prometheus_port))	


        # Prometheus metric for build and running info
        self.igw_version_info = prometheus_client.Info('igw_build_version', 'Description of info')
        self.igw_version_info.info({'version': __version__, 'status': __status__, 'started': self.timestamp_to_readable_datetime(self.makeTimestamp())})
        self.igw_script_running_info = prometheus_client.Gauge('igw_script_cycle_info', 'Actual cycle of the running script')
        self.igw_script_running_info.set(0)
        self.igw_metric_status_info = prometheus_client.Gauge('igw_metric_status_info', 'Status of internet connection') 
        self.igw_metric_status_info.set(0)

    def check_igw(self):
        try_counter = 2
        counter = 0
		
        while counter < try_counter:
            try:
                result = requests.head('https://www.google.ch')
                result.raise_for_status()
       
                if result.status_code != 200:
                    logging.info(("Waiting {} seconds and trying again").format(self._sleeptime_between_check))
                    time.sleep(int(self._sleeptime_between_check))
                    counter = counter + 1
                else:
                    logging.info("Internet is reachable, continuing...")
                    self.internet_status = 0
                    return
       
            except requests.exceptions.RequestException as err:
                logging.info(f"Internet is not reachable! Error: {err}")
                time.sleep(int(self._sleeptime_between_check))
                counter = counter + 1

        self.internet_status = 1
        self.restart_unifi_port()


    def restart_unifi_port(self):        
        cmd = "{}/ssh {}@{} 'ubntbox swctrl poe set off id {};  sleep {}; ubntbox swctrl poe set auto id {}'".format(self._env_ssh_path, self._unifi_user, self._unifi_host, self._unifi_port, self._unifi_on_off_sleeptime, self._unifi_port)
        try:
            subprocess.check_output([cmd], shell=True)
        except subprocess.CalledProcessError:
            logging.info("Connection to unifi device failed")


    def create_prometheus_metrics(self):
        logging.info(f'create metrics for prometheus...')

        self.igw_script_running_info.inc()
        self.igw_metric_status_info.set(self.internet_status)
       

    def makeTimestamp(self):
        ts = int(time.time())
        return ts


    def timestamp_to_readable_datetime(self, vartimestamp):
        try:
            """ make timestamp human readable """
            timestamp = datetime.datetime.fromtimestamp(vartimestamp)
        except:
            """ prevent error while having wrong timestamp """
            timestamp = datetime.datetime.fromtimestamp(self.makeTimestamp())            
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")           
				

## Logging handler
def create_timed_rotating_log(log_file):
    logging.basicConfig(filename=log_file, filemode='a', format='%(asctime)s %(levelname)-8s %(message)s',
                        level=logging.getLevelName(log_level))
    logger = logging.getLogger(__name__)
    file_handler = logging.handlers.TimedRotatingFileHandler(log_file, when="midnight", backupCount=3)
    logger.addHandler(file_handler)


def create_stdout_log():
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                        level=logging.getLevelName(log_level))
    logger = logging.getLogger(__name__)
    stdout_handler = logging.StreamHandler(sys.stdout)
    logger.addHandler(stdout_handler)


if __name__ == '__main__':

    # Logging Options
    logconfig = configparser.ConfigParser()
    logrootdir = os.path.dirname(os.path.abspath('config.ini'))
    logconfig.read(logrootdir + "/config.ini")
    log_mode = logconfig.get("LOGGING", "LOG_MODE", fallback='console')
    log_filename = logconfig.get("LOGGING", "LOG_FILENAME", fallback='igw.log')
    log_level = logconfig.get("LOGGING", "LOG_LEVEL", fallback='INFO')

    if log_mode == "console":
        create_stdout_log()
    elif log_mode == "file":
        create_timed_rotating_log(log_filename)
    else:
        create_timed_rotating_log('/dev/null')

    ## init igw
    igw = igw()

    try:
        # Loop for checking every configured interval
        while True:

            # Start checking internet
            logging.info("Checking Internet connectivity...")	
            igw.check_igw()
			
            # Create prometheus metrics
            if igw._prometheus_enable:
                igw.create_prometheus_metrics()   

            # Waiting for next check			
            logging.info("Waiting {} seconds for next check...".format(igw._sleeptime_between_check))
            time.sleep(int(igw._sleeptime_between_check))
	
    except KeyboardInterrupt:
        logging.info("IGW will be stopped")
        exit(0)	