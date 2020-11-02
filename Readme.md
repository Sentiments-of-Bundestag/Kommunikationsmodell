# Sentiments-of-Bundestag: Communication Model

**Group 2**: Kommunikationsmodell

We try to build a communication model out of the parsed XML data from Group 1.

This is pretty much work in progress. You can have a look into the examples folder to see what we are trying to archive.

## Installation

The project is structured as an installable python package. Therefore it can be installed through pip and will install 
all needed dependencies in this case.

To install it you just have to clone the repo and run `pip install .`, but it should be noted that this will install the
cme and dependencies system wide and **can potentially break your system package manager**! If it is not desired to 
install it system wide it makes sense to build a python [venv](https://docs.python.org/3/library/venv.html) in which you
can safely install the package and needed other packages.

If you want to change the code it should also be noted that the package can be installed in the so called development 
mode. Doing so makes it possible to change code without having to reinstall it after this to run it. To install it in 
dev mode just run `pip install -e .`.

## Usage

After the installation `cme` should be available in your path and can than either be used in manual or server mode.

todo: extend this

## Supporter

* Max Lüdemann
* Ralph Schlett
* Oskar Sailer
* Youri Seichter
