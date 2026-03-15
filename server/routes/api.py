from fastapi import APIRouter
import os

router = APIRouter()

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "projects", "test_project", "media")


@router.get("/api/images")
def list_images():

    files = os.listdir(UPLOAD_FOLDER)

    images = []

    for f in files:
        if f.lower().endswith((".jpg", ".jpeg", ".png")):
            images.append(f)

    return images
