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

If the controller universal getter (get_atomic_value) returns a single value, then the
`single_value.json` file is a good place to start.  Just edit it to configure for your telemetry.
If the getter returns a list, and you want to specify a location for each sensor in a list then use the
`multiple_value.json` file and edit it to include locations.  The locations are optional and not
required.  A more specific example without locations can be found in `example.json`.
