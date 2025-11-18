#!/usr/bin/env python3
"""log telemetry to influxdb

Assumes controller module has implemented the abstract methods in hardware_device_base module.

See https://github.com/COO-Utilities/hardware_device_base for more info.
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
    """Read config file for setup info and start logging to InfluxDB."""
    # pylint: disable=too-many-branches, too-many-statements, too-many-locals

    # read the config file
    with open(config_file, encoding='utf-8') as cfg_file:
        cfg = json.load(cfg_file)

    verbose = cfg['verbose'] == 1

    contmod = importlib.import_module(cfg['controller_module'])

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

    logger.info('Connecting to %s', cfg['controller_module'])
    contclass = getattr(contmod, cfg['controller_class'])
    if cfg['controller_kwargs']:
        controller = contclass(**cfg['controller_kwargs'])
    else:
        controller = contclass()
    if cfg['device_host'] and cfg['device_port']:
        controller.connect(cfg['device_host'], cfg['device_port'])

    items = cfg['log_items']
    device = cfg['device']
    if 'log_locations' in cfg:
        locations = cfg['log_locations']
    else:
        locations = None

    # Try/except to catch exceptions
    db_client = None
    try:
        # Loop until ctrl-C
        while True:
            try:
                # Connect to InfluxDB
                logger.info('Connecting to InfluxDB...')
                db_client = InfluxDBClient(url=cfg['db_url'], token=cfg['db_token'],
                                           org=cfg['db_org'])
                write_api = db_client.write_api(write_options=SYNCHRONOUS)

                for item in items:
                    expected_type = items[item]['value_type']
                    # Universal getter
                    value = controller.get_atomic_value(item)
                    # Deal with a list of values
                    if isinstance(value, list):
                        # Does our list have the correct types?
                        if all(isinstance(datum, eval(expected_type)) for datum in value):
                            # Loop over our list
                            for num, datum in enumerate(value):
                                # Are locations specified?
                                if locations:
                                    if str(num + 1) in locations:
                                        location = locations[str(num + 1)]
                                    else:
                                        location = "Unknown"
                                    point = (
                                        Point(device)
                                        .field(items[item]['field']+str(num+1), datum)
                                        .tag("location", location)
                                        .tag("units", items[item]['units'])
                                        .tag("channel", f"{cfg['db_channel']}")
                                    )
                                # No locations specified
                                else:
                                    point = (
                                        Point(device)
                                        .field(items[item]['field'] + str(num + 1), datum)
                                        .tag("units", items[item]['units'])
                                        .tag("channel", f"{cfg['db_channel']}")
                                    )
                                # Write to database and log
                                write_api.write(bucket=cfg['db_bucket'], org=cfg['db_org'], record=point)
                                logger.debug(point)
                        else:
                            logger.error("Type error, expected %s, got %s",
                                         expected_type, type(value[0]))
                    # Single value returned from getter
                    else:
                        # pylint: disable=eval-used
                        # Is our value of the expected type?
                        if isinstance(value, eval(expected_type)):
                            point = (
                                Point(device)
                                .field(items[item]['field'], value)
                                .tag("units", items[item]['units'])
                                .tag("channel", f"{cfg['db_channel']}")
                            )
                            # Write to database and log
                            write_api.write(bucket=cfg['db_bucket'], org=cfg['db_org'], record=point)
                            logger.debug(point)
                        else:
                            logger.error("Type error, expected %s, got %s",
                                         expected_type, type(value))

                # Close db connection
                logger.info('Closing connection to InfluxDB...')
                db_client.close()
                db_client = None

            # Handle exceptions
            except ReadTimeoutError as e:
                logger.critical("ReadTimeoutError: %s, will retry.", e)
            except Exception as e:
                logger.critical("Unexpected error: %s, will retry.", e)

            # Sleep for interval_secs
            logger.info("Waiting %d seconds...", cfg['interval_secs'])
            time.sleep(cfg['interval_secs'])

    except KeyboardInterrupt:
        logger.critical("Shutting down InfluxDB logging...")
        if db_client:
            db_client.close()
        controller.disconnect()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python log2influxdb.py <your_edited_configuration.json>")
        sys.exit(0)
    main(sys.argv[1])
