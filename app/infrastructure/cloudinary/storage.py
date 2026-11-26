import logging
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

import cloudinary.uploader
from fastapi import HTTPException

from app.shared.config import Settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Asset:
    public_id: str
    url: str


class CloudinaryStorage:
    def __init__(self):
        settings = Settings()
        if not settings.cloudinary_enabled or not re.fullmatch(r"[A-Za-z0-9_-]+", settings.cloudinary_cloud_name) or not settings.cloudinary_api_key or not settings.cloudinary_api_secret:
            raise HTTPException(503, "Cloudinary no configurado")
        self.options = dict(cloud_name=settings.cloudinary_cloud_name,
                            api_key=settings.cloudinary_api_key,
                            api_secret=settings.cloudinary_api_secret,
                            secure=True, timeout=40)

    def upload(self, data: bytes, mime: str, public_id: str, folder: str) -> Asset:
        video = mime.startswith("video/")
        try:
            result = cloudinary.uploader.upload(
                data, public_id=public_id, asset_folder=folder,
                resource_type="video" if video else "image",
                overwrite=False, allowed_formats=["mp4", "webm", "mov"] if video else ["jpg", "png", "webp"],
                **self.options,
            )
            url = result["secure_url"]
            parts = urlsplit(url)
            if result["public_id"] != public_id or parts.scheme != "https" or parts.hostname != "res.cloudinary.com" or not parts.path.startswith("/" + self.options["cloud_name"] + "/"):
                raise ValueError("Invalid asset")
            return Asset(public_id, url)
        except Exception:
            raise HTTPException(502, "Cloudinary no pudo procesar el archivo") from None

    def delete(self, public_id: str, video: bool) -> None:
        try:
            result = cloudinary.uploader.destroy(public_id, resource_type="video" if video else "image",
                                                 invalidate=True, **self.options)
            if result.get("result") not in ("ok", "not found"):
                raise ValueError("Deletion failed")
        except Exception:
            logger.warning("Cloudinary cleanup failed for asset %s", public_id)
