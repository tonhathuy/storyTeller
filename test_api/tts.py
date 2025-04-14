from google.cloud import texttospeech as tts
import os

# Set the path to your service account key file
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "./second-capsule-456707-h2-beeb0ceb5c11.json"

def list_voices(language_code=None):
    client = tts.TextToSpeechClient()
    response = client.list_voices(language_code=language_code)
    voices = sorted(response.voices, key=lambda voice: voice.name)

    print(f" Voices: {len(voices)} ".center(60, "-"))
    for voice in voices:
        languages = ", ".join(voice.language_codes)
        name = voice.name
        gender = tts.SsmlVoiceGender(voice.ssml_gender).name
        rate = voice.natural_sample_rate_hertz
        print(f"{languages:<8} | {name:<24} | {gender:<8} | {rate:,} Hz")
        

def text_to_speech(text, voice_name, output_filename):
   

    client = tts.TextToSpeechClient()

    synthesis_input = tts.SynthesisInput(text=text)

    voice_params = tts.VoiceSelectionParams(
        language_code="vi-VN",
        name=voice_name
    )
    pitch_param = 4
    audio_config = tts.AudioConfig(
        # audio_encoding=tts.AudioEncoding.MP3
        audio_encoding=tts.AudioEncoding.LINEAR16,
        pitch=pitch_param,
        speaking_rate=1.1
    )
    
    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice_params,
        audio_config=audio_config
    )
    
    with open(output_filename, "wb") as out:
        out.write(response.audio_content)
        print(f"Audio content written to file: {output_filename}")

if __name__ == "__main__":
    text =  "Ở Seoul năm 2013, Yoon Ji – một họa sĩ truyện tranh kinh dị trên mạng – nổi tiếng nhờ những tác phẩm kỳ quái và ám ảnh. Cô có thói quen ký tên bằng một họa tiết riêng biệt sau mỗi bản vẽ, như cách khẳng định dấu ấn cá nhân.,"
    output_file = "output.wav"
    text_to_speech(text, "vi-VN-Wavenet-A", output_file)