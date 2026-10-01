"""Deep, content-based format detection.

Never trusts the filename extension — a file renamed from .jpg to .png (or
.mp4 to .avi) and re-uploaded is still identified correctly.
"""
import json
import subprocess

import magic

IMAGE_MIME_TO_FORMAT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/tiff": "tiff",
    "image/bmp": "bmp",
    "image/x-ms-bmp": "bmp",
    "image/gif": "gif",
    "image/webp": "webp",
    "image/heic": "heic",
    "image/heif": "heic",
    "image/vnd.microsoft.icon": "ico",
    "image/x-icon": "ico",
    "image/svg+xml": "svg",
    "image/vnd.adobe.photoshop": "psd",
}

DOCUMENT_MIME_TO_FORMAT = {
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/rtf": "rtf",
    "text/rtf": "rtf",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.oasis.opendocument.text": "odt",
    "application/vnd.oasis.opendocument.spreadsheet": "ods",
    "application/vnd.oasis.opendocument.presentation": "odp",
    "application/vnd.ms-powerpoint": "ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "text/plain": "txt",
    "text/csv": "csv",
    "application/csv": "csv",
    "application/pdf": "pdf",
}


def sniff_mime(django_file) -> str:
    django_file.seek(0)
    head = django_file.read(4096)
    django_file.seek(0)
    return magic.from_buffer(head, mime=True)


def detect_image_format(django_file):
    mime = sniff_mime(django_file)
    return IMAGE_MIME_TO_FORMAT.get(mime), mime


def detect_document_format(django_file):
    mime = sniff_mime(django_file)
    fmt = DOCUMENT_MIME_TO_FORMAT.get(mime)
    if fmt is None and mime == "application/zip":
        # Legacy libmagic versions sometimes report bare OOXML files as zip.
        fmt = "docx"
    if fmt is None and mime in ("application/x-ole-storage", "application/CDFV2"):
        fmt = "doc"
    return fmt, mime


def _ffprobe(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "error",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            path,
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def detect_video_format(path):
    """Runs ffprobe against the file on disk and classifies the container.

    mp4/mov share the same ISO-BMFF demuxer, and mkv/webm share the same
    EBML demuxer, so format_name alone is ambiguous — brand/codec checks
    disambiguate them.
    """
    probe = _ffprobe(path)
    format_name = probe.get("format", {}).get("format_name", "")
    tags = probe.get("format", {}).get("tags", {}) or {}
    major_brand = (tags.get("major_brand") or tags.get("MAJOR_BRAND") or "").strip().lower()

    video_stream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in probe.get("streams", []) if s.get("codec_type") == "audio"), None)
    video_codec = (video_stream or {}).get("codec_name", "")
    audio_codec = (audio_stream or {}).get("codec_name", "")

    if "avi" in format_name:
        return "avi", format_name

    if "matroska" in format_name or "webm" in format_name:
        webm_video = video_codec in ("vp8", "vp9", "av1")
        webm_audio = audio_codec in ("opus", "vorbis") or audio_stream is None
        if webm_video and webm_audio:
            return "webm", format_name
        return "mkv", format_name

    if "mov" in format_name or "mp4" in format_name:
        if major_brand.startswith("qt"):
            return "mov", format_name
        return "mp4", format_name

    return None, format_name
