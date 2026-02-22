"""Synchronous multi-person animation example.

This example demonstrates how to process a video with multiple persons:
1. Detect persons in the video (prepare_multi_person_job)
2. Assign character models to detected persons
3. Process animation for each person (start_multi_person_job)
"""
import os

from dm.animate3d import Animate3DClient, ProcessParams, Status, ResultCallbackData, ProgressCallbackData

# Configuration
API_SERVER_URL = "https://service.deepmotion.com"
CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"

# Test video
VIDEO_PATH = "multi_person.mp4"
OUTPUT_DIR = "./output/multi_person"

client = Animate3DClient(
    api_server_url=API_SERVER_URL,
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
)


def on_progress(data: ProgressCallbackData):
    """Progress callback."""
    if data.position_in_queue:
        print(f"Position in queue : {data.position_in_queue})")
    else:
        print(f"Progress: {data.progress_percent}%")


def on_result(data: ResultCallbackData):
    """Result callback."""
    if data.result:
        print(f"Job completed successfully!")
        print("Downloading results...")
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        client.download_job(data.rid, output_dir=OUTPUT_DIR)
    elif data.error:
        print(f"Job failed: {data.error.message} (Code: {data.error.code})")


def main():
    # Step 1: Detect persons
    print("Step 1: Detecting persons...")
    detection_rid = client.prepare_multi_person_job(
        VIDEO_PATH
    )

    # Check if detection succeeded
    job = client.get_job_status(detection_rid)
    if job.status != Status.SUCCESS:
        print(f"Detection failed: {job.status}")
        return

    # Step 2: Assign models
    print("\nStep 2: Assign models")
    all_models = client.list_character_models()
    if not all_models:
        print("No models found")
        return
    model_id = all_models[0].id
    models = [
        {"trackingId": "001", "modelId": model_id},
        {"trackingId": "002", "modelId": model_id},
    ]

    # Step 3: Process animation
    print("\nStep 3: Processing animation...")
    rid = client.start_multi_person_job(
        detection_rid,
        models=models,
        params=ProcessParams(formats=["bvh", "fbx"]),
        result_callback=on_result,
        progress_callback=on_progress,
    )

    print(f"Processing finished, RID: {rid}")


if __name__ == "__main__":
    main()
