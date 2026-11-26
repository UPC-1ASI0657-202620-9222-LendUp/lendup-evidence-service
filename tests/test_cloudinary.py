from unittest.mock import patch
import pytest
from fastapi import HTTPException
from app.infrastructure.cloudinary.storage import CloudinaryStorage


def test_disabled(monkeypatch):
    monkeypatch.setenv("CLOUDINARY_ENABLED", "false")
    with pytest.raises(HTTPException) as error:
        CloudinaryStorage()
    assert error.value.status_code == 503


def test_upload(monkeypatch):
    for key, value in {"CLOUDINARY_ENABLED": "true", "CLOUDINARY_CLOUD_NAME": "testcloud",
                       "CLOUDINARY_API_KEY": "test-key", "CLOUDINARY_API_SECRET": "test-secret"}.items():
        monkeypatch.setenv(key, value)
    with patch("cloudinary.uploader.upload") as upload:
        upload.return_value = {"public_id": "lendup/test", "secure_url": "https://res.cloudinary.com/testcloud/image/upload/lendup/test.jpg"}
        asset = CloudinaryStorage().upload(b"fake", "image/jpeg", "lendup/test", "lendup/evidencias/entrega")
        assert asset.public_id == "lendup/test"
        assert upload.call_args.kwargs["overwrite"] is False
        assert upload.call_args.kwargs["resource_type"] == "image"
