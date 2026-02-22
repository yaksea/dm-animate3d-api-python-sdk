"""Character model management example.

This example demonstrates how to:
1. List available character models
2. Upload custom character models
3. Delete character models
"""

from dm.animate3d import Animate3DClient

# Configuration
API_SERVER_URL = "https://service.deepmotion.com"
CLIENT_ID = "your_client_id"
CLIENT_SECRET = "your_client_secret"


def main():
    client = Animate3DClient(
        api_server_url=API_SERVER_URL,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
    )

    # ========================================
    # List Character Models
    # ========================================
    print("=== Listing All Models ===")
    all_models = client.list_character_models()

    print("\nAll Models:")
    for model in all_models:
        print(f"  {model.name} (ID: {model.id}, Platform: {model.platform})")

    # ========================================
    # Upload Custom Character Model
    # ========================================
    print("\n=== Uploading Custom Model ===")

    # Example 1: Upload from local file
    model_id = client.upload_character_model(
        source="./test_character.glb",  # Local FBX file
        name="My Custom Character",  # Model name
    )
    print(f"Uploaded model ID: {model_id}")

    # ========================================
    # Delete Character Model
    # ========================================
    print("\n=== Deleting Model ===")

    # Delete a model by ID
    deleted_count = client.delete_character_model(model_id)
    print(f"Deleted {deleted_count} model(s)")

    # ========================================
    # Get Specific Model by ID
    # ========================================
    if all_models:
        print("\n=== Get Specific Model ===")
        first_model_id = all_models[0].id
        specific_models = client.list_character_models(model_id=first_model_id)
        if specific_models:
            model = specific_models[0]
            print(f"Model: {model.name}")
            print(f"  ID: {model.id}")
            print(f"  Platform: {model.platform}")
            print(f"  Rig ID: {model.rig_id}")
            if model.created_at:
                print(f"  Created: {model.created_at}")

    print("\n=== Done! ===")


if __name__ == "__main__":
    main()
