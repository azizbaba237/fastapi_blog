# import uuid
# from io import BytesIO
# from pathlib import Path

# from PIL import Image, ImageOps

# PROFILE_PICS_DIR = Path("media/profile_pics")


# def process_profile_image(content: bytes) -> str:
#     with Image.open(BytesIO(content)) as original:
#         img = ImageOps.exif_transpose(original)

#         img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS)

#         if img.mode in ("RGBA", "LA", "P"):
#             img = img.convert("RGB")

#         filename = f"{uuid.uuid4().hex}.jpg"
#         filepath = PROFILE_PICS_DIR / filename

#         PROFILE_PICS_DIR.mkdir(parents=True, exist_ok=True)

#         img.save(filepath, "JPEG", quality=85, optimize=True)

#     return filename


# def delete_profile_image(filename: str | None) -> None:
#     if filename is None:
#         return

#     filepath = PROFILE_PICS_DIR / filename
#     if filepath.exists():
#         filepath.unlink()




from io import BytesIO
import cloudinary
import cloudinary.uploader
from PIL import Image, ImageOps
from config import settings

# Configure Cloudinary once at import time
cloudinary.config(
    cloud_name=settings.cloudinary_cloud_name,
    api_key=settings.cloudinary_api_key,
    api_secret=settings.cloudinary_api_secret.get_secret_value(),
    secure=True,
)


def process_profile_image(content: bytes) -> str:
    """
    Process the image with Pillow, then upload it to Cloudinary.
    Returns the Cloudinary secure URL (stored in the database).
    """
    with Image.open(BytesIO(content)) as original:
        # Fix orientation based on EXIF data (prevents upside-down photos)
        img = ImageOps.exif_transpose(original)

        # Crop and resize to a 300x300 square
        img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS)

        # Convert to RGB — Cloudinary JPEG upload doesn't support transparency
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")

        # Save the processed image into memory (not on disk)
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85, optimize=True)
        buffer.seek(0)

    # Upload the in-memory image to Cloudinary
    result = cloudinary.uploader.upload(
        buffer,
        folder="fastapi_blog/profile_pics",
        resource_type="image",
    )

    # Return the permanent URL — this is what gets stored in the database
    return result["secure_url"]


def delete_profile_image(image_url: str | None) -> None:
    """
    Delete a profile picture from Cloudinary using its URL.
    Extracts the public_id from the URL before calling the API.
    """
    if image_url is None:
        return

    try:
        # Cloudinary URL format:
        # https://res.cloudinary.com/<cloud>/image/upload/v123/fastapi_blog/profile_pics/<id>.jpg
        # We need to extract: fastapi_blog/profile_pics/<id>  (without extension)
        parts = image_url.split("/upload/")
        if len(parts) != 2:
            return

        path = parts[1]

        # Remove the version prefix (v1234567890/) if present
        if path.startswith("v") and "/" in path:
            path = path.split("/", 1)[1]

        # Remove the file extension (.jpg)
        public_id = path.rsplit(".", 1)[0]

        cloudinary.uploader.destroy(public_id)

    except Exception:
        # Never crash the app if image deletion fails
        pass