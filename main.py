import os
import time
import argparse
from downloader import download_random_ncs_song
from image_gen import create_background
from video_compiler import create_music_video
from uploader import run_upload

def run_ncs_automation(video_type="long", no_upload=False):
    print("==================================================")
    print(f"  🚀 STARTING NCS YOUTUBE BOT ({video_type.upper()} MODE)")
    print("==================================================")
    
    # STEP 1: Get Audio
    print("\n>>> STEP 1: Fetching Music...")
    audio_path, title = download_random_ncs_song("downloads")
    if not audio_path:
        print("Pipeline Failed at Step 1.")
        return
        
    # STEP 2: Get Background AI Image
    print("\n>>> STEP 2: Generating AI Visuals...")
    image_path = create_background(video_type)
    if not image_path:
        print("Pipeline Failed at Step 2.")
        return
        
    # STEP 3: Render Final Video with Visualizer Overlay
    print("\n>>> STEP 3: Compiling Music Video with Visualizer...")
    video_path = "downloads/final_video.mp4"
    
    success = create_music_video(audio_path, image_path, video_path, video_type, song_title=title)
    if not success:
        print("Pipeline Failed at Step 3.")
        return
        
    if no_upload:
        print("\n✅ DRY RUN COMPLETE: Video generated but NOT uploaded.")
        print(f"Preview available at: {video_path}")
        return

    # STEP 4: Upload to YouTube
    print("\n>>> STEP 4: Uploading to YouTube...")
    upload_success = run_upload(video_path, title, video_type)
    
    if upload_success:
        print("\n🎉 AUTOMATION PIPELINE COMPLETED SUCCESSFULLY! 🎉")
        
        # Cleanup
        print("🧹 Cleaning up workspace...")
        try:
            if os.path.exists(audio_path): os.remove(audio_path)
            if os.path.exists(image_path): os.remove(image_path)
            if os.path.exists(video_path): os.remove(video_path)
        except: pass
            
    else:
        print("\n❌ Pipeline Failed at Final Upload Step.")
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NCS YouTube Music Bot")
    parser.add_argument("--type", choices=["long", "short"], default="long", help="Video format")
    parser.add_argument("--no-upload", action="store_true", help="Generate video but do not upload to YouTube")
    args = parser.parse_args()
    
    run_ncs_automation(args.type, no_upload=args.no_upload)
