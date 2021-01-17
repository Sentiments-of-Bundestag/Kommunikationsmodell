# Sentiments-of-Bundestag: Communication Model Extraction (CME)

**Group 2**: Kommunikationsmodell

This service generates communication data out of the parsed XML data from Group 1.

The workflow and interfaces to Group 1 (Crawer, Entity Extraction) and Group 3 (Semantic analyses) is shown here:

![Ablaufdiagramm](./resources/Ablaufdiagramm.jpg)

## Installation

This service consists of two sub-services:
1. The API, which contains the `Communication Model Extractor` (or `cme` for short) and all the business logic.
2. A mongo database
 
Installation depends on whether you want to install it in a productive or a development environment.

### Production

For production, you start both sub-services as docker services.

First, make sure to fill all `<username>` and `<password>` credentials in the `./deployment/.env.prod.example` file.
Afterwards, rename it to `.env.prod`.

To start, execute 

```bash
./deployment/start_prod.sh
```

To stop, execute:

```bash
./deployment/stop_prod.sh
```

### Development

For the development environment, you start the api service locally (without docker) and the mongodb as a docker service (together with a mongo-express service for debugging).  

#### mongodb

The mongodb can be spin up with

```bash
docker-compose up
```

and turned down with 

```bash
docker-compose down
```

#### API

The cme sub-service is structured as an installable python package. We highly recommend setting up a 
[venv](https://docs.python.org/3/library/venv.html). Either way, you have to install it once with all it's dependencies 
with:

```
pip install -e .
```

Now, `cme` should be an available executable. Every time you want to spin up your api, use the script: 

```bash
./run_api.sh
```

## CME Options

Once the cme package is installed, you can use `cme` features other than the cme api service. 
This is mostly usefull for debugging. 

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
