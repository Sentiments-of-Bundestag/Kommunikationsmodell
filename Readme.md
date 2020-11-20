# Sentiments-of-Bundestag: Communication Model Extraction (CME)

**Group 2**: Kommunikationsmodell

We try to build a communication model out of the parsed XML data from Group 1.

This is pretty much work in progress. You can have a look into the examples folder to see what we are trying to archive.

The desired workflow with teams working before and after the communication model is shown here:

![Ablaufdiagramm](./resources/Ablaufdiagramm.jpg)

## Installation

For installation, you need two services
1. The API, which also contains the `Communication Model Extractor` (or `cme` for short) and all the business logic.
2. A mongodb.

### API

The project is structured as an installable python package. We highly recommend setting up a 
[venv](https://docs.python.org/3/library/venv.html). Either way, you can install it and all it's dependencies with:
```bash
pip install .
```

Or, to not reinstall during development, use the dev mode:
```
pip install -e .
```

Now, `cme` should be an available executable. 

### mongodb

The mongodb can be spin up with
```bash
docker-compose up
``` 

You can also host it locally, we're using port `27017`

## Usage

Once the API oder `cme` features a manual or server mode.

### Manual Mode

Manual mode allows you to convert input data from a file instead of waiting for a request to our REST API. The mode can 
be triggered by running: 
```bash
cme manual
```

### Server Mode
The server mode will start up our REST API endpoints and will wait for requests from group 1 or 3 
to do anything. To run `cme` in server mode just run:
```bash
cme server
```

### Flags
There are several flags which can be used to configure the behaviour of `cme`. To explore those 
just run `cme --help` or `cme -h`.

## API

The api will offer multiple endpoints which will be fully disclosed in a soon to come swagger-api documentation.

There will be at least the following endpoints:


This project retrieves the protocols from another group via direct DB access. For that you will have to set the following environment variables:
```
export CRAWL_DB_USER=""
export CRAWL_DB_PASSWORD=""
export CRAWL_DB_IP=""
``` 

* `/cme/data/` - for getting notified about updated data and new sessions to evaluate
* `/cme/data/session/{session_id}` - to retrieve a specific session
* `/cme/data/sessions` - to get a list of all existing sessions with their respective ID
* `/cme/data/period/{legislative_period}` - to retrieve all sessions in the given period

- mongoDB
- install and start as a daemon, accessible through port 27017 
    mac: brew
    linux: systemctl

## Main Supporter

* Max Lüdemann @menno4000
* Ralph Schlett @aradar
* Oskar Sailer @d064467
* Youri Seichter @medizinmensch
