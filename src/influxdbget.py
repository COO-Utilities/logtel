#!/usr/bin/env python3
"""get telemetry values from influxdb
"""
import importlib
import time
import sys
import json
import logging
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from urllib3.exceptions import ReadTimeoutError

def main(config_file):
    """Read config file for setup info and retrieve from InfluxDB."""
    # pylint: disable=too-many-branches, too-many-statements, too-many-locals

    # read the config file
    with open(config_file, encoding='utf-8') as cfg_file:
        cfg = json.load(cfg_file)

    verbose = cfg['verbose'] == 1

    items = cfg['log_items']
    device = cfg['device']
    if 'log_locations' in cfg:
        locations = cfg['log_locations']
    else:
        locations = None

    # set up logging
    logfile = cfg['logfile']
    if logfile is None:
        logfile = __name__.rsplit(".", 1)[-1]
    logger = logging.getLogger(logfile)
    if verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    # log to console by default
    console_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    # log to file if requested
    if cfg['logfile'] is not None:
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(funcName)s() - %(message)s"
        )
        file_handler = logging.FileHandler(logfile if ".log" in logfile else logfile + ".log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Connect to InfluxDB
    logger.info('Connecting to InfluxDB...')
    db_client = InfluxDBClient(url=cfg['db_url'], token=cfg['db_token'],
                               org=cfg['db_org'])
    query_api = db_client.query_api()

    results = []
    for item in items:
        query = ""
