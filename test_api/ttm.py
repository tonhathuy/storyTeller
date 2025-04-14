import requests
import os
import json
invoke_url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"

headers = {
    "Authorization": "Bearer " + os.getenv("NGC_API_KEY"),
    "Accept": "application/json",
}

payload = {
    "text_prompts": [
        {
            "text": "underwater world, plants, shells, creatures, high detail, sharp focus, 4k",
            "weight": 1
        },
        {
            "text":  "" ,
            "weight": -1
        }
    ],
    "cfg_scale": 5,
    "sampler": "K_DPM_2_ANCESTRAL",
    "seed": 0,
    "steps": 25
}

response = requests.post(invoke_url, headers=headers, json=payload)

response.raise_for_status()
response_body = response.json()
# Save the image to a file
import base64
image_base64 = response_body['artifacts'][0]['base64']
image_path = "test_image.png"
with open(image_path, "wb") as f:
    f.write(base64.b64decode(image_base64))

print(f"Image saved to {image_path}")


