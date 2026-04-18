import os
import sys
from video_compiler import create_music_video

# Add current dir to path
sys.path.append(os.getcwd())

audio_path = r"TANTRON, More Plastic - CERBERUS ｜ DnB ｜ NCS - Copyright Free Music [C07xJuLrmfg].wav"
output_path = "downloads/beat_sync_test.mp4"

if not os.path.exists(audio_path):
    print(f"Error: Audio file not found at {audio_path}")
    sys.exit(1)

print(f"🎬 Starting Visualizer Test Run for: {audio_path}")
success = create_music_video(
    audio_path=audio_path,
    image_path=None,
    output_path=output_path,
    video_type="short",
    song_title="CERBERUS (Cyan Theme Test)",
    song_genre="Chillstep"
)

if success:
    print(f"✅ Success! Test video generated at: {output_path}")
else:
    print("❌ Failed to generate test video.")
