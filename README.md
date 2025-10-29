# logtel

Utility for logging telemetry to influxDB

## Features

- Configurable logging of telemetry to an InfluxDB database
- Works with libraries that have implemented the hardware_device_base class
- Logging defaults to INFO, but verbose mode uses DEBUG level logging

## Requirements

 - Need an InfluxDB token and a bucket and organization set up for the database
 - Need the low-level library to implement get_atomic_value method from abstract class

## Installation

```bash
pip install .
```

## Usage

Copy influx_db.json file and edit to configure for telemetry.  See example.json
for an example of how to configure.
