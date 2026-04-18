import subprocess
import random
import os
import json

def download_random_ncs_song(output_dir="downloads"):
    """
    Robust Multi-Engine Downloader:
    1. Fetches latest videos from NCS YouTube.
    2. Attempts High-Quality download with robust extractor settings.
    3. (Future) Fallback to external API if direct fails.
    """
    os.makedirs(output_dir, exist_ok=True)
    print("Fetching list of latest NCS videos from YouTube...")
    
    ncs_url = "https://www.youtube.com/@NoCopyrightSounds/videos"
    cookies_file = "cookies.txt"
    
    # Engine Settings: Using mobile/android clients is more robust against signature blocks
    extractor_args = "youtube:player-client=web,android"
    
    # 1. Fetch JSON data
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        "--playlist-end", "50",
        "--extractor-args", extractor_args,
        ncs_url
    ]
    
    if os.path.exists(cookies_file):
        cmd.extend(["--cookies", cookies_file])

    try:
        print("Running yt-dlp to fetch video list...")
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line: continue
            try:
                data = json.loads(line)
                uploader = data.get("uploader") or ""
                if data.get("id") and data.get("title"):
                    v_url = data.get("url") or f"https://www.youtube.com/watch?v={data['id']}"
                    if "NoCopyrightSounds" in uploader or "@NoCopyrightSounds" in ncs_url:
                        videos.append({"id": data["id"], "title": data["title"], "url": v_url})
            except json.JSONDecodeError:
                pass
        
        if not videos:
            print("Error: No videos found. YouTube might be blocking the flat-playlist request.")
            return None, None
            
        print(f"Found {len(videos)} videos. Selecting a fresh one...")
        
        history_file = "downloads_history.txt"
        history = []
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = f.read().splitlines()
            
        random.shuffle(videos)
        chosen = next((v for v in videos if v['id'] not in history), None)
                
        if not chosen:
            print("Notice: No fresh videos found. All latest videos are in history.")
            return None, None
        
        target_v_url = chosen['url']
        print(f"Selected: {chosen['title']} ({target_v_url})")
        
        audio_file = os.path.join(output_dir, "audio.wav")
        if os.path.exists(audio_file):
            os.remove(audio_file)
            
        # 2. Robust HQ Download Command
        # We try with 'bestaudio/best' and use the android client to avoid signature issues
        dl_cmd = [
            "yt-dlp",
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "wav", 
            "--audio-quality", "0",
            "--extractor-args", extractor_args,
            "--rm-cache-dir",
            "--output", audio_file,
            target_v_url
        ]
        
        if os.path.exists(cookies_file):
            dl_cmd.extend(["--cookies", cookies_file])
        
        print("Attempting High-Quality audio download (Engine 1: Direct Robust)...")
        dl_result = subprocess.run(dl_cmd, capture_output=True, text=True)
        
        if dl_result.returncode == 0 and os.path.exists(audio_file):
            # Save to history only on success
            with open(history_file, 'a', encoding='utf-8') as f:
                f.write(chosen['id'] + "\n")
            print(f"Download complete: {audio_file}")
            return audio_file, chosen['title']
        else:
            print("Engine 1 failed. Error details:")
            print(dl_result.stderr[-500:] if dl_result.stderr else "Unknown Error")
            
            # TODO: Add Engine 2 (Cobalt API) fallback here in next update
            print("No more engines configured. Download failed.")
            return None, None
            
    except Exception as e:
        print(f"Engine Exception: {e}")
        return None, None
            
    except subprocess.CalledProcessError as e:
        print(f"Command Error: yt-dlp failed with exit code {e.returncode}.")
        if getattr(e, 'stderr', None):
            print(f"yt-dlp STDERR: {e.stderr}")
        return None, None
    except Exception as e:
        print(f"Error downloading: {e}")
        return None, None

if __name__ == "__main__":
    audio_path, title = download_random_ncs_song()
    if title:
        print(f"Success! Ready for visualizer: {title}")
