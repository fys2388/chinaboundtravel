import os
from gtts import gTTS
from config import Config

def synthesize_speech(text: str, output_path: str) -> bool:
    try:
        tts = gTTS(text=text, lang='en', slow=False)
        tts.save(output_path)
        
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            return True
        return False
    except Exception as e:
        print(f"Error synthesizing speech: {e}")
        return False

def generate_voiceover(narration_text: str, video_id: str) -> str:
    output_path = os.path.join(Config.TEMP_DIR, f"{video_id}_voiceover.mp3")
    
    try:
        success = synthesize_speech(narration_text, output_path)
        
        if success:
            return output_path
        print("Voiceover generation returned empty")
        return ""
    except Exception as e:
        print(f"Voiceover generation error: {e}")
        return ""

def list_available_voices() -> list:
    voices = [
        {"name": "en-US-GuyNeural", "language": "English (US)", "gender": "Male"},
        {"name": "en-US-JennyNeural", "language": "English (US)", "gender": "Female"},
        {"name": "en-GB-RyanNeural", "language": "English (UK)", "gender": "Male"},
        {"name": "en-GB-SoniaNeural", "language": "English (UK)", "gender": "Female"},
        {"name": "en-AU-CarlyNeural", "language": "English (AU)", "gender": "Female"},
        {"name": "en-AU-WilliamNeural", "language": "English (AU)", "gender": "Male"},
        {"name": "en-CA-ClaraNeural", "language": "English (CA)", "gender": "Female"},
        {"name": "en-CA-LiamNeural", "language": "English (CA)", "gender": "Male"},
    ]
    return voices