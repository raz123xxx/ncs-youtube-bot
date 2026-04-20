import os
import requests
import subprocess

SETTINGS = {
    "stability": 0.50,
    "similarity_boost": 0.75,
    "style": 0.25,
    "use_speaker_boost": True,
    "speed": 1.10
}


def generate_voice(text: str, output_path: str, voice_id: str, api_key: str) -> str:
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": api_key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
        json={
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": SETTINGS["stability"],
                "similarity_boost": SETTINGS["similarity_boost"],
                "style": SETTINGS["style"],
                "use_speaker_boost": SETTINGS["use_speaker_boost"]
            }
        },
        timeout=30
    )
    if r.status_code != 200:
        raise Exception(f"ElevenLabs error {r.status_code}: {r.text}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(r.content)
    print(f"Voice saved: {output_path}")

    fast_path = output_path.replace(".mp3", "_fast.mp3")
    subprocess.run(
        ["ffmpeg", "-y", "-i", output_path, "-filter:a", f"atempo={SETTINGS['speed']}", fast_path],
        check=True, capture_output=True
    )
    return fast_path
