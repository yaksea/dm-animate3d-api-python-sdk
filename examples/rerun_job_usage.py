"""Rerun job example.

This example demonstrates how to rerun a previous job with different parameters.
"""

from dm.animate3d import Animate3DClient, ProcessParams, ProgressCallbackData, ResultCallbackData

# Configuration
API_SERVER_URL = "https://service.deepmotion.com"
CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"

OUTPUT_DIR = "./output/rerun"


# Define callbacks
def on_progress(data: ProgressCallbackData):
    """Progress callback."""
    if data.position_in_queue:
        print(f"Position in queue: {data.position_in_queue})")
    else:
        print(f"Progress: {data.progress_percent}%")


def on_result(data: ResultCallbackData):
    """Result callback."""
    if data.result:
        print(f"Job completed successfully!")
        if data.result.output:
            print(f"Output file: {data.result.output}")
    elif data.error:
        print(f"Job failed: {data.error.message} (Code: {data.error.code})")


def main():
    client = Animate3DClient(
        api_server_url=API_SERVER_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )

    jobs = client.list_jobs()
    if not len(jobs):
        print("No job to rerun")
        return
    # 1. Start initial job (mock)
    print("Starting initial job...")
    rid = jobs[0].rid
    print(f"Initial job RID: {rid}")

    # 2. Rerun with new parameters (e.g., enable face tracking)
    print("\nRerunning job with new parameters...")
    all_models = client.list_character_models()
    if not all_models:
        print("No models found")
        return
    model_id = all_models[0].id
    new_params = ProcessParams(
        model_id=model_id,  # required
        formats=["fbx", "glb"],
        track_face=1,
    )

    try:
        new_rid = client.rerun_job(
            rid,
            params=new_params,
            result_callback=on_result,
            progress_callback=on_progress,
        )
        print(f"Job finished, RID: {new_rid}")

    except Exception as e:
        print(f"Error rerunning job: {e}")
        print("Note: This example requires a valid RID from a previous job.")


if __name__ == "__main__":
    main()
