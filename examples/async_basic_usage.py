"""Basic asynchronous usage example for Animate 3D SDK.

This example demonstrates how to use the async client with callback pattern:
1. Start a new animation job
2. Receive progress updates via callback
3. Download results
"""

import asyncio
import os

from dm.animate3d import AsyncAnimate3DClient, ProcessParams, ResultCallbackData, ProgressCallbackData

# Configuration - replace with your credentials
API_SERVER_URL = "https://service.deepmotion.com"
CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"

# Test video path
VIDEO_PATH = "test.mp4"
OUTPUT_DIR = "./output"

client = AsyncAnimate3DClient(
    api_server_url=API_SERVER_URL,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
)


# Define callbacks
def on_progress(data: ProgressCallbackData):
    """Progress callback."""
    if data.position_in_queue:
        print(f"Position in queue: {data.position_in_queue})")
    else:
        print(f"Progress: {data.progress_percent}%")


async def on_result(data: ResultCallbackData):
    if data.result:
        print(f"Job completed successfully!")
        if data.result.output:
            print(f"Output file: {data.result.output}")
        print("Downloading results...")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        await client.download_job(data.rid, output_dir=OUTPUT_DIR)
    elif data.error:
        print(f"Job failed: {data.error.message} (Code: {data.error.code})")


async def main():
    # Check credit balance
    balance = await client.get_credit_balance()
    print(f"Credit balance: {balance}")

    if balance <= 0:
        print("Exception: No credit, cannot process job")
        return

    # Get a character model ID
    all_models = await client.list_character_models()
    if not all_models:
        print("Exception: No character models found which is required.")
        return

    model_id = all_models[0].id

    # Configure processing parameters
    params = ProcessParams(
        formats=["bvh", "fbx", "mp4"],
        model_id=model_id,
        track_face=1,
        track_hand=1,
    )

    print(f"\n=== Processing {VIDEO_PATH} ===")

    # Submit job (returns when finished because blocking=True is default)
    rid = await client.start_new_job(
        VIDEO_PATH,
        params=params,
        result_callback=on_result,
        progress_callback=on_progress,
    )
    print(f"Job finished, RID: {rid}")

    print("\n=== Done! ===")


if __name__ == "__main__":
    asyncio.run(main())
