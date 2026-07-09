import os
import re
from typing import List, Dict
import requests

import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.LANCZOS

from moviepy import config as moviepy_config

imagemagick_paths = [
    r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe",
    r"C:\Program Files\ImageMagick\magick.exe",
    r"C:\Program Files (x86)\ImageMagick\magick.exe",
    r"C:\Program Files\ImageMagick-7.1.1-Q16\magick.exe",
]

for path in imagemagick_paths:
    if os.path.exists(path):
        moviepy_config.change_settings({"IMAGEMAGICK_BINARY": path})
        break

from moviepy.editor import (
    VideoFileClip,
    ImageClip,
    AudioFileClip,
    CompositeAudioClip,
    concatenate_videoclips,
    TextClip,
    CompositeVideoClip,
    ColorClip
)
from moviepy.video.fx.all import resize, fadein, fadeout
from config import Config

def generate_image(prompt: str, image_id: str) -> str:
    try:
        url = "https://trae-api-cn.mchost.guru/api/ide/v1/text_to_image"
        params = {
            "prompt": prompt,
            "image_size": "portrait_9_16"
        }
        
        response = requests.get(url, params=params, timeout=60)
        response.raise_for_status()
        
        image_data = response.content
        output_path = os.path.join(Config.TEMP_DIR, f"{image_id}.jpg")
        
        with open(output_path, "wb") as f:
            f.write(image_data)
        
        return output_path
    except Exception as e:
        print(f"Error generating image: {e}")
        return ""

def parse_time_segment(time_str: str) -> tuple:
    match = re.match(r"(\d+)-(\d+)s", time_str)
    if match:
        return int(match.group(1)), int(match.group(2))
    return 0, 5

def create_slide(image_path: str, duration: float) -> VideoFileClip:
    try:
        clip = ImageClip(image_path)
        clip = clip.resize(height=Config.VIDEO_HEIGHT)
        
        if clip.w < Config.VIDEO_WIDTH:
            clip = clip.resize(width=Config.VIDEO_WIDTH)
        
        clip = clip.crop(
            x_center=clip.w // 2,
            y_center=clip.h // 2,
            width=Config.VIDEO_WIDTH,
            height=Config.VIDEO_HEIGHT
        )
        
        return clip.set_duration(duration).set_fps(Config.VIDEO_FPS)
    except Exception as e:
        print(f"Error creating slide: {e}")
        color_clip = ColorClip(
            size=(Config.VIDEO_WIDTH, Config.VIDEO_HEIGHT),
            color=(30, 41, 59)
        ).set_duration(duration)
        return color_clip

def create_subtitle(text: str, start_time: float, duration: float) -> TextClip:
    try:
        subtitle = TextClip(
            text,
            fontsize=48,
            font="Arial",
            color="white",
            stroke_color="black",
            stroke_width=2,
            method="label"
        )
        
        subtitle = subtitle.set_start(start_time).set_duration(duration)
        subtitle = subtitle.set_position(("center", "bottom"))
        
        return subtitle
    except Exception as e:
        print(f"Error creating subtitle: {e}")
        return None

def assemble_video(script: Dict, voiceover_path: str, video_id: str) -> str:
    scenes = script.get("scenes", [])
    subtitles = script.get("subtitles", [])
    
    image_paths = []
    slides = []
    
    for i, scene in enumerate(scenes):
        prompt = scene.get("image_prompt", "")
        if prompt:
            image_path = generate_image(prompt, f"{video_id}_scene_{i}")
            if image_path:
                image_paths.append(image_path)
                start, end = parse_time_segment(scene.get("time", "0-5s"))
                duration = end - start
                slide = create_slide(image_path, duration)
                slides.append(slide)
        else:
            start, end = parse_time_segment(scene.get("time", "0-5s"))
            duration = end - start
            color_clip = ColorClip(
                size=(Config.VIDEO_WIDTH, Config.VIDEO_HEIGHT),
                color=(30, 41, 59)
            ).set_duration(duration)
            slides.append(color_clip)
    
    if not slides:
        slides.append(ColorClip(
            size=(Config.VIDEO_WIDTH, Config.VIDEO_HEIGHT),
            color=(30, 41, 59)
        ).set_duration(15))
    
    video = concatenate_videoclips(slides, method="compose")
    
    if voiceover_path and os.path.exists(voiceover_path):
        audio = AudioFileClip(voiceover_path)
        if audio.duration > video.duration:
            video = video.set_duration(audio.duration)
        elif audio.duration < video.duration:
            video = video.subclip(0, audio.duration)
        video = video.set_audio(audio)
    
    subtitle_clips = []
    for subtitle in subtitles:
        start, end = parse_time_segment(subtitle.get("time", "0-3s"))
        text = subtitle.get("text", "")
        duration = end - start
        sub_clip = create_subtitle(text, start, duration)
        if sub_clip:
            subtitle_clips.append(sub_clip)
    
    if subtitle_clips:
        video = CompositeVideoClip([video] + subtitle_clips)
    
    output_path = os.path.join(Config.OUTPUT_DIR, f"{video_id}.mp4")
    
    try:
        video.write_videofile(
            output_path,
            fps=Config.VIDEO_FPS,
            codec="libx264",
            audio_codec="aac",
            bitrate="5000k",
            threads=4
        )
        
        if os.path.exists(output_path):
            return output_path
        return ""
    except Exception as e:
        print(f"Error writing video: {e}")
        return ""

def cleanup_temp_files(video_id: str):
    for filename in os.listdir(Config.TEMP_DIR):
        if video_id in filename:
            file_path = os.path.join(Config.TEMP_DIR, filename)
            try:
                os.remove(file_path)
            except Exception:
                pass