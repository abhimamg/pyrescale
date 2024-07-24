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


**Create First Job**

```python
from rescaleapi import Job

# Initialize the Job with your API key
j = Job(api_key="xxxxxxxxxxxxxx")

# Add hardware specifications
j.add_hardware(cores=1, slots=1)

# Add a Conda environment and specify the input files and command
j.add_conda(inputfiles=["main.py"], command="python main.py")

# Create the job with a name
j.create("Demo Example")

# Submit the job
j.submit()
```


**Adding Abaqus as a Software**

To add Abaqus as a software in your job, use the following code:

```python
j.add_abaqus(version="2022", inputfiles=["job1.inp"], command="abaqus j=job1.inp interactive")
```

**Get Available Abaqus Versions**

To get a list of available Abaqus versions, run:

```python
j.get_abaqus_versions()
print("Available Abaqus versions:", versions)
```

