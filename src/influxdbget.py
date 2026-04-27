#!/usr/bin/env python3
"""get telemetry values from influxdb
"""
import json
import logging
from influxdb_client import InfluxDBClient
import certifi # Used for SSL certificate verification on some systems

class InfluxDBRetriever:
    """
    A class for connecting to and retrieving data from InfluxDB.

    # Example Usage
    if __name__ == '__main__':
        # **Replace with your actual InfluxDB details**
        URL = "http://localhost:8086"
        TOKEN = "your-super-secret-token"
        ORG = "your-organization"
        BUCKET = "your-bucket"

        # Initialize the retriever class
        db_retriever = InfluxDBRetriever(URL, TOKEN, ORG, BUCKET)

        # Define your query (using Flux in this example)
        flux_query = f'''
        from(bucket: "{BUCKET}")

          |> range(start: -10m)
          |> filter(fn: (r) => r._measurement == "h2o_level")
          |> filter(fn: (r) => r.location == "coyote_creek")
        '''

        # Retrieve data as a list of dictionaries
        data_records = db_retriever.query_data(flux_query)
        print("--- Data Records (List of Dicts) ---")
        for record in data_records:
            print(record)

        # Close the connection
        db_retriever.close_connection()
    """
    def __init__(self, url, token, org, bucket):
        self.url = url
        self.token = token
        self.org = org
        self.bucket = bucket
        # Instantiate the client
        self.client = InfluxDBClient(
            url=self.url,
            token=self.token,
            org=self.org,
            ssl_ca_cert=certifi.where() # Optional: Helps with SSL verification
        )
        self.query_api = self.client.query_api()

    def query_data(self, query):
        """
        Executes a Flux query and returns the results as a list of records.
        """
        results = []
        try:
            # The query_api.query method returns a list of tables
            tables = self.query_api.query(query, org=self.org)

            for table in tables:
                for record in table.records:
                    # Append a dictionary of values for easier use
                    results.append(record.values)
        except Exception as e:
            print(f"An error occurred during query: {e}")
        return results

    def close_connection(self):
        """
        Closes the InfluxDB client connection.
        """
        self.client.close()



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
