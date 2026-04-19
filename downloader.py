import subprocess
import random
import os
import json
import re

HISTORY_FILE = "downloads_history.txt"
COOKIES_FILE = "cookies.txt"
EXTRACTOR_ARGS = "youtube:player-client=web,android"
NCS_SOUNDCLOUD = "https://soundcloud.com/nocopyrightsounds"
NCS_YOUTUBE = "https://www.youtube.com/@NoCopyrightSounds/videos"


def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return set(f.read().splitlines())
    return set()


def save_to_history(track_id):
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(str(track_id) + "\n")


def detect_genre(title):
    """
    Detect genre from NCS title patterns:
    - Pipe format:    Artist - Song | Genre | NCS x Label ...
    - Bracket format: Artist - Song [Genre]
    """
    SKIP_LABELS = {"ncs release", "ncs", "ncs x aurorian records", "copyright free music", ""}
    title_clean = title.replace("\uff5c", "|")

    # Pipe format: pick first part that is not a skip label
    if "|" in title_clean:
        parts = [p.strip() for p in title_clean.split("|")]
        for part in parts[1:]:          # skip artist/song name (parts[0])
            candidate = part.strip()
            if candidate.lower() not in SKIP_LABELS and not candidate.lower().startswith("ncs x"):
                return candidate

    # Bracket format: Artist - Song [Genre] or Artist - Song [NCS Release]
    matches = re.findall(r'\[([^\]]+)\]', title_clean)
    for match in matches:
        candidate = match.strip()
        if candidate.lower() not in SKIP_LABELS:
            return candidate

    return "NCS Release"


def find_genre_from_youtube(sc_title, yt_videos):
    """
    Cross-reference a SoundCloud title with YouTube videos to get the real genre.
    SoundCloud uses '[NCS Release]', YouTube uses '| Genre |'.
    Matches by artist name(s) found in both titles.
    """
    # Extract artist part: everything before ' - ' or '[' in the SoundCloud title
    artist_part = re.split(r'\s*[-–]\s*|\s*\[', sc_title)[0].strip().lower()
    # artist_part might be like "twisted, kellapsage" or "nuphory, chikaya"
    # Split by comma to get individual artist names
    artists = [a.strip() for a in re.split(r'[,&]', artist_part) if a.strip()]

    for yt in yt_videos:
        yt_lower = yt["title"].lower()
        # Check if any artist from SoundCloud is in the YouTube title
        if any(len(a) > 3 and a in yt_lower for a in artists):
            genre = yt.get("genre", "NCS Release")
            if genre and genre.lower() != "ncs release":
                return genre
    return None


# ─────────────────────────────────────────
# ENGINE 1: NCS official website (ncs.io)
# ─────────────────────────────────────────
def fetch_tracks_from_ncs_io():
    """Fetch track list from NCS official website (ncs.io/music-search)."""
    try:
        import requests
        from bs4 import BeautifulSoup

        print("Engine 1: Fetching tracks from NCS official website (ncs.io)...")
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        offset = random.choice([0, 15, 30, 45, 60, 75, 90, 105, 120])
        url = f"https://ncs.io/music-search?q=&genre=&mood=&version=&offset={offset}"

        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        tracks = []

        # Approach A: data-tid attributes
        for item in soup.find_all(attrs={"data-tid": True}):
            track_id = item.get("data-tid", "").strip()
            title_el = (
                item.find(class_=["play-title", "track-title", "title"])
                or item.find("h3") or item.find("h4")
            )
            title = title_el.get_text(strip=True) if title_el else item.get("data-track-title", "")
            genre = item.get("data-genre", "") or detect_genre(title)
            if track_id and title:
                tracks.append({"id": track_id, "title": title, "genre": genre})

        # Approach B: playlist__item <li>
        if not tracks:
            for item in soup.find_all("li", class_=lambda c: c and "playlist" in c.lower()):
                track_id = (
                    item.get("data-tid") or item.get("data-id")
                    or item.get("id", "").replace("track-", "")
                )
                title_el = item.find(
                    class_=lambda c: c and ("title" in c.lower() or "name" in c.lower())
                )
                title = title_el.get_text(strip=True) if title_el else ""
                if title:
                    tracks.append({
                        "id": track_id or title,
                        "title": title,
                        "genre": item.get("data-genre", "NCS Release"),
                    })

        # Approach C: any element with data-track-title
        if not tracks:
            for item in soup.find_all(attrs={"data-track-title": True}):
                title = item.get("data-track-title", "").strip()
                track_id = item.get("data-tid") or item.get("data-id") or title
                genre = item.get("data-genre", "") or detect_genre(title)
                if title:
                    tracks.append({"id": track_id, "title": title, "genre": genre})

        print(f"NCS.io: Found {len(tracks)} tracks at offset {offset}")
        return tracks

    except Exception as e:
        print(f"NCS.io fetch error: {e}")
        return []


def download_from_ncs_io(track_id, title, output_file):
    """Download audio from NCS official website using track ID."""
    try:
        import requests

        print(f"  Downloading '{title}' from NCS.io (id={track_id})...")
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "Referer": "https://ncs.io/music",
            "Accept": "*/*",
        }

        candidates = [
            f"https://ncs.io/{track_id}/download",
            f"https://ncs.io/track/{track_id}/download",
            f"https://ncs.io/music/{track_id}/download",
        ]

        for dl_url in candidates:
            try:
                resp = requests.get(
                    dl_url, headers=headers, timeout=90,
                    allow_redirects=True, stream=True
                )
                ctype = resp.headers.get("Content-Type", "")
                if resp.status_code == 200 and (
                    "audio" in ctype or "octet-stream" in ctype or "mpeg" in ctype
                ):
                    with open(output_file, "wb") as f:
                        for chunk in resp.iter_content(chunk_size=8192):
                            f.write(chunk)
                    if os.path.exists(output_file) and os.path.getsize(output_file) > 100_000:
                        print(f"  Engine 1 Success via {dl_url}")
                        return True
                    if os.path.exists(output_file):
                        os.remove(output_file)
            except Exception:
                continue

        return False

    except Exception as e:
        print(f"NCS.io download error: {e}")
        return False


# ──────────────────────────────────────────────────────
# ENGINE 2: Cobalt API (FIXED — updated 2024/2025 format)
# ──────────────────────────────────────────────────────
def download_via_cobalt(url, output_file):
    """Download via Cobalt API using the updated v10+ format."""
    import requests

    print("Engine 2: Attempting download via Cobalt API (updated format)...")

    cobalt_instances = [
        "https://api.cobalt.tools/",
        "https://cobalt.api.timelessnesses.me/",
        "https://co.wuk.sh/",
    ]

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    payload = {
        "url": url,
        "downloadMode": "audio",
        "audioFormat": "wav",
        "audioBitrate": "320",
    }

    for api_url in cobalt_instances:
        try:
            resp = requests.post(api_url, json=payload, headers=headers, timeout=30)
            data = resp.json()
            status = data.get("status", "")

            # New API returns 'tunnel' or 'redirect'; old returned 'stream'
            if status in ("tunnel", "redirect", "stream"):
                stream_url = data.get("url")
                if not stream_url:
                    continue
                print(f"  Cobalt: Got '{status}' URL, downloading...")
                s_resp = requests.get(
                    stream_url, stream=True, timeout=120,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                with open(output_file, "wb") as f:
                    for chunk in s_resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                if os.path.exists(output_file) and os.path.getsize(output_file) > 100_000:
                    print(f"  Engine 2 Success via {api_url}")
                    return True
                if os.path.exists(output_file):
                    os.remove(output_file)
            else:
                err = (data.get("error") or {}).get("code", "") or data.get("text", "unknown")
                print(f"  Cobalt ({api_url}) error: {err}")

        except Exception as e:
            print(f"  Cobalt ({api_url}) exception: {e}")
            continue

    return False


# ──────────────────────────────────────────────────────
# ENGINE 3 + 4: yt-dlp helpers
# ──────────────────────────────────────────────────────
def fetch_videos_via_ytdlp(source_url, limit=40, use_cookies=True):
    """Fetch video list from YouTube or SoundCloud via yt-dlp."""
    cmd = [
        "yt-dlp",
        "--dump-json",
        "--flat-playlist",
        "--playlist-end", str(limit),
        source_url,
    ]
    if use_cookies and os.path.exists(COOKIES_FILE):
        cmd.extend(["--cookies", COOKIES_FILE])
    if "youtube.com" in source_url:
        cmd.extend(["--extractor-args", EXTRACTOR_ARGS])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        videos = []
        for line in result.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                vid_id = data.get("id", "")
                title = data.get("title", "")
                if vid_id and title:
                    if "youtube.com" in source_url or "youtu.be" in source_url:
                        v_url = f"https://www.youtube.com/watch?v={vid_id}"
                    else:
                        v_url = data.get("url") or data.get("webpage_url") or source_url
                    videos.append({
                        "id": vid_id,
                        "title": title,
                        "url": v_url,
                        "genre": detect_genre(title),
                    })
            except json.JSONDecodeError:
                pass
        return videos
    except Exception as e:
        print(f"  yt-dlp listing error ({source_url}): {e}")
        return []


def download_via_ytdlp(url, output_file, use_cookies=True):
    """Download audio via yt-dlp."""
    cmd = [
        "yt-dlp", "-f", "bestaudio/best",
        "--extract-audio", "--audio-format", "wav",
        "--audio-quality", "0",
        "--output", output_file,
        url,
    ]
    if use_cookies and os.path.exists(COOKIES_FILE):
        cmd.extend(["--cookies", COOKIES_FILE])
    if "youtube.com" in url or "youtu.be" in url:
        cmd.extend(["--extractor-args", EXTRACTOR_ARGS])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 100_000:
            return True
        if result.returncode != 0:
            print(f"  yt-dlp stderr: {result.stderr[:400]}")
    except subprocess.TimeoutExpired:
        print("  yt-dlp timed out")
    except Exception as e:
        print(f"  yt-dlp exception: {e}")
    return False


# ──────────────────────────────────────────────────────
# MAIN ENTRY POINT
# ──────────────────────────────────────────────────────
def download_random_ncs_song(output_dir="downloads"):
    """
    Multi-Engine Downloader — tries each engine in order:
      1. NCS official website (ncs.io) — primary, no IP block
      2. Cobalt API (updated 2024 format) + YouTube video URL
      3. yt-dlp on NCS SoundCloud (less strict than YouTube)
      4. yt-dlp direct YouTube (last resort)
    Returns (audio_path, title, genre)
    """
    os.makedirs(output_dir, exist_ok=True)
    history = load_history()

    audio_file = os.path.join(output_dir, "audio.wav")
    if os.path.exists(audio_file):
        os.remove(audio_file)

    # ── ENGINE 1: NCS.io ──────────────────────────────
    print("\n>>> ENGINE 1: NCS official website (ncs.io)")
    ncs_tracks = fetch_tracks_from_ncs_io()
    if ncs_tracks:
        random.shuffle(ncs_tracks)
        fresh = [t for t in ncs_tracks if str(t["id"]) not in history]
        chosen = fresh[0] if fresh else ncs_tracks[0]

        if download_from_ncs_io(chosen["id"], chosen["title"], audio_file):
            save_to_history(chosen["id"])
            return audio_file, chosen["title"], chosen["genre"]
        print("  Engine 1 download failed.")
    else:
        print("  Engine 1: No tracks fetched from ncs.io.")

    # Fetch YouTube video list (needed for engines 2 & 4)
    print("\n>>> Fetching YouTube video list for engines 2 & 4...")
    yt_videos = fetch_videos_via_ytdlp(NCS_YOUTUBE, limit=30, use_cookies=True)
    if yt_videos:
        print(f"  Found {len(yt_videos)} YouTube videos.")
    else:
        print("  Could not fetch YouTube list (IP block likely).")

    # ── ENGINE 2: Cobalt API + YouTube URL ────────────
    print("\n>>> ENGINE 2: Cobalt API (updated format)")
    if yt_videos:
        random.shuffle(yt_videos)
        fresh_yt = [v for v in yt_videos if v["id"] not in history]
        chosen_yt = fresh_yt[0] if fresh_yt else yt_videos[0]

        if download_via_cobalt(chosen_yt["url"], audio_file):
            save_to_history(chosen_yt["id"])
            return audio_file, chosen_yt["title"], chosen_yt["genre"]
        print("  Engine 2 failed.")
    else:
        print("  Engine 2 skipped (no YouTube URLs).")

    # ── ENGINE 3: yt-dlp on NCS SoundCloud ────────────
    print("\n>>> ENGINE 3: yt-dlp on NCS SoundCloud")
    sc_tracks = fetch_videos_via_ytdlp(NCS_SOUNDCLOUD, limit=50, use_cookies=False)
    if sc_tracks:
        random.shuffle(sc_tracks)
        fresh_sc = [t for t in sc_tracks if t["id"] not in history]
        chosen_sc = fresh_sc[0] if fresh_sc else sc_tracks[0]
        print(f"  Trying: {chosen_sc['title']}")

        # SoundCloud titles use '[NCS Release]' — cross-reference YouTube for real genre
        if chosen_sc["genre"] == "NCS Release" and yt_videos:
            yt_genre = find_genre_from_youtube(chosen_sc["title"], yt_videos)
            if yt_genre:
                chosen_sc["genre"] = yt_genre
                print(f"  Genre resolved via YouTube: {yt_genre}")

        if download_via_ytdlp(chosen_sc["url"], audio_file, use_cookies=False):
            save_to_history(chosen_sc["id"])
            return audio_file, chosen_sc["title"], chosen_sc["genre"]
        print("  Engine 3 failed.")
    else:
        print("  Engine 3: No SoundCloud tracks found.")

    # ── ENGINE 4: yt-dlp direct YouTube ───────────────
    print("\n>>> ENGINE 4: yt-dlp direct YouTube (last resort)")
    if yt_videos:
        fresh_yt2 = [v for v in yt_videos if v["id"] not in history]
        chosen_yt2 = fresh_yt2[0] if fresh_yt2 else yt_videos[0]
        print(f"  Trying: {chosen_yt2['title']}")

        if download_via_ytdlp(chosen_yt2["url"], audio_file, use_cookies=True):
            save_to_history(chosen_yt2["id"])
            return audio_file, chosen_yt2["title"], chosen_yt2["genre"]
        print("  Engine 4 failed.")

    print("\n\u274c All Engines Failed. No audio could be downloaded.")
    return None, None, None


if __name__ == "__main__":
    audio_path, title, genre = download_random_ncs_song()
    if title:
        print(f"\n\u2705 Success! Ready for visualizer: {title} [{genre}]")
