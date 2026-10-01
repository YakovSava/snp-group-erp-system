import subprocess

TARGET_CODEC_ARGS = {
    "mp4": ["-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-movflags", "+faststart"],
    "webm": ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32", "-c:a", "libopus"],
}


def convert_video(source_path, target_format, output_path):
    codec_args = TARGET_CODEC_ARGS.get(target_format.lower())
    if codec_args is None:
        raise ValueError(f"Unsupported target format: {target_format}")

    cmd = ["ffmpeg", "-y", "-i", source_path, *codec_args, output_path]
    subprocess.run(cmd, capture_output=True, check=True, timeout=1800)
