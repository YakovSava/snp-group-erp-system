import os
import tempfile

from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone

from .models import ConversionHistory, ConversionJob
from .services import detect, document, image, video


@shared_task
def process_conversion_job(job_id):
    try:
        job = ConversionJob.objects.select_related("user").get(pk=job_id)
    except ConversionJob.DoesNotExist:
        return

    job.status = ConversionJob.STATUS_PROCESSING
    job.save(update_fields=["status"])

    try:
        if job.kind == ConversionJob.KIND_IMAGE:
            _process_image(job)
        elif job.kind == ConversionJob.KIND_VIDEO:
            _process_video(job)
        elif job.kind == ConversionJob.KIND_DOCUMENT:
            _process_document(job)
        else:
            raise ValueError(f"Unknown job kind: {job.kind}")
    except Exception as exc:  # noqa: BLE001 - any conversion failure is reported to the user, not raised
        job.status = ConversionJob.STATUS_FAILED
        job.error_message = str(exc)[:2000]
        job.save(update_fields=["status", "error_message"])
        ConversionHistory.objects.create(
            user=job.user,
            action=(
                f"Не удалось конвертировать {os.path.basename(job.source_file.name)} "
                f"в {job.target_format}: {job.error_message}"
            ),
        )
        return

    job.status = ConversionJob.STATUS_DONE
    job.save(update_fields=["status"])
    ConversionHistory.objects.create(
        user=job.user,
        action=(
            f"Конвертировал {os.path.basename(job.source_file.name)} "
            f"({job.detected_source_format}) в {job.target_format}"
        ),
    )


def _result_filename(job):
    base = os.path.splitext(os.path.basename(job.source_file.name))[0]
    return f"{base}.{job.target_format}"


def _process_image(job):
    fmt, mime = detect.detect_image_format(job.source_file)
    if fmt is None:
        raise ValueError(f"Неизвестный или неподдерживаемый формат изображения ({mime}).")
    job.detected_source_format = fmt
    job.save(update_fields=["detected_source_format"])

    result_bytes = image.convert_image(job.source_file, fmt, job.target_format)
    job.result_file.save(_result_filename(job), ContentFile(result_bytes), save=True)


def _process_video(job):
    fmt, format_name = detect.detect_video_format(job.source_file.path)
    if fmt is None:
        raise ValueError(f"Неизвестный или неподдерживаемый формат видео ({format_name}).")
    job.detected_source_format = fmt
    job.save(update_fields=["detected_source_format"])

    filename = _result_filename(job)
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = os.path.join(tmp_dir, filename)
        video.convert_video(job.source_file.path, job.target_format, output_path)
        with open(output_path, "rb") as fh:
            job.result_file.save(filename, ContentFile(fh.read()), save=True)


def _process_document(job):
    fmt, mime = detect.detect_document_format(job.source_file)
    if fmt is None:
        raise ValueError(f"Неизвестный или неподдерживаемый формат документа ({mime}).")
    job.detected_source_format = fmt
    job.save(update_fields=["detected_source_format"])

    result_bytes = document.convert_document(job.source_file.path, job.target_format)
    job.result_file.save(_result_filename(job), ContentFile(result_bytes), save=True)


@shared_task
def cleanup_expired_conversion_jobs():
    expired = ConversionJob.objects.filter(expires_at__lte=timezone.now())
    for job in expired:
        job.source_file.delete(save=False)
        if job.result_file:
            job.result_file.delete(save=False)
    expired.delete()
