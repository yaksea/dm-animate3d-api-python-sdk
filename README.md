# Animate 3D Python SDK

Python SDK for the Animate 3D REST API, providing both synchronous and asynchronous interfaces.

## Installation

```bash
pip install dm-animate3d-api
```

## Quick Start

### Synchronous Usage

```python
from dm.animate3d import Animate3DClient, ProcessParams

client = Animate3DClient(
    api_server_url="https://service.deepmotion.com",
    client_id="your_client_id",
    client_secret="your_client_secret",
)

# Check credit balance
balance = client.get_credit_balance()
print(f"Credit balance: {balance}")

# Get a character model
all_models = client.list_character_models()
model_id = all_models[0].id if all_models else None


# Callbacks
def on_progress(data):
    if data.position_in_queue:
        print(f"Position in queue: {data.position_in_queue})")
    else:
        print(f"Progress: {data.progress_percent}%")


def on_result(data):
    if data.result:
        print("Job completed successfully!")
        print(f"Output: {data.result.output}")
        # Download results
        client.download_job(data.rid, output_dir="./output")
    elif data.error:
        print(f"Job failed: {data.error.message}")


# Start job
if model_id:
    params = ProcessParams(
        formats=["bvh", "fbx", "mp4"],
        model_id=model_id,
        track_face=1,
        track_hand=1
    )

    print("Starting job...")
    # The call will block until the job finishes (or fails) by default
    rid = client.start_new_job(
        "video.mp4",
        params=params,
        result_callback=on_result,
        progress_callback=on_progress,
    )
    print(f"Job finished, RID: {rid}")
```

### Non-blocking Mode Usage

You can use the `blocking=False` parameter to make the SDK return immediately. This is useful for integration with GUIs or other event loops.

```python
# Start job in non-blocking mode
rid = client.start_new_job(
    "video.mp4",
    params=params,
    result_callback=on_result,
    progress_callback=on_progress,
    blocking=False  # Return immediately
)

# You must keep the main thread alive if using callbacks
import time
from dm.animate3d import Status
while True:
    status = client.get_job_status(rid).status
    if status in [Status.SUCCESS, Status.FAILURE]:
        break
    time.sleep(5)
```

### Asynchronous Usage

```python
import asyncio
from dm.animate3d import AsyncAnimate3DClient, ProcessParams


async def main():
    async with AsyncAnimate3DClient(
            api_server_url="https://service.deepmotion.com",
            client_id="your_client_id",
            client_secret="your_client_secret",
    ) as client:

        # Check credit balance
        balance = await client.get_credit_balance()
        print(f"Credit balance: {balance}")

        # Get a character model
        all_models = await client.list_character_models()
        model_id = all_models[0].id if all_models else None

        if not model_id:
            return

        params = ProcessParams(
            formats=["bvh", "fbx", "mp4"],
            model_id=model_id,
            track_face=1,
            track_hand=1
        )

        def on_progress(data):
            if data.position_in_queue:
                print(f"Position in queue: {data.position_in_queue})")
            else:
                print(f"Progress: {data.progress_percent}%")

        async def on_result(data):
            if data.result:
                print("Success!")
                await client.download_job(data.rid, output_dir="./output")
            elif data.error:
                print(f"Failed: {data.error.message}")

        # Start job
        rid = await client.start_new_job(
            "video.mp4",
            params=params,
            result_callback=on_result,
            progress_callback=on_progress
        )
        print(f"Job finished, RID: {rid}")


asyncio.run(main())
```

## API Reference

### Client Initialization

```python
# Synchronous client
client = Animate3DClient(
    api_server_url: str,      # API server URL
    client_id: str,           # Client ID
    client_secret: str,       # Client secret
    timeout: Optional[int],   # Request timeout in seconds
)

# Asynchronous client
async with AsyncAnimate3DClient(
    api_server_url: str,
    client_id: str,
    client_secret: str,
    timeout: Optional[int],
) as client:
    ...
```

### Character Model API

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `list_character_models` | model_id?, search_token?, only_custom? | List[CharacterModel] | List available models |
| `upload_character_model` | source, name?, create_thumb? | str (model_id) | Upload or store a model |
| `delete_character_model` | model_id | int (count) | Delete a model |

### Job API

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `start_new_job` | video_path, params?, name?, result_callback?, progress_callback?, poll_interval?, blocking?, timeout? | str (rid) | Start a new animation job |
| `prepare_multi_person_job` | video_path, name?, result_callback?, progress_callback?, poll_interval?, blocking?, timeout? | str (rid) | Detect persons in video |
| `start_multi_person_job` | rid_mp_detection, models, params?, result_callback?, progress_callback?, poll_interval?, blocking?, timeout? | str (rid) | Process multi-person animation |
| `rerun_job` | rid, params?, result_callback?, progress_callback?, poll_interval?, blocking?, timeout? | str (new_rid) | Rerun with different params |
| `get_job_status` | rid | JobStatus | Get current job status |
| `list_jobs` | status? | List[JobStatus] | List jobs by status |
| `download_job` | rid, output_dir? | DownloadLink | Download job results |

### Account API

| Method | Returns | Description |
|--------|---------|-------------|
| `get_credit_balance` | float | Get account credit balance |

## Callback Data Structures

### ProgressCallbackData

```python
@dataclass
class ProgressCallbackData:
    rid: str
    progress_percent: int
    position_in_queue: int
```

### ResultCallbackData

```python
@dataclass
class ResultCallbackData:
    rid: str
    result: Optional[JobResult] = None
    error: Optional[JobError] = None

@dataclass
class JobResult:
    input: List[str]
    output: Any

@dataclass
class JobError:
    code: str
    message: str
```

## Synchronous vs Asynchronous Design

| Feature | Synchronous | Asynchronous |
|---------|-------------|--------------|
| HTTP Library | requests | aiohttp |
| Progress Updates | callback function | callback function |
| Blocking | Controlled by `blocking` parameter (default: True) | Controlled by `blocking` parameter (default: True) |
| Batch Processing | Sequential or Manual Polling | Concurrent with asyncio |

## Usage Examples

See the `examples/` directory for complete usage examples:

- `sync_basic_usage.py` - Basic synchronous usage
- `sync_batch_usage.py` - Batch processing (sync)
- `sync_multiperson_usage.py` - Multi-person animation (sync)
- `async_basic_usage.py` - Basic asynchronous usage
- `async_batch_usage.py` - Concurrent batch processing (async)
- `async_multiperson_usage.py` - Multi-person animation (async)
- `character_model_usage.py` - Character model management
- `rerun_job_usage.py` - Rerunning jobs with different parameters

## ProcessParams Reference

```python
ProcessParams(
    # Output formats
    formats=["bvh", "fbx", "mp4", "glb"],
    
    # Character model (single person)
    model_id="model_id",
    
    # Tracking options
    track_face=1,                    # 0=off, 1=on
    track_hand=1,                    # 0=off, 1=on
    sim=1,                           # Physics simulation: 0=off, 1=on
    
    # Foot locking
    foot_locking_mode="auto",        # "auto", "always", "never", "grounding"
    
    # Video processing
    video_speed_multiplier=2.0,      # 1.0-8.0 for slow-motion videos
    pose_filtering_strength=0.5,     # 0.0-1.0, higher = smoother
    upper_body_only=False,           # Track upper body only
    root_at_origin=False,            # True to keep root at origin
    
    # Trim and crop
    trim=(1.0, 10.0),                # (start_sec, end_sec)
    crop=(0.1, 0.1, 0.9, 0.9),       # (left, top, right, bottom) normalized
    
    # MP4 rendering options
    render_sbs=0,                    # 0=character only, 1=side-by-side
    render_bg_color=(0, 177, 64, 0), # RGBA for green screen
    render_backdrop="studio",        # Background style
    render_shadow=1,                 # 0=off, 1=on
    render_include_audio=1,          # 0=off, 1=on
    render_cam_mode=0,               # 0=Cinematic, 1=Fixed, 2=Face
)
```

## Error Handling

```python
from dm.animate3d import (
    Animate3DError,      # Base exception
    AuthenticationError, # Authentication failed
    APIError,            # API call failed
    ValidationError,     # Input validation failed
    TimeoutError,        # Operation timed out
)

# Job errors are returned in the result callback via ResultCallbackData.error
def on_result(data):
    if data.error:
        print(f"Job failed: {data.error.message} (Code: {data.error.code})")
```

## Requirements

- Python 3.8+
- requests >= 2.28.0
- aiohttp >= 3.8.0

## License

MIT License

## Support

For issues and questions, please contact DeepMotion support.
