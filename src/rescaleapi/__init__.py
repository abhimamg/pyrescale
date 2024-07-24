import json
import sys
import requests
import click
import os
import io

DEFAULT_TIMEOUT = 60


def get_api(api_key):
    """
    Get the Rescale API key from the provided input or environment variable.
    """
    if api_key is None:
        api_key = os.environ.get("RESCALE_API_KEY", None)
    if api_key is None:
        click.secho("API key not found", fg="red")
        api_key_error()
    return api_key


class Job:
    """
    Represents a Rescale Job.
    """

    def __init__(self, job_id=None, api_key=None):
        """
        Initializes a new Rescale Job.

        Args:
            job_id (str): The Rescale job ID.
            api_key (str): The Rescale API key.
        """
        click.echo("Initializing New Rescale Job")
        self.api_key = get_api(api_key)
        self.id = job_id
        self.analyses = []
        self.param = None

    def add_param(self, param):
        """
        Adds a parameter to the job.

        Args:
            param: The parameter to be added.
        """
        self.param = None if param is None else param.id_string()

    @property
    def url(self):
        """
        Returns the job's URL.
        """
        return f"https://platform.rescale.com/api/v2/jobs/{self.id or ''}"

    def search_file(self, search_string):
        """
        Searches for a file in the job.
        """
        pass

    @property
    def status(self):
        """
        Retrieves the status of the job and its associated cluster.
        """
        status_ = {}
        url = self.url + "/statuses/"
        status_["job"] = send_get(url, self.api_key)
        url = self.url + "/statuses/"
        status_["cluster"] = send_get(url, self.api_key)
        return status_

    def get_meta(self):
        """
        Retrieves metadata for the job.
        """
        self.meta = send_get(self.url, self.api_key)

    def add_hardware(self, cores=1, slots=1):
        """
        Adds hardware specifications to the job.
        """
        click.echo(f"Adding hardware: {click.style('emerald_max', fg='cyan')}")
        self.hardware = {
            "coreType": "emerald_max",
            "coresPerSlot": cores,
            "slots": slots or 1,
        }

    def get_available_analyses(self):
        """
        Retrieves available analyses from Rescale.
        """
        url = "https://platform.rescale.com/api/v2/analyses/"
        return send_get(url, self.api_key, timeout=200)

    def get_available_hardwares(self):
        """
        Retrieves available hardware configurations from Rescale.
        """
        url = "https://platform.rescale.com/api/v2/coretypes/?page=1&page_size=500"
        return send_get(url, self.api_key, timeout=200)

    def get_hardware_codes(self):
        """
        Retrieves hardware codes and their names.
        """
        hardwares = self.get_available_hardwares()
        hardwares = [(i["code"], i["name"]) for i in hardwares["results"]]
        return dict(hardwares)

    def get_abaqus_versions(self):
        """
        Retrieves available Abaqus versions.
        """
        a = self.get_available_analyses()
        abaqus_versions = [i for i in a["results"] if i["code"] == "abaqus"]
        abaqus_versions = [
            (i["version"], i["versionCode"]) for i in abaqus_versions[0]["versions"]
        ]
        return dict(abaqus_versions)

    def add_analysis(
        self,
        code,
        version,
        command,
        inputfiles=[],
        templates=[],
        post_script=None,
        post_command="",
        env_var={},
    ):
        """
        Adds an analysis to the job.
        """
        if bool(post_command) != bool(post_script):
            raise Exception("Both post_command and post_script must be provided")

        post_script = None if post_script is None else post_script.id_string()
        self.analyses.append(
            {
                "analysis": {
                    "code": code,
                    "version": version,
                },
                "command": command,
                "hardware": self.hardware,
                "inputFiles": [file.id_string() for file in inputfiles],
                "templateTasks": [file.template_string() for file in templates],
                "postProcessScript": post_script,
                "postProcessScriptCommand": post_command,
                "envVars": env_var,
            }
        )

    def add_conda(
        self,
        inputfiles,
        command,
        post_script=None,
        post_command="",
        env_var={},
    ):
        """
        Adds a Miniconda analysis to the job.
        """
        click.echo(f"Adding Miniconda {click.style('5.3.1', fg='cyan')}")

        self.add_analysis(
            code="anaconda",
            version="5.3.1",
            command=command,
            inputfiles=inputfiles,
            post_script=post_script,
            post_command=post_command,
            env_var=env_var,
        )

    def add_abaqus(
        self,
        version,
        inputfiles,
        templates=[],
        command="",
        license_="27101@us001sa0200",
    ):
        """
        Adds an Abaqus analysis to the job.
        """
        versions = {
            "2023": "2023-hf4",
            "2022": "2022-2241",
            "2021": "2021-2140",
            "2020": "2020-2136",
            "2019": "2019-1947",
            "2018": "2018-1928",
            "2017": "2017-gpu",
            "2016": "2016-2005",
            "6.14-3": "6.14.3-pcmpi",
            "6.14-2": "6.14.2-pcmpi",
        }

        click.echo(f"Adding Abaqus {click.style(version, fg='cyan')}")
        self.add_analysis(
            code="abaqus",
            version=versions[str(version)],
            command="# interactive\n" + command,
            templates=templates,
            inputfiles=inputfiles,
            env_var={"LM_LICENSE_FILE": license_},
        )

    def create(self, name):
        """
        Creates a new job.
        """
        click.echo(f"Creating new job: {click.style(name, fg='cyan')}")
        if self.id is not None:
            raise Exception("Job already exists")
        json_data = {
            "name": name,
            "jobanalyses": self.analyses,
            "paramFile": self.param,
        }

        template_check = any(analysis["templateTasks"] for analysis in self.analyses)
        if bool(self.param) != template_check:
            raise Exception(
                "If param file is provided, at least one analysis must have template tasks"
            )

        self.meta = send_post(self.url, self.api_key, json_data=json_data)
        self.id = self.meta["id"]
        click.echo(f"Job created: {click.style(self.id, fg='cyan')}")

    def submit(self):
        """
        Submits the job for execution.
        """
        click.echo(f"Submitting job: {click.style(self.id, fg='cyan')}")
        url = self.url + "/submit/"
        send_post(url=url, api_key=self.api_key)


class File:
    """
    Represents a Rescale File.
    """

    def __init__(self, file=None, upload=False, api_key=None, name=None, is_text=False):
        """
        Initializes a new Rescale File.
        """
        self.id = None if upload else file
        self.path = file if upload else None
        self.api_key = get_api(api_key)
        self.is_text = is_text
        self.name = name

    @property
    def url(self):
        """
        Returns the file's URL.
        """
        return f"https://platform.rescale.com/api/v2/files/{self.id or ''}"

    def get_meta(self):
        """
        Retrieves metadata for the file.
        """
        self.meta = send_get(self.url, self.api_key)
        self.name = self.meta["name"]

    def patch(self, data):
        """
        Updates file metadata.
        """
        self.meta = send_patch(self.url, self.api_key, data=data)

    def id_string(self):
        """
        Returns the file ID as a dictionary.
        """
        if self.id is None:
            self.upload()
        return {"id": self.id}

    def template_string(self):
        """
        Returns the file ID and processed filename as a dictionary.
        """
        id_string = self.id_string()
        if self.name is None:
            self.get_meta()
        return {
            "templateFile": id_string,
            "processedFilename": self.name,
        }

    def list_all_files(self):
        """
        Retrieves a list of all files from Rescale.
        """
        url = "https://platform.rescale.com/api/v2/files/"
        return send_get(url, self.api_key)

    def upload(self):
        """
        Uploads the file to Rescale.
        """
        click.echo(
            f"Uploading {click.style(self.name if self.is_text else self.path, fg='cyan')}"
        )
        if self.id is not None:
            raise Exception("File already exists")

        url = "https://platform.rescale.com/api/v2/files/contents/"

        if self.is_text:
            buffer = (self.name, io.BytesIO(self.path.encode("utf-8")))
        else:
            if self.name:
                buffer = (self.name, open(self.path, "rb"))
            else:
                buffer = open(self.path, "rb")

        resp = requests.post(
            url,
            timeout=DEFAULT_TIMEOUT,
            data=None,
            files={"file": buffer},  # noqa: SIM115
            headers={
                "Authorization": f"Token {self.api_key}",
            },
        )
        self.meta = get_json(resp)
        self.name = self.meta["name"]
        self.id = self.meta["id"]


def get_json(resp):
    """
    Extract JSON content from the response.
    """
    try:
        content = json.loads(resp.content)
    except json.JSONDecodeError as e:
        return e
    if resp.status_code >= 300:
        if resp.status_code == 401:
            click.secho("API key not valid", fg="red")
            api_key_error()

        else:
            raise click.ClickException(f"[{resp.status_code}]: {content}")
    else:
        return content


def api_key_error():
    """
    Display an error message about the missing or invalid API key and exit the script.
    """
    s1 = click.style("setx RESCALE_API_KEY XXXXXXXXXX", fg="cyan", bold=True)
    msg = (
        "Set Rescale API key using the following command in the command prompt"
        f" {s1} and restart the command prompt.\nSee https://rescale.com/documentation"
        "/main/rescale-advanced-features/rest-api/ to get API key."
    )

    click.echo(msg)
    sys.exit()


def send_get(url, api_key, timeout=DEFAULT_TIMEOUT):
    """
    Send a GET request to the specified URL with the Rescale API key.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {api_key}",
    }
    with requests.Session() as session:
        response = session.get(
            url,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )

    content = get_json(response)
    return content


def send_post(
    url,
    api_key,
    json_data=None,
    timeout=DEFAULT_TIMEOUT,
):
    """
    Send a POST request to the specified URL with the Rescale API key.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {api_key}",
    }
    with requests.Session() as session:
        response = session.post(
            url,
            headers=headers,
            json=json_data,
            timeout=DEFAULT_TIMEOUT,
        )
    content = get_json(response)
    return content


def send_patch(
    url,
    api_key,
    data,
    timeout=DEFAULT_TIMEOUT,
):
    """
    Send a PATCH request to the specified URL with the Rescale API key.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Token {api_key}",
    }
    with requests.Session() as session:
        response = session.patch(
            url,
            data,
            headers=headers,
            timeout=DEFAULT_TIMEOUT,
        )
    content = get_json(response)
    return content


if __name__ == "__main__":
    pass
