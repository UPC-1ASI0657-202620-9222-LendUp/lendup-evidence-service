from enum import Enum


class EvidenceStage(str, Enum):
    DELIVERY = "ENTREGA"
    RETURN = "DEVOLUCION"
    INCIDENT = "INCIDENCIA"


class EvidenceType(str, Enum):
    PHOTO = "FOTO"
    VIDEO = "VIDEO"
    NOTE = "OBSERVACION"


def media_mime(data: bytes, declared: str = "") -> str:
    if not data or len(data) > 5 * 1024 * 1024:
        raise ValueError("Cada archivo debe pesar hasta 5 MB")
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[4:8] == b"ftyp":
        return "video/quicktime" if declared == "video/quicktime" else "video/mp4"
    if data.startswith(b"\x1a\x45\xdf\xa3"):
        return "video/webm"
    raise ValueError("Usa archivos JPG, PNG, WebP, MP4, WebM o MOV")
