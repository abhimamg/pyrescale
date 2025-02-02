# Rescale API

**Rescale API** is a python API for communicating with the rescale platform.

## Getting Started

To use the Rescale API, you need to obtain an API key. You can get your Rescale API key by following the instructions [here](https://rescale.com/documentation/main-2/rescale-advanced-features/rest-api/).

## Prerequisites

- Python 3.10 or higher
- An active Rescale account


## Installation

To install the Rescale API package, run the following command:

```bash
pip install rescaleapi
```


## Usage

Here's an example of how to create and submit your first job using the Rescale API:

**Set API Key**
Add user enviroment variable `RESCALE_API_KEY` with your API key.


**Create First Job**

```python
from rescaleapi import Hardware, Job, Abaqus, File

# Collect the files. You can either upload files from your local machine or use the Rescale API to upload files from your Rescale account.
inputfiles = [File().load_from_id("zNXApj"), File("files.zip")]

# Add hardware specifications
hardware = Hardware(coresPerSlot=1, slots=1, coreType="emerald_max")

# Add Software
abaqus = Abaqus(version = "2022-2328", inputfiles=inputfiles, command="abaqus j=job1.inp interactive")

# Create the job with a name
job = Job("Demo Example",  hardware = hardware, analyses=[abaqus])
job.create()

# Submit the job
j.submit()
```


**Get Available Abaqus Versions**

To get a list of available Abaqus versions codes, run:

```python
versions = Abaqus.get_version_code("2024 HF4 (FlexNet Licensing)")
print(versions)
```

