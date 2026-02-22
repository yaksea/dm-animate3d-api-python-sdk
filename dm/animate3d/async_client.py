"""Asynchronous client for Animate 3D API."""

import asyncio
import math
import os
from typing import List, Optional, Dict, Any, Callable, Union, Awaitable

import aiohttp
from aiohttp import BasicAuth

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


class AsyncAnimate3DClient:
    """Asynchronous client for Animate 3D REST API.

    This client provides an async interface to the Animate 3D API.
    It mirrors the synchronous client's structure but uses async/await.

    Example:
        async with AsyncAnimate3DClient(
            api_server_url="https://service.deepmotion.com",
            client_id="your_client_id",
            client_secret="your_client_secret",
        ) as client:
            params = ProcessParams(formats=["bvh", "fbx", "mp4"])

            def on_progress(data):
                print(f"Progress: {data.progress_percent}%")

            rid = await client.start_new_job(
                "video.mp4",
                params=params,
                progress_callback=on_progress
            )
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
            api_server_url: Base URL of the API server
            client_id: Client ID for authentication
            client_secret: Client secret for authentication
            timeout: Request timeout in seconds
        """
        self.api_server_url = api_server_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = aiohttp.ClientTimeout(total=timeout) if timeout else None
        self._session: Optional[aiohttp.ClientSession] = None
        self._authenticated = False
        self._auth = BasicAuth(client_id, client_secret)
        self._cookie_jar: Optional[aiohttp.CookieJar] = None

    async def _authenticate(self, session: aiohttp.ClientSession) -> None:
        """Authenticate and get session cookie."""
        auth_url = f"{self.api_server_url}/session/auth"

        try:
            async with session.get(auth_url) as response:
                response.raise_for_status()

                if "dmsess" in response.cookies:
                    self._authenticated = True
                else:
                    raise AuthenticationError("Failed to get session cookie")
        except aiohttp.ClientError as e:
            raise AuthenticationError(f"Authentication failed: {str(e)}") from e

    async def _request(
            self,
            method: str,
            path: str,
            params: Optional[Dict[str, Any]] = None,
            json_data: Optional[Dict[str, Any]] = None,
            data: Optional[bytes] = None,
            headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Make HTTP request to API.

        Returns:
            Parsed JSON response
        """
        url = f"{self.api_server_url}{path}"

        # If we have a managed session (via context manager), use it
        if self._session and not self._session.closed:
            if not self._authenticated:
                await self._authenticate(self._session)

            try:
                async with self._session.request(
                        method=method,
                        url=url,
                        params=params,
                        json=json_data,
                        data=data,
                        headers=headers,
                ) as response:
                    return await self._handle_response(response)
            except aiohttp.ClientError as e:
                raise APIError(f"Request failed: {str(e)}") from e
        else:
            # Lazy initialize cookie jar
            if self._cookie_jar is None:
                self._cookie_jar = aiohttp.CookieJar()

            # Otherwise create a temporary session but share cookies
            async with aiohttp.ClientSession(
                auth=self._auth,
                timeout=self.timeout,
                cookie_jar=self._cookie_jar,
                trust_env=True,
            ) as session:
                if not self._authenticated:
                    await self._authenticate(session)

                try:
                    async with session.request(
                            method=method,
                            url=url,
                            params=params,
                            json=json_data,
                            data=data,
                            headers=headers,
                    ) as response:
                        return await self._handle_response(response)
                except aiohttp.ClientError as e:
                    raise APIError(f"Request failed: {str(e)}") from e

    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle API response."""
        if response.status >= 400:
            error_msg = f"API request failed with status {response.status}"
            try:
                error_data = await response.json()
                if "message" in error_data:
                    error_msg = error_data["message"]
            except (ValueError, KeyError, aiohttp.ContentTypeError):
                pass

            raise APIError(error_msg, status_code=response.status)

        return await response.json()

    async def close(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None
            # Allow event loop to process connection cleanup (avoids "Event loop is closed"
            # on Windows when transports are GC'd after the loop has closed)
            await asyncio.sleep(0.25)

    def __del__(self):
        """Destructor to warn about unclosed session."""
        pass  # No longer critical as we handle temp sessions

    async def __aenter__(self):
        """Async context manager entry."""
        if self._cookie_jar is None:
            self._cookie_jar = aiohttp.CookieJar()

        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                auth=self._auth,
                timeout=self.timeout,
                cookie_jar=self._cookie_jar,
                trust_env=True,
            )
            self._authenticated = False
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    # ==================== Video Upload (Internal) ====================

    async def _upload_video(
            self, file_path: str, name: Optional[str] = None
    ) -> str:
        """Upload video file to GCS."""
        if not os.path.exists(file_path):
            raise ValidationError(f"File does not exist: {file_path}")

        if name is None:
            name = os.path.basename(file_path)

        params = {"name": name, "resumable": "0"}
        upload_data = await self._request("GET", "/upload", params=params)
        gcs_url = upload_data["url"]

        with open(file_path, "rb") as f:
            file_data = f.read()

        headers = {
            "Content-Length": str(len(file_data)),
            "Content-Type": "application/octet-stream",
        }

        async with aiohttp.ClientSession(timeout=self.timeout, trust_env=True) as temp_session:
            async with temp_session.put(
                    gcs_url, headers=headers, data=file_data
            ) as put_response:
                put_response.raise_for_status()

        return gcs_url

    async def _process_video(
            self,
            url: Optional[str] = None,
            rid: Optional[str] = None,
            rid_mp_detection: Optional[str] = None,
            params: Optional[ProcessParams] = None,
    ) -> str:
        """Start video processing."""
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

        result = await self._request("POST", "/process", json_data=process_data)
        return result["rid"]

    async def _poll_job(
        self,
        rid: str,
        result_callback: Optional[Callable[[ResultCallbackData], Optional[Awaitable[None]]]] = None,
        progress_callback: Optional[Callable[[ProgressCallbackData], Optional[Awaitable[None]]]] = None,
        poll_interval: int = 5,
        timeout: Optional[int] = None,
    ) -> None:
        """Poll job status until completion."""
        import time

        start_time = time.time()

        while True:
            job_status = await self.get_job_status(rid)

            if job_status.status == Status.PROGRESS:
                step = job_status.details.step if job_status.details and job_status.details.step else 0
                total = (
                    job_status.details.total if job_status.details and job_status.details.total else 100
                )
                percent = math.ceil((step / total) * 100) if total > 0 else 0
                queue_pos = job_status.position_in_queue

                if progress_callback:
                    data = ProgressCallbackData(
                        rid=rid,
                        progress_percent=percent,
                        position_in_queue=queue_pos,
                    )
                    if asyncio.iscoroutinefunction(progress_callback):
                        await progress_callback(data)
                    else:
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
                        print(f"Job failed: {job_status.details.exc_message}")
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
                    res = result_callback(data)
                    if asyncio.iscoroutine(res):
                        await res
                return

            if timeout and (time.time() - start_time) > timeout:
                raise TimeoutError(f"Job timed out after {timeout} seconds", rid=rid)

            await asyncio.sleep(poll_interval)

    # ==================== Character Model API ====================

    async def list_character_models(
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
            male_models = await client.list_character_models(search_token="male")

            # Include only custom models
            models = await client.list_character_models(only_custom=True)

        """
        params = {}
        if model_id:
            params["modelId"] = model_id
        if search_token:
            params["searchToken"] = search_token
        if not only_custom:
            params["stockModel"] = "all"

        data = await self._request("GET", "/character/listModels", params=params)

        characters = []
        if isinstance(data, list):
            for char_data in data:
                characters.append(CharacterModel.from_dict(char_data))
        elif "list" in data:
            for char_data in data["list"]:
                characters.append(CharacterModel.from_dict(char_data))

        return characters

    async def upload_character_model(
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
            model_id = await client.upload_character_model(
                source="./my_character.fbx",
                name="My Custom Character",
            )

            # Store from URL
            model_id = await client.upload_character_model(
                source="https://storage.example.com/model.fbx",
                name="Remote Character"
            )
        """
        if is_http_url(source):
            return await self._store_model(
                model_url=source,
                model_name=name or "Unnamed Model",
                create_thumb=create_thumb,
            )
        else:
            if not os.path.exists(source):
                raise ValidationError(f"Model file does not exist: {source}")

            if name is None:
                name = get_file_name_without_ext(source)

            model_ext = get_file_extension(source)

            # Get upload URLs
            upload_urls = await self._get_model_upload_url(name, model_ext)

            # Upload model file
            await self._upload_file_to_gcs(
                upload_urls["modelUrl"], source
            )

            return await self._store_model(
                model_url=upload_urls["modelUrl"],
                model_name=name,
                create_thumb=create_thumb,
            )

    async def _get_model_upload_url(
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

        return await self._request("GET", "/character/getModelUploadUrl", params=params)

    async def _upload_file_to_gcs(
            self, gcs_url: str, file_path: str
    ) -> None:
        """Upload file to GCS URL."""
        with open(file_path, "rb") as f:
            file_data = f.read()

        headers = {
            "Content-Length": str(len(file_data)),
            "Content-Type": "application/octet-stream",
        }

        async with aiohttp.ClientSession(timeout=self.timeout) as temp_session:
            async with temp_session.put(
                    gcs_url, headers=headers, data=file_data
            ) as put_response:
                put_response.raise_for_status()

    async def _store_model(
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

        result = await self._request(
            "POST", "/character/storeModel", json_data=store_data
        )
        return result["modelId"]

    async def start_new_job(
        self,
        video_path: str,
        params: Optional[ProcessParams] = None,
        name: Optional[str] = None,
        result_callback: Optional[Callable[[ResultCallbackData], Optional[Awaitable[None]]]] = None,
        progress_callback: Optional[Callable[[ProgressCallbackData], Optional[Awaitable[None]]]] = None,
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
            params: Processing parameters
            name: Optional video name
            result_callback: Callback for job completion (success or failure)
            progress_callback: Callback for progress updates
            poll_interval: Seconds between status polls
            blocking: Whether to block until job completes (default: True)
            timeout: Maximum wait time in seconds

        Returns:
            Request ID (rid)
        """
        # Upload video
        gcs_url = await self._upload_video(video_path, name=name)

        # Start processing
        rid = await self._process_video(url=gcs_url, params=params)

        # If callbacks provided, poll job
        if blocking or progress_callback is not None or result_callback is not None:
            if blocking:
                await self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                asyncio.create_task(self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                ))

        return rid

    # ==================== Job API (AsyncGenerator) ====================

    async def delete_character_model(self, model_id: str) -> int:
        """Delete a character model.

        Args:
            model_id: Model ID to delete

        Returns:
            Number of deleted models
        """
        data = await self._request("DELETE", f"/character/deleteModel/{model_id}")
        return data.get("count", 0)

    async def prepare_multi_person_job(
        self,
        video_path: str,
        name: Optional[str] = None,
        result_callback: Optional[Callable[[ResultCallbackData], Optional[Awaitable[None]]]] = None,
        progress_callback: Optional[Callable[[ProgressCallbackData], Optional[Awaitable[None]]]] = None,
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
        gcs_url = await self._upload_video(video_path, name=name)

        # Start detection
        params = ProcessParams()
        params._pipeline = "mp_detection"
        rid = await self._process_video(url=gcs_url, params=params)

        # If callbacks provided or blocking is True, poll job
        if blocking or progress_callback is not None or result_callback is not None:
            if blocking:
                await self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                asyncio.create_task(self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                ))

        return rid

    async def start_multi_person_job(
            self,
            rid_mp_detection: str,
            models: List[Dict[str, str]],
            params: Optional[ProcessParams] = None,
            result_callback: Optional[Callable[[ResultCallbackData], Optional[Awaitable[None]]]] = None,
            progress_callback: Optional[Callable[[ProgressCallbackData], Optional[Awaitable[None]]]] = None,
            poll_interval: int = 5,
            blocking: bool = True,
            timeout: Optional[int] = None,
    ) -> str:
        """Start multi-person animation processing.

        Args:
            rid_mp_detection: RID from prepare_multi_person_job()
            models: List of model assignments
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

        rid = await self._process_video(rid_mp_detection=rid_mp_detection, params=params)

        if progress_callback is not None or result_callback is not None:
            if blocking:
                await self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                asyncio.create_task(self._poll_job(
                    rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                ))

        return rid

    async def rerun_job(
        self,
        rid: str,
        params: Optional[ProcessParams] = None,
        result_callback: Optional[Callable[[ResultCallbackData], Optional[Awaitable[None]]]] = None,
        progress_callback: Optional[Callable[[ProgressCallbackData], Optional[Awaitable[None]]]] = None,
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
        new_rid = await self._process_video(rid=rid, params=params)

        # If callbacks provided or blocking is True, poll job
        if blocking or progress_callback is not None or result_callback is not None:
            if blocking:
                await self._poll_job(
                    new_rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                )
            else:
                asyncio.create_task(self._poll_job(
                    new_rid,
                    result_callback=result_callback,
                    progress_callback=progress_callback,
                    poll_interval=poll_interval,
                    timeout=timeout,
                ))

        return new_rid

    async def get_job_status(self, rid: str) -> JobStatus:
        """Get current status of a job.

        Args:
            rid: Request ID

        Returns:
            Job object with current status
        """
        data = await self._request("GET", f"/status/{rid}")

        if data.get("count", 0) > 0 and "status" in data:
            status_data = data["status"][0]
            return JobStatus.from_dict(status_data)

        return JobStatus(rid=rid, status=Status.PROGRESS)

    async def list_jobs(self, status: Optional[List[Status]] = None) -> List[Job]:
        """List jobs, optionally filtered by status.

        Args:
            status: List of statuses to filter (None for all jobs)

        Returns:
            List of Job objects
        """
        if status:
            status_str = ",".join([s.value for s in status])
            path = f"/list/{status_str}"
        else:
            path = "/list"

        data = await self._request("GET", path)

        jobs = []
        if "list" in data:
            for job_data in data["list"]:
                jobs.append(Job.from_dict(job_data))

        return jobs

    async def download_job(
            self, rid: str, output_dir: Optional[str] = None
    ) -> DownloadLink:
        """Download completed job results.

        Args:
            rid: Request ID
            output_dir: Directory to save files (if None, only returns URLs)

        Returns:
            DownloadLink object with file URLs
        """
        data = await self._request("GET", f"/download/{rid}")

        if data.get("count", 0) == 0:
            raise APIError(f"No download links found for rid {rid}")

        link_data = data["links"][0]
        download_link = DownloadLink.from_dict(link_data)

        if output_dir:
            await self._download_files(download_link, output_dir)

        return download_link

    async def _download_files(
            self, download_link: DownloadLink, output_dir: str
    ) -> int:
        """Download files from download link."""
        os.makedirs(output_dir, exist_ok=True)

        files_to_download = []
        for url_group in download_link.urls:
            name = url_group.name

            if ends_with_mp_tracked_id(name) or name.startswith("inter"):
                continue

            for file_info in url_group.files:
                file_type = file_info.file_type
                file_url = file_info.url

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

                files_to_download.append((file_url, output_file))

        if not files_to_download:
            return 0

        count = 0
        # Download with longer timeout
        download_timeout = aiohttp.ClientTimeout(total=3600)
        proxy_url = os.environ.get("HTTPS_PROXY") or os.environ.get("HTTP_PROXY")

        connector = aiohttp.TCPConnector(
            limit=10, force_close=True, enable_cleanup_closed=True
        )

        try:
            async with aiohttp.ClientSession(
                    timeout=download_timeout, connector=connector, trust_env=True
            ) as download_session:
                for file_url, output_file in files_to_download:
                    async with download_session.get(
                            file_url, proxy=proxy_url
                    ) as file_response:
                        file_response.raise_for_status()
                        file_data = await file_response.read()

                    with open(output_file, "wb") as f:
                        f.write(file_data)
                    count += 1
        finally:
            await connector.close()

        print(f"Downloaded {count} files to {output_dir}")
        return count

    # ==================== Account API ====================

    async def get_credit_balance(self) -> float:
        """Get account credit balance.

        Returns:
            Credit balance as float
        """
        data = await self._request("GET", "/account/creditBalance")
        return math.floor(data.get("credits", 0))
