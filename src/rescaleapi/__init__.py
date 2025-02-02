# Standard library imports
import json
import sys
import os
from dataclasses import dataclass
from typing import List, Optional

# Third-party imports
import requests
import click

# Default timeout for API requests in seconds
DEFAULT_TIMEOUT = 60

def set_api_key(api_key: str) -> None:
    """Store Rescale API key in environment."""
    os.environ["RESCALE_API_KEY"] = api_key

def get_api_key() -> str:
    """Get Rescale API key from environment."""
    return os.environ.get("RESCALE_API_KEY")

@dataclass
class ApiResponse:
    """Base class for API interactions."""
    BASE_URL = "https://platform.rescale.com/api/v2/"

    def __post_init__(self):
        """Set API key after init."""
        self.api_key = get_api_key()

    def _get_headers(self) -> dict:
        """Get request headers."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_key}",
        }

    def send_get(self, endpoint: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
        """Send GET request."""
        url = f"{self.BASE_URL}{endpoint}"
        with requests.Session() as session:
            response = session.get(
                url,
                headers=self._get_headers(),
                timeout=timeout,
            )
            return self.parse_response(response)

    def send_post(
        self,
        endpoint: str,
        json_data: Optional[dict] = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> dict:
        """Send POST request."""
        url = f"{self.BASE_URL}{endpoint}"
        with requests.Session() as session:
            response = session.post(
                url,
                headers=self._get_headers(),
                json=json_data,
                timeout=timeout,
            )
            return self.parse_response(response)

    @staticmethod
    def parse_response(response: requests.Response) -> dict:
        """Parse API response."""
        if response.status_code >= 300:
            click.echo(f"Error: {response.status_code}")
            click.echo(response.text)
            sys.exit(1)
        try:
            return response.json()
        except json.JSONDecodeError:
            return response.text

@dataclass
class Hardware(ApiResponse):
    """Hardware configuration settings."""
    coreType: str = "emerald_max"
    coresPerSlot: int = 1
    slots: int = 1

    def get_available_hardwares(self, page: int = 1) -> dict:
        """Get hardware options."""
        return self.send_get(f"coretypes?page={page}")

    def to_json(self) -> dict:
        """Convert to JSON format."""
        return {
            "coreType": self.coreType,
            "coresPerSlot": self.coresPerSlot,
            "slots": self.slots,
        }

@dataclass
class File(ApiResponse):
    """File upload handler."""
    path: Optional[str] = None
    id: Optional[str] = None

    def upload(self) -> None:
        """Upload file to platform."""
        if self.id:
            raise ValueError("File already uploaded")

        url = f"{self.BASE_URL}files/contents/"
        with open(self.path, "rb") as file:
            response = requests.post(
                url,
                timeout=DEFAULT_TIMEOUT,
                files={"file": file},
                headers={"Authorization": f"Token {self.api_key}"},
            )
            result = self.parse_response(response)
            self.id = result["id"]

    @classmethod
    def load_from_id(cls, id: str) -> "File":
        """Create from existing file ID."""
        return cls(id=id)

@dataclass
class Software(ApiResponse):
    """Software configuration settings."""
    code: Optional[str] = None
    version: Optional[str] = None
    command: Optional[str] = None
    inputfiles: Optional[List[File]] = None
    lic: Optional[str] = None

    def get_available_softwares(self, page: int = 1) -> dict:
        """Get software options."""
        return self.send_get(f"analyses?page={page}")

    def upload_files(self) -> None:
        """Upload input files."""
        if self.inputfiles:
            for file in self.inputfiles:
                if not file.id:
                    file.upload()

    def to_json(self, hardware: Hardware) -> dict:
        """Convert to JSON format."""
        self.upload_files()
        return {
            "analysis": {
                "code": self.code,
                "version": self.version,
            },
            "command": self.command,
            "hardware": hardware.to_json(),
            "inputFiles": [{"id": file.id} for file in (self.inputfiles or [])],
            "envVars": {"LM_LICENSE_FILE": self.lic} if self.lic else {},
        }

@dataclass
class Abaqus(Software):
    """Abaqus-specific settings."""
    code: str = "abaqus"
    lic: str = "27101@SV10266"

    @staticmethod
    def get_version_code(name: str) -> str:
        """Convert version name to code."""
        codes = {
            "2024 HF4 (FlexNet Licensing)": "2024-hf4",
            "2023 HF9 (FlexNet Licensing)": "2023-hf9",
            "2023 HF4 (FlexNet Licensing)": "2023-hf4",
            "2023 HF2 (FlexNet Licensing)": "2023-HF2",
            "2023 HF1 (FlexNet Licensing)": "2023-HF1",
            "2023 Golden (FlexNet Licensing)": "2023-golden",
            "2022.HF9 (FlexNet Licensing)": "2022-2328",
            "2022.HF5 (FlexNet Licensing)": "2022-2241",
            "2022.HF4 (FlexNet Licensing)": "2022-2232",
            "2022.HF3 (FlexNet Licensing)": "2022-2223",
            "2022.HF1 (FlexNet Licensing)": "2022-2205",
            "2022 Golden (FlexNet Licensing)": "2022-golden",
            "2021.HF9 (FlexNet Licensing)": "2021-2140",
            "2021.HF6 (FlexNet Licensing)": "2021-2117",
            "2020.HF11 (FlexNet Licensing)": "2020-2136",
            "2020.HF6 (FlexNet Licensing)": "2020-2046",
            "2020.HF5 (FlexNet Licensing)": "2020-2038",
            "2020 Golden (FlexNet Licensing)": "2020",
            "2019.HF6 (FlexNet Licensing)": "2019-1947",
            "2019 (FlexNet Licensing)": "2019",
            "2018.HF10 (FlexNet Licensing)": "2018-1928",
            "2018 (FlexNet Licensing HF4)": "2018",
            "2017-efa-single-node": "2017-efa-single-node",
            "2017": "2017",
            "6.14-5": "6.14.5-pcmpi",
            "6.14-3": "6.14.3-pcmpi",
            "6.14-2": "6.14.2-pcmpi",
            "6.13-5": "6.13.5-ibm",
            "6.12-3": "6.12-3",
        }
        try:
            return codes[name]
        except KeyError as err:
            available_keys = ", ".join(codes.keys())
            raise KeyError(
                f"Key '{name}' not found! Available keys are: {available_keys}"
            ) from err

@dataclass
class Job(ApiResponse):
    """Job submission handler."""
    name: str
    hardware: Optional[Hardware]
    analyses: Optional[List[Software]]

    def create(self) -> None:
        """Create new job."""
        json_data = {
            "name": self.name,
            "jobanalyses": [
                analysis.to_json(self.hardware) for analysis in (self.analyses or [])
            ],
        }
        response = self.send_post("jobs/", json_data=json_data)
        self.id = response["id"]

    def submit(self) -> None:
        """Submit job for execution."""
        if not self.id:
            raise ValueError("Job must be created before submission")
        self.send_post(f"jobs/{self.id}/submit/")

    @classmethod
    def load_from_id(cls, id: str) -> "Job":
        """Create from existing job ID."""
        return cls(id=id)
