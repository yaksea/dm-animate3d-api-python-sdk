"""Synchronous client for Animate 3D API."""
import math
import os
import threading
import time
from typing import List, Optional, Dict, Any, Callable

import requests
from requests.auth import HTTPBasicAuth

from dm.animate3d.data.callback import (
    ProgressCallbackData,
    ResultCallbackData,
    JobResult,
    JobError,
)
from dm.animate3d.data.character import CharacterModel
from dm.animate3d.data.enums import Status
from dm.animate3d.data.job import Job
from dm.animate3d.data.job_status import JobStatus
from dm.animate3d.data.params import ProcessParams
from dm.animate3d.data.response import DownloadLink
from dm.animate3d.exceptions import (
    AuthenticationError,
    APIError,
    ValidationError,
    TimeoutError,
)
from dm.animate3d.utils import (
    ends_with_mp_tracked_id,
    is_http_url,
    get_file_extension,
    get_file_name_without_ext,
)


class Animate3DClient:
    """Synchronous client for Animate 3D REST API.

    This client provides a simple, blocking interface to the Animate 3D API.
    For async operations, use AsyncAnimate3DClient instead.

    Example:
        client = Animate3DClient(
            api_server_url="https://service.deepmotion.com",
            client_id="your_client_id",
            client_secret="your_client_secret",
        )

        # Start a new job
        rid = client.start_new_job("video.mp4", params=ProcessParams(formats=["bvh", "fbx"]))

        # Wait for completion with progress callback
        job = client.wait_for_job(rid, callback=lambda j: print(f"Progress: {j.details.step}"))

        # Download results
        client.download_job(rid, output_dir="./output")
    """

    def __init__(
            self,
            api_server_url: str,
            client_id: str,
            client_secret: str,
            timeout: Optional[int] = None,
    ):
        """Initialize the client.

        Args:
            api_server_url: Base URL of the API server (e.g., "https://service.deepmotion.com")
            client_id: Client ID for authentication
            client_secret: Client secret for authentication
            timeout: Request timeout in seconds (default: None, no timeout)
        """
        self.api_server_url = api_server_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self._session: Optional[requests.Session] = None
        self._authenticated = False

    def _get_session(self) -> requests.Session:
        """Get or create authenticated session."""
        if self._session is None:
            self._session = requests.Session()
            self._session.auth = HTTPBasicAuth(self.client_id, self.client_secret)
            self._authenticated = False

        if not self._authenticated:
            self._authenticate()

        return self._session

    def _authenticate(self) -> None:
        """Authenticate and get session cookie."""
        auth_url = f"{self.api_server_url}/session/auth"

        if self._session is None:
            self._session = requests.Session()
            self._session.auth = HTTPBasicAuth(self.client_id, self.client_secret)

        try:
            response = self._session.get(auth_url, timeout=self.timeout)
            response.raise_for_status()

            if "dmsess" in response.cookies:
                self._authenticated = True
            else:
                raise AuthenticationError("Failed to get session cookie")
        except requests.exceptions.RequestException as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}") from e

    def _request(
            self,
            method: str,
            path: str,
            params: Optional[Dict[str, Any]] = None,
            json_data: Optional[Dict[str, Any]] = None,
            data: Optional[bytes] = None,
            headers: Optional[Dict[str, str]] = None,
    ) -> requests.Response:
        """Make HTTP request to API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., "/upload")
            params: Query parameters
            json_data: JSON body data
            data: Raw body data
            headers: Additional headers

        Returns:
            Response object

        Raises:
            APIError: If request fails
        """
        url = f"{self.api_server_url}{path}"
        session = self._get_session()

        try:
            response = session.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                data=data,
                headers=headers,
                timeout=self.timeout,
            )

            if response.status_code >= 400:
                error_msg = f"API request failed with status {response.status_code}"
                content_type = response.headers.get("Content-Type", "")
                if "json" in content_type:
                    try:
                        error_data = response.json()
                        if "message" in error_data:
                            error_msg = error_data["message"]
                    except (ValueError, KeyError):
                        pass
                else:
                    body = response.text.strip()
                    if body:
                        error_msg += ": " + body

                raise APIError(error_msg, status_code=response.status_code)

            return response
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}") from e

    # ==================== Video Upload (Internal) ====================

    def _upload_video(
            self, file_path: str, name: Optional[str] = None
    ) -> str:
        """Upload video file to GCS.

        Args:
            file_path: Path to video file
            name: Optional file name (defaults to basename)

        Returns:
            GCS URL of uploaded file
        """
        if not os.path.exists(file_path):
            raise ValidationError(f"File does not exist: {file_path}")

        if name is None:
            name = os.path.basename(file_path)

        # Get upload URL
        params = {"name": name, "resumable": "0"}
        response = self._request("GET", "/upload", params=params)
        upload_data = response.json()
        gcs_url = upload_data["url"]

        # Upload file
        with open(file_path, "rb") as f:
            file_data = f.read()

        headers = {
            "Content-Length": str(len(file_data)),
            "Content-Type": "application/octet-stream",
        }

        put_response = requests.put(
            gcs_url, headers=headers, data=file_data, timeout=self.timeout
        )

        put_response.raise_for_status()
        return gcs_url

    def _process_video(
            self,
            url: Optional[str] = None,
            rid: Optional[str] = None,
            rid_mp_detection: Optional[str] = None,
            params: Optional[ProcessParams] = None,
    ) -> str:
        """Start video processing.

        Args:
            url: GCS URL of uploaded video
            rid: Previous job RID (for rerun)
            rid_mp_detection: Multi-person detection RID
            params: Process parameters

        Returns:
            Request ID (rid)
        """
        if params is None:
            params = ProcessParams()

        process_data = {
            "processor": "video2anim",
            "params": params.to_params_list(),
        }

        if url:
            process_data["url"] = url
        if rid:
            process_data["rid"] = rid
        if rid_mp_detection:
            process_data["rid_mp_detection"] = rid_mp_detection

        response = self._request("POST", "/process", json_data=process_data)
        result = response.json()
        return result["rid"]

    # ==================== Character Model API ====================

    def list_character_models(
            self,
            model_id: Optional[str] = None,
            search_token: Optional[str] = None,
            only_custom: Optional[bool] = None,
    ) -> List[CharacterModel]:
        """List character models.

        Args:
            model_id: Specific model ID to retrieve
            search_token: Search by model name
            only_custom: Include only custom models

        Returns:
            List of CharacterModel objects

        Example:
            # Search for models by name
            male_models = client.list_character_models(search_token="male")

            # Include only custom models
            models = client.list_character_models(only_custom=True)

        """
        params = {}
        if model_id:
            params["modelId"] = model_id
        if search_token:
            params["searchToken"] = search_token
        if not only_custom:
            params["stockModel"] = "all"

        response = self._request("GET", "/character/listModels", params=params)
        data = response.json()

        characters = []
        if isinstance(data, list):
            for char_data in data:
                characters.append(CharacterModel.from_dict(char_data))
        elif "list" in data:
            for char_data in data["list"]:
                characters.append(CharacterModel.from_dict(char_data))

        return characters

    def upload_character_model(
            self,
            source: str,
            name: Optional[str] = None,
            create_thumb: bool = False,
    ) -> str:
        """Upload or store a character model.

        This method intelligently handles both local files and HTTP URLs:
        - Local file: Uploads to GCS, then stores in database
        - HTTP URL: Directly stores in database

        Args:
            source: Local file path or HTTP URL of the model
            name: Model name (defaults to filename for local files)
            create_thumb: Whether to auto-generate thumbnail

        Returns:
            Model ID

        Example:
            # Upload local file
            model_id = client.upload_character_model(
                source="./my_character.fbx",
                name="My Custom Character",
                thumb_source="./thumbnail.png"
            )

            # Store from URL
            model_id = client.upload_character_model(
                source="https://storage.example.com/model.fbx",
                name="Remote Character"
            )
        """
        if is_http_url(source):
            # HTTP URL: directly store
            return self._store_model(
                model_url=source,
                model_name=name or "Unnamed Model",
                create_thumb=create_thumb,
            )
        else:
            # Local file: upload then store
            if not os.path.exists(source):
                raise ValidationError(f"Model file does not exist: {source}")

            if name is None:
                name = get_file_name_without_ext(source)

            model_ext = get_file_extension(source)

            # Get upload URLs
            upload_urls = self._get_model_upload_url(name, model_ext)

            # Upload model file
            self._upload_file_to_gcs(
                upload_urls["modelUrl"], source
            )

            return self._store_model(
                model_url=upload_urls["modelUrl"],
                model_name=name,
                create_thumb=create_thumb,
            )

    def _get_model_upload_url(
            self,
            name: str,
            model_ext: str,
    ) -> Dict[str, str]:
        """Get signed URLs for model upload."""
        params = {
            "name": name,
            "modelExt": model_ext,
            "resumable": "0",
        }

        response = self._request("GET", "/character/getModelUploadUrl", params=params)
        return response.json()

    def _upload_file_to_gcs(
            self, gcs_url: str, file_path: str
    ) -> None:
        """Upload file to GCS URL."""
        with open(file_path, "rb") as f:
            file_data = f.read()

        headers = {
            "Content-Length": str(len(file_data)),
            "Content-Type": "application/octet-stream",
        }

        put_response = requests.put(
            gcs_url, headers=headers, data=file_data, timeout=self.timeout
        )

        put_response.raise_for_status()

    def _store_model(
            self,
            model_url: str,
            model_name: str,
            thumb_url: Optional[str] = None,
            model_id: Optional[str] = None,
            create_thumb: bool = False,
    ) -> str:
        """Store model in database."""
        store_data = {
            "modelUrl": model_url,
            "modelName": model_name,
        }

        if thumb_url:
            store_data["thumbUrl"] = thumb_url
        if model_id:
            store_data["modelId"] = model_id
        if create_thumb:
            store_data["createThumb"] = 1

        response = self._request("POST", "/character/storeModel", json_data=store_data)
        result = response.json()
        return result["modelId"]

    def delete_character_model(self, model_id: str) -> int:
        """Delete a character model.

        Args:
            model_id: Model ID to delete

        Returns:
            Number of deleted models

        Example:
            deleted_count = client.delete_character_model("model_id_here")
        """
        response = self._request("DELETE", f"/character/deleteModel/{model_id}")
        data = response.json()
        return data.get("count", 0)

    # ==================== Job API ====================

    def start_new_job(
            self,
            video_path: str,
            params: Optional[ProcessParams] = None,
            name: Optional[str] = None,
            result_callback: Optional[Callable[[ResultCallbackData], None]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], None]] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        """Start a new animation job.

        This method uploads the video and starts processing in one step.
        If result_callback or progress_callback is provided, it will wait for the job to complete
        if blocking is True (default: True).

        Args:
            video_path: Path to video file
            params: Processing parameters (see ProcessParams)
            name: Optional video name (defaults to filename)
            result_callback: Callback for job completion (success or failure)
            progress_callback: Callback for progress updates
            poll_interval: Seconds between status polls (default: 5)
            blocking: Whether to block until job completes (default: True)
            timeout: Maximum wait time in seconds (only used with callbacks)

        Returns:
            Request ID (rid)
        """
        # Upload video
        gcs_url = self._upload_video(video_path, name=name)

        # Start processing
        rid = self._process_video(url=gcs_url, params=params)

        # If callbacks provided or blocking is True, poll job
        if blocking or progress_callback is not None or result_callback is not None:
            if blocking:
                self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                thread = threading.Thread(
                    target=self._poll_job,
                    args=(rid,),
                    kwargs={
                        "result_callback": result_callback,
                        "progress_callback": progress_callback,
                        "poll_interval": poll_interval,
                        "timeout": timeout,
                    },
                    daemon=True,
                )
                thread.start()

        return rid

    def prepare_multi_person_job(
            self,
            video_path: str,
            name: Optional[str] = None,
            result_callback: Optional[Callable[[ResultCallbackData], None]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], None]] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        """Prepare a multi-person job by detecting persons in video.

        This uploads the video and runs person detection. The returned RID
        is used with start_multi_person_job() to process the detected persons.

        Args:
            video_path: Path to video file
            name: Optional video name
            result_callback: Callback for job completion
            progress_callback: Callback for progress updates
            poll_interval: Seconds between status polls
            blocking: Whether to block until job completes (default: True)
            timeout: Maximum wait time in seconds

        Returns:
            Detection job RID (use with start_multi_person_job)
        """
        # Upload video
        gcs_url = self._upload_video(video_path, name=name)

        # Start detection
        params = ProcessParams()
        params._pipeline = "mp_detection"
        rid = self._process_video(url=gcs_url, params=params)

        # If callbacks provided, poll job
        if blocking or progress_callback is not None or result_callback is not None:
            if blocking:
                self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                thread = threading.Thread(
                    target=self._poll_job,
                    args=(rid,),
                    kwargs={
                        "result_callback": result_callback,
                        "progress_callback": progress_callback,
                        "poll_interval": poll_interval,
                        "timeout": timeout,
                    },
                    daemon=True,
                )
                thread.start()

        return rid

    def start_multi_person_job(
            self,
            rid_mp_detection: str,
            models: List[Dict[str, str]],
            params: Optional[ProcessParams] = None,
            result_callback: Optional[Callable[[ResultCallbackData], None]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], None]] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        """Start multi-person animation processing.

        Uses the detection results from prepare_multi_person_job() to process
        animation for each detected person.

        Args:
            rid_mp_detection: RID from prepare_multi_person_job()
            models: List of model assignments, each dict has:
                    - "trackingId": Person ID from detection (e.g., "001")
                    - "modelId": Character model ID to use
            params: Processing parameters
            result_callback: Callback for job completion
            progress_callback: Callback for progress updates
            poll_interval: Seconds between status polls
            blocking: Whether to block until job completes (default: True)
            timeout: Maximum wait time in seconds

        Returns:
            Processing job RID
        """
        if params is None:
            params = ProcessParams()
        else:
            params = params.copy()

        params._models = models

        rid = self._process_video(rid_mp_detection=rid_mp_detection, params=params)

        if progress_callback is not None or result_callback is not None:
            if blocking:
                self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                thread = threading.Thread(
                    target=self._poll_job,
                    args=(rid,),
                    kwargs={
                        "result_callback": result_callback,
                        "progress_callback": progress_callback,
                        "poll_interval": poll_interval,
                        "timeout": timeout,
                    },
                    daemon=True,
                )
                thread.start()

        return rid

    def rerun_job(
            self,
            rid: str,
            params: Optional[ProcessParams] = None,
            result_callback: Optional[Callable[[ResultCallbackData], None]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], None]] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        """Rerun a previous job with different parameters.

        Args:
            rid: Previous job's RID
            params: New processing parameters
            result_callback: Callback for job completion
            progress_callback: Callback for progress updates
            poll_interval: Seconds between status polls
            blocking: Whether to block until job completes (default: True)
            timeout: Maximum wait time in seconds

        Returns:
            New job RID
        """
        new_rid = self._process_video(rid=rid, params=params)

        # If callbacks provided or blocking is True, poll job
        if blocking or progress_callback is not None or result_callback is not None:
            if blocking:
                self._poll_job(
                    new_rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                thread = threading.Thread(
                    target=self._poll_job,
                    args=(new_rid,),
                    kwargs={
                        "result_callback": result_callback,
                        "progress_callback": progress_callback,
                        "poll_interval": poll_interval,
                        "timeout": timeout,
                    },
                    daemon=True,
                )
                thread.start()

        return new_rid

    def _poll_job(
            self,
            rid: str,
            result_callback: Optional[Callable[[ResultCallbackData], None]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], None]] = None,
            poll_interval: int = 5,
            timeout: Optional[int] = None,
    ) -> None:
        """Poll job status until completion."""
        start_time = time.time()

        while True:
            job_status = self.get_job_status(rid)

            if job_status.status == Status.PROGRESS:
                step = job_status.details.step if job_status.details and job_status.details.step else 0
                total = (
                    job_status.details.total if job_status.details and job_status.details.total else 100
                )
                percent = math.ceil((step / total) * 100) if total > 0 else 0
                # Queue position is not currently available in JobStatus, defaulting to 0
                queue_pos = job_status.position_in_queue

                if progress_callback:
                    data = ProgressCallbackData(
                        rid=rid,
                        progress_percent=percent,
                        position_in_queue=queue_pos,
                    )
                    progress_callback(data)
                else:
                    if queue_pos:
                        print(f"Position in queue: {queue_pos})")
                    else:
                        print(f"Progress: {percent}%")

            if job_status.status in (Status.SUCCESS, Status.FAILURE):
                if not result_callback:
                    if job_status.status == Status.SUCCESS:
                        print("Job completed successfully!")
                    else:
                        f"Job failed: {job_status.details.exc_message}"
                else:
                    result_data = None
                    error_data = None

                    if job_status.status == Status.SUCCESS:
                        inp = (
                            [job_status.details.input_file]
                            if job_status.details and job_status.details.input_file
                            else []
                        )
                        out = job_status.details.output_file if job_status.details else None
                        result_data = JobResult(input=inp, output=out)
                    else:
                        code = job_status.details.exc_type if job_status.details else "Unknown"
                        msg = (
                            job_status.details.exc_message
                            if job_status.details
                            else "Unknown error"
                        )
                        error_data = JobError(code=code, message=msg)

                    data = ResultCallbackData(
                        rid=rid, result=result_data, error=error_data
                    )
                    result_callback(data)
                return

            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Job timed out after {timeout} seconds", rid=rid)

            time.sleep(poll_interval)

    def get_job_status(self, rid: str) -> JobStatus:
        """Get current status of a job.

        Args:
            rid: Request ID

        Returns:
            JobStatus object with current status

        Example:
            job = client.get_job_status("some_rid")
            print(f"Status: {job.status}")
            if job.details and job.details.step:
                print(f"Progress: {job.details.step}/{job.details.total}")
        """
        response = self._request("GET", f"/status/{rid}")
        data = response.json()

        if data.get("count", 0) > 0 and "status" in data:
            status_data = data["status"][0]
            return JobStatus.from_dict(status_data)

        return JobStatus(rid=rid, status=Status.PROGRESS)

    def list_jobs(self, status: Optional[List[Status]] = None) -> List[Job]:
        """List jobs, optionally filtered by status.

        Args:
            status: List of statuses to filter (None for all jobs)

        Returns:
            List of Job objects

        Example:
            # List all jobs in progress
            progress_jobs = client.list_jobs(status=[Status.PROGRESS])

            # List all completed jobs
            success_jobs = client.list_jobs(status=[Status.SUCCESS])

            # List all jobs
            all_jobs = client.list_jobs()
        """
        if status:
            status_str = ",".join([s.value for s in status])
            path = f"/list/{status_str}"
        else:
            path = "/list"

        response = self._request("GET", path)
        data = response.json()

        jobs = []
        if "list" in data:
            for job_data in data["list"]:
                jobs.append(Job.from_dict(job_data))

        return jobs

    def download_job(
            self, rid: str, output_dir: Optional[str] = None
    ) -> DownloadLink:
        """Download completed job results.

        Args:
            rid: Request ID
            output_dir: Directory to save files (if None, only returns URLs)

        Returns:
            DownloadLink object with file URLs

        Example:
            # Just get download URLs
            download_link = client.download_job(rid)
            for url_group in download_link.urls:
                for file in url_group.files:
                    print(f"{file.file_type}: {file.url}")

            # Download to directory
            download_link = client.download_job(rid, output_dir="./output")
        """
        response = self._request("GET", f"/download/{rid}")
        data = response.json()

        if data.get("count", 0) == 0:
            raise APIError(f"No download links found for rid {rid}")

        link_data = data["links"][0]
        download_link = DownloadLink.from_dict(link_data)

        if output_dir:
            self._download_files(download_link, output_dir)

        return download_link

    def _download_files(self, download_link: DownloadLink, output_dir: str) -> int:
        """Download files from download link."""
        os.makedirs(output_dir, exist_ok=True)

        session = self._get_session()

        count = 0
        for url_group in download_link.urls:
            name = url_group.name

            # Skip intermediate files and MP tracked IDs
            if ends_with_mp_tracked_id(name) or name.startswith("inter"):
                continue

            for file_info in url_group.files:
                file_type = file_info.file_type
                file_url = file_info.url

                # Determine output filename
                if name == "all_characters":
                    output_file = os.path.join(
                        output_dir, f"{download_link.rid}-{name}.{file_type}.zip"
                    )
                elif file_type == "mp4":
                    output_file = os.path.join(
                        output_dir, f"{download_link.rid}-{name}.{file_type}"
                    )
                else:
                    output_file = os.path.join(
                        output_dir, f"{download_link.rid}-{name}.{file_type}.zip"
                    )

                # Download file
                file_response = session.get(file_url, timeout=self.timeout)
                file_response.raise_for_status()

                with open(output_file, "wb") as f:
                    f.write(file_response.content)
                count += 1

        print(f"Downloaded {count} files to {output_dir}")
        return count

    # ==================== Account API ====================

    def get_credit_balance(self) -> float:
        """Get account credit balance.

        Returns:
            Credit balance as float

        Example:
            balance = client.get_credit_balance()
            print(f"Current balance: {balance}")
        """
        response = self._request("GET", "/account/creditBalance")
        data = response.json()
        return math.floor(data.get("credits", 0))
