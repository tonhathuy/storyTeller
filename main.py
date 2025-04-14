import os
import json
import re
import base64
import requests
import argparse
import shutil
from openai import OpenAI
from google.cloud import texttospeech as tts
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Có thể thư viện MoviePy chưa được cài đặt đúng cách, thêm xử lý try-except cho việc import
try:
    # Thử cách import khác theo gợi ý
    from moviepy import *
    from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips, concatenate_audioclips, CompositeAudioClip
    has_moviepy = True
except ImportError:
    print("Warning: MoviePy not available. Video generation will be disabled.")
    print("Try installing MoviePy with: pip install moviepy")
    has_moviepy = False

# Đường dẫn đến file JSON quản lý stories
STORIES_DB_PATH = "stories.json"

def load_stories_db():
    """
    Load the stories database from JSON file.
    
    Returns:
        Dictionary of stories indexed by ID
    """
    if os.path.exists(STORIES_DB_PATH):
        with open(STORIES_DB_PATH, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                # Check if the data is already a dictionary with story_id keys
                if "story_id" in data:
                    # Convert to proper format: {story_id: data}
                    return {data["story_id"]: data}
                return data
            except json.JSONDecodeError:
                print(f"Error parsing {STORIES_DB_PATH}. Creating a new database.")
                return {}
    return {}

def save_stories_db(stories_db):
    """
    Save the stories database to JSON file.
    
    Args:
        stories_db: Dictionary of stories indexed by ID
    """
    with open(STORIES_DB_PATH, 'w', encoding='utf-8') as f:
        json.dump(stories_db, f, ensure_ascii=False, indent=2)

def get_story_by_id(story_id):
    """
    Get story configuration by ID.
    
    Args:
        story_id: ID of the story
        
    Returns:
        Story configuration or None if not found
    """
    stories_db = load_stories_db()
    return stories_db.get(story_id)

def add_or_update_story(story_config):
    """
    Add or update a story in the database.
    
    Args:
        story_config: Story configuration dictionary
        
    Returns:
        Updated stories database
    """
    stories_db = load_stories_db()
    stories_db[story_config["story_id"]] = story_config
    save_stories_db(stories_db)
    return stories_db

def set_api_key(api_key):
    """
    Set the API key for the OpenAI client.
    
    Args:
        api_key: The API key to use
        
    Returns:
        None
    """
    os.environ["OPENAI_API_KEY"] = api_key

def load_prompt(prompt_path):
    """
    Load a prompt file.
    
    Args:
        prompt_path: Path to the prompt file
    
    Returns:
        The content of the prompt file as a string
    """
    try:
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

def load_story(story_path):
    """
    Load the content of a story file.
    
    Args:
        story_path: Path to the story file
        
    Returns:
        The content of the story file as a string
    """
    try:
        with open(story_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Story file not found: {story_path}")

def load_full_prompt(prompt_path, story_path):
    """
    Load a prompt and populate it with the story content.
    
    Args:
        prompt_path: Path to the prompt file
        story_path: Path to the story file
        
    Returns:
        The populated prompt as a string
    """
    prompt_template = load_prompt(prompt_path)
    story_content = load_story(story_path)
    
    # Replace the placeholder with the actual story content
    full_prompt = prompt_template.replace("[PASTE YOUR STORY HERE]", story_content)
    
    return full_prompt

def extract_json_array(text):
    """
    Extract a JSON array from text.
    
    Args:
        text: Text that may contain a JSON array
        
    Returns:
        Extracted JSON array as string or None if not found
    """
    # Look for array pattern with balanced brackets
    pattern = r'\[\s*{.*}\s*\]'
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(0)
        
    # If not found, try finding the first [ and last ]
    start_idx = text.find('[')
    end_idx = text.rfind(']')
    
    if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
        return text[start_idx:end_idx+1]
        
    return None

def prompt_to_json(prompt_content, cached_llm_path=None, model="meta/llama-3.1-405b-instruct", temperature=0.2, max_tokens=4096, debug=False):
    """
    Send the prompt to the LLM API and get the JSON result.
    
    Args:
        prompt_content: The complete prompt to send to the LLM
        cached_llm_path: Path to the cached LLM response
        model: The LLM model to use
        temperature: The temperature parameter for the LLM
        max_tokens: The maximum number of tokens to generate
        debug: Whether to print debug information
        
    Returns:
        The JSON response from the LLM as a Python dictionary
    """
    # If cache_file is provided and exists, load from it
    if cached_llm_path and os.path.exists(cached_llm_path):
        if debug:
            print(f"Loading cached LLM response from {cached_llm_path}")
        with open(cached_llm_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    try:
        # Check if NGC_API_KEY exists, otherwise try OPENAI_API_KEY
        api_key = os.getenv("NGC_API_KEY")
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("API key not found. Please set either NGC_API_KEY or OPENAI_API_KEY environment variable.")
        
        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=api_key
        )
        
        # Đầu tiên, tạo completion không stream để lấy kết quả hoàn chỉnh
        completion = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt_content}],
            temperature=temperature,
            top_p=0.7,
            max_tokens=max_tokens,
            stream=False  # Không sử dụng stream để lấy kết quả hoàn chỉnh
        )
        
        response_text = completion.choices[0].message.content
        
        # Nếu debug mode, hiển thị kết quả theo từng chunk
        if debug:
            print("\n--- DEBUG: GENERATING RESPONSE STREAMING ---")
            # Tạo một lần nữa với stream=True chỉ để hiển thị
            stream_completion = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt_content}],
                temperature=temperature,
                top_p=0.7,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in stream_completion:
                if chunk.choices[0].delta.content is not None:
                    print(chunk.choices[0].delta.content, end="")
            print("\n--- END STREAMING ---\n")
        
        if debug:
            print("\n--- DEBUG: RAW API RESPONSE ---")
            print(response_text)
            print("--- END RAW RESPONSE ---\n")
        
        # Parse the response text as JSON
        try:
            # First try direct JSON parsing
            response_json = json.loads(response_text)
            
            # Save to cache if path is provided
            if cached_llm_path:
                # Ensure directory exists
                os.makedirs(os.path.dirname(cached_llm_path), exist_ok=True)
                with open(cached_llm_path, 'w', encoding='utf-8') as f:
                    json.dump(response_json, f, ensure_ascii=False, indent=2)
                    
            return response_json
        except json.JSONDecodeError:
            if debug:
                print("Direct JSON parsing failed. Trying to extract JSON array...")
            
            # Extract JSON array from text
            json_text = extract_json_array(response_text)
            
            if debug and json_text:
                print("\n--- DEBUG: EXTRACTED JSON ---")
                print(json_text)
                print("--- END EXTRACTED JSON ---\n")
            
            if json_text:
                try:
                    response_json = json.loads(json_text)
                    
                    # Save to cache if path is provided
                    if cached_llm_path:
                        # Ensure directory exists
                        os.makedirs(os.path.dirname(cached_llm_path), exist_ok=True)
                        with open(cached_llm_path, 'w', encoding='utf-8') as f:
                            json.dump(response_json, f, ensure_ascii=False, indent=2)
                            
                    return response_json
                except json.JSONDecodeError as e:
                    if debug:
                        print(f"JSON parsing error: {str(e)}")
                    raise ValueError("Could not parse extracted JSON from the LLM response")
            else:
                raise ValueError("Could not find JSON array in the LLM response")
            
    except Exception as e:
        raise Exception(f"Error calling LLM API: {str(e)}")

def prompt_to_image(image_prompt, output_path, negative_prompt="", cfg_scale=5, steps=25, seed=0, debug=False):
    """
    Generate an image from a text prompt using Stable Diffusion XL.
    
    Args:
        image_prompt: Text description for image generation
        output_path: Path to save the generated image
        negative_prompt: Negative prompt to guide what not to include
        cfg_scale: Guidance scale for image generation
        steps: Number of diffusion steps
        seed: Random seed for reproducibility
        debug: Whether to print debug information
        
    Returns:
        True if image was generated successfully, False otherwise
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Check for API key
        api_key = os.getenv("NGC_API_KEY")
        if not api_key:
            raise ValueError("NGC_API_KEY environment variable not set")
        
        # API endpoint
        invoke_url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl"
        
        # Headers
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }
        
        # Payload
        payload = {
            "text_prompts": [
                {
                    "text": image_prompt,
                    "weight": 1
                },
                {
                    "text": negative_prompt,
                    "weight": -1
                }
            ],
            "cfg_scale": cfg_scale,
            "sampler": "K_DPM_2_ANCESTRAL",
            "seed": seed,
            "steps": steps
        }
        
        if debug:
            print(f"\n--- DEBUG: GENERATING IMAGE FOR PROMPT ---")
            print(f"Prompt: {image_prompt}")
            print(f"Output path: {output_path}")
            print("--- END DEBUG INFO ---\n")
        
        # Send request
        response = requests.post(invoke_url, headers=headers, json=payload)
        response.raise_for_status()
        
        # Parse response
        response_body = response.json()
        
        # Save the image
        image_base64 = response_body['artifacts'][0]['base64']
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(image_base64))
        
        if debug:
            print(f"Image saved to {output_path}")
        
        return True
        
    except Exception as e:
        if debug:
            print(f"Error generating image: {str(e)}")
        return False

def text_to_speech(text, output_path, voice_name="vi-VN-Wavenet-A", debug=False):
    """
    Convert text to speech using Google Cloud TTS.
    
    Args:
        text: Text to convert to speech
        output_path: Path to save the audio file
        voice_name: Google TTS voice to use
        debug: Whether to print debug information
        
    Returns:
        True if audio was generated successfully, False otherwise
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Check for Google credentials
        if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            raise ValueError("GOOGLE_APPLICATION_CREDENTIALS environment variable not set")
        
        if debug:
            print(f"\n--- DEBUG: GENERATING AUDIO FOR TEXT ---")
            print(f"Text: {text[:50]}..." if len(text) > 50 else f"Text: {text}")
            print(f"Output path: {output_path}")
            print(f"Voice: {voice_name}")
            print("--- END DEBUG INFO ---\n")
        
        # Initialize TTS client
        client = tts.TextToSpeechClient()
        
        # Set input text
        synthesis_input = tts.SynthesisInput(text=text)
        
        # Set voice parameters
        voice_params = tts.VoiceSelectionParams(
            language_code="vi-VN",
            name=voice_name
        )
        
        # Set audio config
        audio_config = tts.AudioConfig(
            audio_encoding=tts.AudioEncoding.LINEAR16,
            pitch=2,
            speaking_rate=1.1
        )
        
        # Generate speech
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice_params,
            audio_config=audio_config
        )
        
        # Save audio to file
        with open(output_path, "wb") as out:
            out.write(response.audio_content)
        
        if debug:
            print(f"Audio saved to {output_path}")
        
        return True
        
    except Exception as e:
        if debug:
            print(f"Error generating audio: {str(e)}")
        return False

def generate_scene_images(scenes_data, images_path, force_regenerate=False, debug=False):
    """
    Generate images for all scenes based on their image descriptions.
    
    Args:
        scenes_data: List of scene dictionaries with 'image_description' keys
        images_path: Directory to save the generated images
        force_regenerate: Whether to regenerate images even if they already exist
        debug: Whether to print debug information
        
    Returns:
        List of paths to successfully generated images
    """
    # Create output directory if it doesn't exist
    os.makedirs(images_path, exist_ok=True)
    
    generated_images = []
    
    for scene in scenes_data:
        scene_index = scene.get("index", 0)
        image_description = scene.get("image_description", "")
        
        if not image_description:
            if debug:
                print(f"No image description for scene {scene_index}, skipping")
            continue
        
        # Create output path
        output_path = os.path.join(images_path, f"scene_{scene_index}.png")
        
        # Skip if image already exists and not forcing regeneration
        if os.path.exists(output_path) and not force_regenerate:
            if debug:
                print(f"Image for scene {scene_index} already exists, skipping")
            generated_images.append(output_path)
            continue
        
        # Generate image
        success = prompt_to_image(
            image_prompt=image_description,
            output_path=output_path,
            debug=debug
        )
        
        if success:
            generated_images.append(output_path)
            if debug:
                print(f"Generated image for scene {scene_index}")
    
    return generated_images

def generate_scene_audio(scenes_data, audio_path, force_regenerate=False, debug=False):
    """
    Generate audio for all scenes based on their content.
    
    Args:
        scenes_data: List of scene dictionaries with 'content' keys
        audio_path: Directory to save the generated audio
        force_regenerate: Whether to regenerate audio even if it already exists
        debug: Whether to print debug information
        
    Returns:
        List of paths to successfully generated audio files
    """
    # Create output directory if it doesn't exist
    os.makedirs(audio_path, exist_ok=True)
    
    generated_audio = []
    
    for scene in scenes_data:
        scene_index = scene.get("index", 0)
        scene_content = scene.get("content", "")
        
        if not scene_content:
            if debug:
                print(f"No content for scene {scene_index}, skipping")
            continue
        
        # Create output path
        output_path = os.path.join(audio_path, f"scene_{scene_index}.wav")
        
        # Skip if audio already exists and not forcing regeneration
        if os.path.exists(output_path) and not force_regenerate:
            if debug:
                print(f"Audio for scene {scene_index} already exists, skipping")
            generated_audio.append(output_path)
            continue
        
        # Generate audio
        success = text_to_speech(
            text=scene_content,
            output_path=output_path,
            debug=debug
        )
        
        if success:
            generated_audio.append(output_path)
            if debug:
                print(f"Generated audio for scene {scene_index}")
    
    return generated_audio

def create_new_story(story_id):
    """
    Create a new story configuration by prompting the user.
    
    Args:
        story_id: ID for the new story
        
    Returns:
        Story configuration dictionary
    """
    print(f"Creating new story with ID: {story_id}")
    
    # Create base directories
    story_dir = f"data/{story_id}"
    images_dir = f"{story_dir}/images"
    audio_dir = f"{story_dir}/audio"
    cached_dir = f"cached/llm"
    
    os.makedirs(story_dir, exist_ok=True)
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)
    os.makedirs(cached_dir, exist_ok=True)
    
    # Prompt for story content
    print("Enter story content (end with Ctrl+D on a new line):")
    story_lines = []
    try:
        while True:
            line = input()
            story_lines.append(line)
    except EOFError:
        pass
    
    story_content = "\n".join(story_lines)
    
    # Save story content
    story_path = f"{story_dir}/story.txt"
    with open(story_path, 'w', encoding='utf-8') as f:
        f.write(story_content)
    
    # Create cached_llm_path but don't write to it yet
    cached_llm_filename = f"{story_id}_{hash(story_content) % 10000000000}.json"
    cached_llm_path = f"{cached_dir}/{cached_llm_filename}"
    
    # Default to story_to_scene.prompt
    prompt_path = "prompts/story_to_scene.prompt"
    
    # Create story config
    story_config = {
        "story_id": story_id,
        "story_path": story_path,
        "cached_llm_path": cached_llm_path,
        "prompt": prompt_path,
        "images_path": images_dir,
        "audio_path": audio_dir
    }
    
    # Save to database
    add_or_update_story(story_config)
    
    print(f"Story created successfully. Configuration saved to {STORIES_DB_PATH}")
    
    return story_config

def create_video_from_scenes(images_paths, audio_paths, output_path, bg_music_path="bg_music/Asphyxia.mp3", image_duration=None, debug=False):
    """
    Create a video from images and audio files.
    
    Args:
        images_paths: List of paths to image files
        audio_paths: List of paths to audio files
        output_path: Path to save the output video
        bg_music_path: Path to background music file
        image_duration: Duration in seconds for each image (if None, will use audio duration)
        debug: Whether to print debug information
        
    Returns:
        Path to the created video file if successful, None otherwise
    """
    if not has_moviepy:
        print("Cannot create video: MoviePy is not available")
        return None
        
    try:
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        if debug:
            print(f"\n--- DEBUG: CREATING VIDEO ---")
            print(f"Number of images: {len(images_paths)}")
            print(f"Number of audio clips: {len(audio_paths)}")
            print(f"Background music: {bg_music_path}")
            print(f"Output path: {output_path}")
            print("--- END DEBUG INFO ---\n")
        
        # Sort image and audio paths by scene number
        def get_scene_number(path):
            match = re.search(r'scene_(\d+)', path)
            if match:
                return int(match.group(1))
            return 0
            
        images_paths = sorted(images_paths, key=get_scene_number)
        audio_paths = sorted(audio_paths, key=get_scene_number)
        
        # Create video clips
        video_clips = []
        
        for i, (img_path, audio_path) in enumerate(zip(images_paths, audio_paths)):
            # Load the image
            img_clip = ImageClip(img_path)
            
            # Load the audio
            audio_clip = AudioFileClip(audio_path)
            
            # Set duration based on audio if not specified
            duration = image_duration if image_duration else audio_clip.duration
            
            # Set image duration
            img_clip = img_clip.set_duration(duration)
            
            # Set audio
            img_clip = img_clip.set_audio(audio_clip)
            
            video_clips.append(img_clip)
            
            if debug:
                print(f"Added scene {i+1}: Image={img_path}, Audio={audio_path}, Duration={duration:.2f}s")
        
        # Concatenate all clips
        final_clip = concatenate_videoclips(video_clips)
        
        # Add background music if the file exists
        try:
            if os.path.exists(bg_music_path):
                # Load background music
                bg_music = AudioFileClip(bg_music_path)
                
                # Loop the background music if needed to match video duration
                if bg_music.duration < final_clip.duration:
                    num_loops = int(final_clip.duration / bg_music.duration) + 1
                    bg_music = concatenate_audioclips([bg_music] * num_loops).subclip(0, final_clip.duration)
                else:
                    # Trim the background music to match video duration
                    bg_music = bg_music.subclip(0, final_clip.duration)
                
                # Mix background music with the existing audio (reduce bg music volume)
                bg_music = bg_music.volumex(0.2)  # Reduce volume to 20%
                
                # Get the existing audio from the final clip
                original_audio = final_clip.audio
                
                # Mix the two audio tracks
                final_audio = CompositeAudioClip([original_audio, bg_music])
                
                # Set the new mixed audio to the final clip
                final_clip = final_clip.set_audio(final_audio)
                
                if debug:
                    print(f"Added background music: {bg_music_path} (volume: 20%)")
            else:
                if debug:
                    print(f"Background music file not found: {bg_music_path}")
        except Exception as e:
            if debug:
                print(f"Error adding background music: {str(e)}")
        
        # Write the result to a file
        final_clip.write_videofile(
            output_path,
            fps=24,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True
        )
        
        # Close all clips to free up memory
        final_clip.close()
        for clip in video_clips:
            clip.close()
            
        if debug:
            print(f"Video saved to {output_path}")
            
        return output_path
        
    except Exception as e:
        if debug:
            print(f"Error creating video: {str(e)}")
        return None

def collect_scene_files(story_config, file_type='all'):
    """
    Collect all files for scenes (images, audio) for a story.
    
    Args:
        story_config: Story configuration dictionary
        file_type: Type of files to collect ('images', 'audio', or 'all')
        
    Returns:
        Dictionary with lists of image and audio files
    """
    result = {
        'images': [],
        'audio': []
    }
    
    # Collect image files
    if file_type in ['images', 'all']:
        images_path = story_config.get('images_path')
        if images_path and os.path.exists(images_path):
            for file in os.listdir(images_path):
                if file.startswith('scene_') and file.endswith('.png'):
                    result['images'].append(os.path.join(images_path, file))
    
    # Collect audio files
    if file_type in ['audio', 'all']:
        audio_path = story_config.get('audio_path')
        if audio_path and os.path.exists(audio_path):
            for file in os.listdir(audio_path):
                if file.startswith('scene_') and file.endswith('.wav'):
                    result['audio'].append(os.path.join(audio_path, file))
    
    # Sort files by scene number
    def get_scene_number(path):
        match = re.search(r'scene_(\d+)', path)
        if match:
            return int(match.group(1))
        return 0
        
    result['images'] = sorted(result['images'], key=get_scene_number)
    result['audio'] = sorted(result['audio'], key=get_scene_number)
    
    return result

def generate_story_video(story_config, force_regenerate=False, bg_music_path="bg_music/Asphyxia.mp3", debug=False):
    """
    Generate a video for a story from images and audio.
    
    Args:
        story_config: Story configuration dictionary
        force_regenerate: Whether to force regeneration of the video
        bg_music_path: Path to background music file
        debug: Whether to print debug information
        
    Returns:
        Path to the video file if successful, None otherwise
    """
    if not has_moviepy:
        print("Cannot generate video: MoviePy is not available")
        return None
        
    # Get story ID and paths
    story_id = story_config.get('story_id')
    story_dir = os.path.dirname(story_config.get('story_path', ''))
    
    # Set video path if not in config
    video_path = story_config.get('video_path')
    if not video_path:
        video_path = os.path.join(story_dir, 'video.mp4')
        story_config['video_path'] = video_path
        add_or_update_story(story_config)
    
    # Check if video already exists
    if os.path.exists(video_path) and not force_regenerate:
        if debug:
            print(f"Video already exists at {video_path}, skipping generation")
        return video_path
    
    # Collect scene files
    scene_files = collect_scene_files(story_config)
    
    # Check if we have both images and audio
    if not scene_files['images'] or not scene_files['audio']:
        if debug:
            print(f"Missing images or audio files for story {story_id}")
            print(f"Found {len(scene_files['images'])} images and {len(scene_files['audio'])} audio files")
        return None
    
    # Match the number of images and audio files by using the minimum
    min_count = min(len(scene_files['images']), len(scene_files['audio']))
    images = scene_files['images'][:min_count]
    audio = scene_files['audio'][:min_count]
    
    # Create video
    return create_video_from_scenes(
        images_paths=images,
        audio_paths=audio,
        output_path=video_path,
        bg_music_path=bg_music_path,
        debug=debug
    )

def process_story(story_id, force_regenerate_scenes=False, force_regenerate_images=False, force_regenerate_audio=False, force_regenerate_video=False, bg_music_path="bg_music/Asphyxia.mp3", debug=False):
    """
    Process a story: generate scenes, images, audio, and video if needed.
    
    Args:
        story_id: ID of the story to process
        force_regenerate_scenes: Whether to force regeneration of scenes
        force_regenerate_images: Whether to force regeneration of images
        force_regenerate_audio: Whether to force regeneration of audio
        force_regenerate_video: Whether to force regeneration of video
        bg_music_path: Path to background music file for video
        debug: Whether to print debug information
        
    Returns:
        True if processing was successful, False otherwise
    """
    # Get story config
    story_config = get_story_by_id(story_id)
    
    if not story_config:
        print(f"Story ID {story_id} not found. Creating new story...")
        story_config = create_new_story(story_id)
    
    # Extract paths from config
    story_path = story_config["story_path"]
    cached_llm_path = story_config["cached_llm_path"]
    prompt_path = story_config["prompt"]
    images_path = story_config["images_path"]
    audio_path = story_config.get("audio_path", os.path.join(os.path.dirname(story_path), "audio"))
    
    # Update config with audio_path if it doesn't exist
    if "audio_path" not in story_config:
        story_config["audio_path"] = audio_path
        add_or_update_story(story_config)
    
    # Ensure directories exist
    os.makedirs(os.path.dirname(story_path), exist_ok=True)
    os.makedirs(os.path.dirname(cached_llm_path), exist_ok=True)
    os.makedirs(images_path, exist_ok=True)
    os.makedirs(audio_path, exist_ok=True)
    
    try:
        # Load the prompt with story content
        full_prompt = load_full_prompt(prompt_path, story_path)
        print(f"Successfully loaded and populated the prompt with story content")
        
        # Only regenerate scenes if forced or no cached response exists
        if force_regenerate_scenes or not os.path.exists(cached_llm_path):
            scenes_json = prompt_to_json(full_prompt, cached_llm_path=cached_llm_path, debug=debug)
            print(f"Generated {len(scenes_json)} scenes")
        else:
            # Load from cache
            with open(cached_llm_path, 'r', encoding='utf-8') as f:
                scenes_json = json.load(f)
            print(f"Loaded {len(scenes_json)} scenes from cache")
        
        # Save the JSON to a file in the story directory
        scenes_json_path = os.path.join(os.path.dirname(story_path), "scenes.json")
        with open(scenes_json_path, 'w', encoding='utf-8') as f:
            json.dump(scenes_json, f, ensure_ascii=False, indent=2)
        print(f"Saved scenes to {scenes_json_path}")
        
        # Generate images
        images = generate_scene_images(
            scenes_json, 
            images_path=images_path, 
            force_regenerate=force_regenerate_images,
            debug=debug
        )
        print(f"Generated/Found {len(images)} images for scenes")
        
        # Generate audio
        audio = generate_scene_audio(
            scenes_json,
            audio_path=audio_path,
            force_regenerate=force_regenerate_audio,
            debug=debug
        )
        print(f"Generated/Found {len(audio)} audio files for scenes")
        
        # Generate video
        if len(images) > 0 and len(audio) > 0 and has_moviepy:
            video = generate_story_video(
                story_config,
                force_regenerate=force_regenerate_video,
                bg_music_path=bg_music_path,
                debug=debug
            )
            if video:
                print(f"Generated video saved to {video}")
            else:
                print("Failed to generate video")
        elif not has_moviepy:
            print("Skipping video generation: MoviePy is not available")
        else:
            print("Skipping video generation: missing images or audio files")
        
        return True
        
    except Exception as e:
        print(f"Error processing story: {str(e)}")
        return False

def list_all_stories():
    """
    List all stories in the database.
    """
    stories_db = load_stories_db()
    
    if not stories_db:
        print("No stories found in the database.")
        return
    
    print("\n=== All Stories ===")
    for story_id, config in stories_db.items():
        print(f"ID: {story_id}")
        try:
            print(f"  Story path: {config['story_path']}")
            print(f"  Prompt: {config['prompt']}")
            print(f"  Images: {config['images_path']}")
            print(f"  Audio: {config.get('audio_path', 'Not set')}")
            print(f"  Video: {config.get('video_path', 'Not set')}")
            print(f"  Cached LLM: {config['cached_llm_path']}")
        except (KeyError, TypeError) as e:
            print(f"  Error displaying story details: {e}")
            print(f"  Raw config: {config}")
        print()

def main():
    """
    Main function to process command line arguments.
    """
    parser = argparse.ArgumentParser(description="Story Scene Generator")
    parser.add_argument("--id", help="Story ID to process")
    parser.add_argument("--list", action="store_true", help="List all stories")
    parser.add_argument("--force-scenes", action="store_true", help="Force regeneration of scenes")
    parser.add_argument("--force-images", action="store_true", help="Force regeneration of images")
    parser.add_argument("--force-audio", action="store_true", help="Force regeneration of audio")
    parser.add_argument("--force-video", action="store_true", help="Force regeneration of video")
    parser.add_argument("--bg-music", help="Path to background music file", default="bg_music/Asphyxia.mp3")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    args = parser.parse_args()
    
    if args.list:
        list_all_stories()
        return
    
    if args.id:
        process_story(
            args.id, 
            force_regenerate_scenes=args.force_scenes,
            force_regenerate_images=args.force_images,
            force_regenerate_audio=args.force_audio,
            force_regenerate_video=args.force_video,
            bg_music_path=args.bg_music,
            debug=args.debug
        )
    else:
        print("Please specify a story ID with --id or use --list to see all stories")
        return

if __name__ == "__main__":
    main() 