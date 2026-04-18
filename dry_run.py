from video_compiler import create_music_video

success = create_music_video(
    audio_path="TANTRON, More Plastic - CERBERUS ｜ DnB ｜ NCS - Copyright Free Music [C07xJuLrmfg].wav",
    image_path="dummy.jpg", 
    output_path="PREVIEW_SHORTS_UI.mp4",
    video_type="short",
    song_title="TANTRON, More Plastic - CERBERUS"
)

if success:
    print("SUCCESS: Preview generated at PREVIEW_SHORTS_UI.mp4")
else:
    print("FAILED")
