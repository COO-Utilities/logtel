"""log telemetry to influxdb"""
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

    # read the config file
    with open(config_file, encoding='utf-8') as cfg_file:
        cfg = json.load(cfg_file)

    verbose = cfg['verbose'] == 1

    contmod = importlib.import_module(cfg['controller_module'])

    # Do we have a logfile?
    if cfg['logfile'] is not None:
        # log to a file
        logger = logging.getLogger(cfg['logfile'])
        if verbose:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler = logging.FileHandler(cfg['logfile'])
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    else:
        logger = None

    if verbose:
        print("Connecting to " + cfg['controller_module'])
    if logger:
        logger.info('Connecting to %s', cfg['controller_module'])
    contclass = getattr(contmod, cfg['controller_class'])
    if cfg['controller_kwargs']:
        controller = contclass(**cfg['controller_kwargs'])
    else:
        controller = contclass()
    if cfg['device_host'] and cfg['device_port']:
        controller.connect(cfg['device_host'], cfg['device_port'])

    channels = cfg['log_channels']
    device = cfg['device']

    # Try/except to catch exceptions
    db_client = None
    try:
        # Loop until ctrl-C
        while True:
            try:
                # Connect to InfluxDB
                if verbose:
                    print("Connecting to InfluxDB...")
                if logger:
                    logger.info('Connecting to InfluxDB...')
                db_client = InfluxDBClient(url=cfg['db_url'], token=cfg['db_token'],
                                           org=cfg['db_org'])
                write_api = db_client.write_api(write_options=SYNCHRONOUS)

                for chan in channels:
                    expected_type = cfg['log_channels'][chan]['value_type']
                    get_value_function_name = cfg['log_channels'][chan]['get_value']
                    get_value = getattr(controller, get_value_function_name)
                    if cfg['log_channels'][chan]['channel_name']:
                        value = get_value(cfg['log_channels'][chan]['channel_name'])
                    else:
                        value = get_value()
                    # pylint: disable=eval-used
                    if isinstance(value, eval(expected_type)):
                        point = (
                            Point(device)
                            .field(channels[chan]['field'], value)
                            .tag("units", channels[chan]['units'])
                            .tag("channel", f"{cfg['db_channel']}")
                        )
                        write_api.write(bucket=cfg['db_bucket'], org=cfg['db_org'], record=point)
                        if verbose:
                            print(point)
                        if logger:
                            logger.debug(point)
                    else:
                        if verbose:
                            print(f"Type error, expected {expected_type}, got {type(value)}")
                        if logger:
                            logger.error("Type error, expected %s, got %s",
                                         expected_type, type(value))

                # Close db connection
                if verbose:
                    print("Closing connection to InfluxDB...")
                if logger:
                    logger.info('Closing connection to InfluxDB...')
                db_client.close()
                db_client = None

            # Handle exceptions
            except ReadTimeoutError as e:
                print(f"ReadTimeoutError: {e}, will retry.")
                if logger:
                    logger.critical("ReadTimeoutError: %s, will retry.", e)
            except Exception as e:
                print(f"Unexpected error: {e}, will retry.")
                if logger:
                    logger.critical("Unexpected error: %s, will retry.", e)

            # Sleep for interval_secs
            if verbose:
                print(f"Waiting {cfg['interval_secs']:d} seconds...")
            if logger:
                logger.info("Waiting %d seconds...", cfg['interval_secs'])
            time.sleep(cfg['interval_secs'])

    except KeyboardInterrupt:
        print("\nShutting down InfluxDB logging...")
        if logger:
            logger.critical("Shutting down InfluxDB logging...")
        if db_client:
            db_client.close()
        controller.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python log2influxdb.py <influxdb_log.json>")
        sys.exit(0)
    main(sys.argv[1])
