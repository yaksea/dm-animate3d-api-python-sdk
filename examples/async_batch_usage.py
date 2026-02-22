"""Async batch job submission example.

This example demonstrates how to:
1. Submit multiple jobs without waiting
2. Wait for all jobs to complete
"""

import asyncio
import os

from dm.animate3d import AsyncAnimate3DClient, ProcessParams, ResultCallbackData, ProgressCallbackData

# Configuration
API_SERVER_URL = "https://service.deepmotion.com"
CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"

done_job_count = 0


# Define callbacks
def on_progress(data: ProgressCallbackData):
    """Progress callback."""
    if data.position_in_queue:
        print(f"Position of Job[{data.rid}] in queue : {data.position_in_queue})")
    else:
        print(f"Progress of Job[{data.rid}]: {data.progress_percent}%")


def on_result(data: ResultCallbackData):
    """Result callback."""
    if data.result:
        print(f"Job[{data.rid}] completed successfully!")
    elif data.error:
        print(f"Job[{data.rid}] failed: {data.error.message} (Code: {data.error.code})")

    global done_job_count
    done_job_count += 1


async def main():
    async with AsyncAnimate3DClient(
            api_server_url=API_SERVER_URL,
            client_id=CLIENT_ID,
            client_secret=CLIENT_SECRET,
    ) as client:
        # Get a character model ID
        all_models = await client.list_character_models()
        if not all_models:
            print("No models found")
            return
        model_id = all_models[0].id

        # Video files to process
        video_files = ["test.mp4", "test.mp4", "test.mp4", ]

        # Processing parameters
        params = ProcessParams(formats=["bvh", "fbx"], model_id=model_id, )

        # Step 1: Submit all jobs (without callback = no waiting)
        # Note: In async client, blocking=False with callbacks will spawn a background task for polling.
        print("=== Submitting jobs ===")
        rids = []
        for video in video_files:
            if not os.path.exists(video):
                print(f"Skipping {video} (file not found)")
                continue

            # start_new_job is awaitable because it performs I/O (upload/start)
            rid = await client.start_new_job(
                video,
                params=params,
                progress_callback=on_progress,
                result_callback=on_result,
                poll_interval=10,
                blocking=False
            )
            rids.append((video, rid))
            print(f"Submitted: {video} -> Job ID: {rid}")

        while done_job_count < len(rids):
            await asyncio.sleep(3)

        print("\n=== All jobs processed ===")


if __name__ == "__main__":
    asyncio.run(main())
