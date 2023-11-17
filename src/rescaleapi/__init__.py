import json
import sys
import requests
import rich_click as click
import os
import io

DEFAULT_TIMEOUT = 60


def get_api(api_key):
    """
    Get the Rescale API key from the provided input or environment variable.

    Args:
        api_key (str): The Rescale API key.

    Returns:
        str: The Rescale API key.

    Raises:
        click.ClickException: If the API key is not found.
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

    Attributes:
        id (str): The Rescale job ID.
        api_key (str): The Rescale API key.
        analyses (list): List of analyses associated with the job.
        param (str): Parameter file ID associated with the job.

    Methods:
        add_param(param): Adds a parameter to the job.
        url(): Returns the job's URL.
        search_file(search_string): Searches for a file in the job.
        status(): Retrieves the status of the job and its associated cluster.
        get_meta(): Retrieves metadata for the job.
        add_hardware(cores, slots): Adds hardware specifications to the job.
        get_available_analyses(): Retrieves available analyses from Rescale.
        get_available_hardwares(): Retrieves available hardware configurations from Rescale.
        get_hardware_codes(): Retrieves hardware codes and their names.
        get_abaqus_versions(): Retrieves available Abaqus versions.
        add_analysis(): Adds an analysis to the job.
        add_conda(): Adds a Miniconda analysis to the job.
        add_abaqus(): Adds an Abaqus analysis to the job.
        create(name): Creates a new job.
        submit(): Submits the job for execution.
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

        Returns:
            str: The job's URL.
        """
        return f"https://platform.rescale.com/api/v2/jobs/{self.id or ''}"

    def search_file(self, search_string):
        """
        Searches for a file in the job.

        Args:
            search_string (str): The string to search for in files.

        Returns:
            None
        """
        pass

    @property
    def status(self):
        """
        Retrieves the status of the job and its associated cluster.

        Returns:
            dict: A dictionary containing job and cluster statuses.
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

        Returns:
            None
        """
        self.meta = send_get(self.url, self.api_key)

    def add_hardware(self, cores=1, slots=1):
        """
        Adds hardware specifications to the job.

        Args:
            cores (int): Number of cores.
            slots (int): Number of slots.

        Returns:
            None
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

        Returns:
            dict: A dictionary containing available analyses.
        """
        url = "https://platform.rescale.com/api/v2/analyses/"
        return send_get(url, self.api_key, timeout=200)

    def get_available_hardwares(self):
        """
        Retrieves available hardware configurations from Rescale.

        Returns:
            dict: A dictionary containing available hardware configurations.
        """
        url = "https://platform.rescale.com/api/v2/coretypes/?page=1&page_size=500"
        return send_get(url, self.api_key, timeout=200)

    def get_hardware_codes(self):
        """
        Retrieves hardware codes and their names.

        Returns:
            dict: A dictionary containing hardware codes and their names.
        """
        hardwares = self.get_available_hardwares()
        hardwares = [(i["code"], i["name"]) for i in hardwares["results"]]
        return dict(hardwares)

    def get_abaqus_versions(self):
        """
        Retrieves available Abaqus versions.

        Returns:
            dict: A dictionary containing Abaqus versions and their codes.
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

        Args:
            code (str): Analysis code.
            version (str): Analysis version.
            command (str): Analysis command.
            inputfiles (list): List of input files.
            templates (list): List of template files.
            post_script: Post-process script.
            post_command (str): Post-process command.
            env_var (dict): Environment variables.

        Returns:
            None
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

        Args:
            inputfiles (list): List of input files.
            command (str): Analysis command.
            post_script: Post-process script.
            post_command (str): Post-process command.
            env_var (dict): Environment variables.

        Returns:
            None
        """
        click.echo(f"Adding Miniconda {click.style('4.8.4', fg='cyan')}")

        self.add_analysis(
            code="miniconda",
            version="4.8.4",
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

        Args:
            version (str): Abaqus version.
            inputfiles (list): List of input files.
            templates (list): List of template files.
            command (str): Analysis command.
            license_ (str): License information.

        Returns:
            None
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

        Args:
            name (str): Name of the job.

        Returns:
            None

        Raises:
            Exception: If the job already exists or parameter conditions are not met.
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

        Returns:
            None
        """
        click.echo(f"Submitting job: {click.style(self.id, fg='cyan')}")
        url = self.url + "/submit/"
        send_post(url=url, api_key=self.api_key)


class File:
    """
    Represents a Rescale File.

    Attributes:
        id (str): The Rescale file ID.
        path (str): The file path.
        api_key (str): The Rescale API key.
        is_text (bool): Indicates whether the file is a text file.
        name (str): The name of the file.

    Methods:
        url(): Returns the file's URL.
        get_meta(): Retrieves metadata for the file.
        patch(data): Updates file metadata.
        id_string(): Returns the file ID as a dictionary.
        template_string(): Returns the file ID and processed filename as a dictionary.
        list_all_files(): Retrieves a list of all files from Rescale.
        upload(): Uploads the file to Rescale.
    """

    def __init__(self, file=None, upload=False, api_key=None, name=None, is_text=False):
        """
        Initializes a new Rescale File.

        Args:
            file: The Rescale file ID or file path.
            upload (bool): Indicates whether the file needs to be uploaded.
            api_key (str): The Rescale API key.
            name (str): The name of the file.
            is_text (bool): Indicates whether the file is a text file.
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

        Returns:
            str: The file's URL.
        """
        return f"https://platform.rescale.com/api/v2/files/{self.id or ''}"

    def get_meta(self):
        """
        Retrieves metadata for the file.

        Returns:
            None
        """
        self.meta = send_get(self.url, self.api_key)
        self.name = self.meta["name"]

    def patch(self, data):
        """
        Updates file metadata.

        Args:
            data: The data to be patched.

        Returns:
            None
        """
        self.meta = send_patch(self.url, self.api_key, data=data)

    def id_string(self):
        """
        Returns the file ID as a dictionary.

        Returns:
            dict: The file ID.
        """
        if self.id is None:
            self.upload()
        return {"id": self.id}

    def template_string(self):
        """
        Returns the file ID and processed filename as a dictionary.

        Returns:
            dict: The file ID and processed filename.
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

        Returns:
            dict: A dictionary containing information about all files.
        """
        url = "https://platform.rescale.com/api/v2/files/"
        return send_get(url, self.api_key)

    def upload(self):
        """
        Uploads the file to Rescale.

        Returns:
            None
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

    Args:
        resp (requests.Response): The HTTP response object.

    Returns:
        dict: Parsed JSON content from the response.

    Raises:
        click.ClickException: If the response status code is greater than or equal to 300.
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

    Raises:
        click.ClickException: Always raised to terminate the script execution.
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

    Args:
        url (str): The URL to send the GET request to.
        api_key (str): The Rescale API key.
        timeout (int, optional): Timeout for the HTTP request. Defaults to DEFAULT_TIMEOUT.

    Returns:
        dict: Parsed JSON content from the response.

    Raises:
        click.ClickException: If there is an issue with the API key or the response status code is >= 300.
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

    Args:
        url (str): The URL to send the POST request to.
        api_key (str): The Rescale API key.
        json_data (dict, optional): JSON data to include in the request body. Defaults to None.
        timeout (int, optional): Timeout for the HTTP request. Defaults to DEFAULT_TIMEOUT.

    Returns:
        dict: Parsed JSON content from the response.

    Raises:
        click.ClickException: If there is an issue with the API key or the response status code is >= 300.
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

    Args:
        url (str): The URL to send the PATCH request to.
        api_key (str): The Rescale API key.
        data (dict): Data to include in the request body.
        timeout (int, optional): Timeout for the HTTP request. Defaults to DEFAULT_TIMEOUT.

    Returns:
        dict: Parsed JSON content from the response.

    Raises:
        click.ClickException: If there is an issue with the API key or the response status code is >= 300.
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
