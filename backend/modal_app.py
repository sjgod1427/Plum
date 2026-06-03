"""
Modal deployment for Plum OPD Claims API.

First-time setup (run once):
    modal secret create plum-secrets OPENAI_API_KEY=sk-...

Deploy (production):
    cd backend && modal deploy modal_app.py

Serve (hot-reload for testing):
    cd backend && modal serve modal_app.py
"""

import modal

VOLUME_MOUNT = "/data"

# ── Persistent volume — stores SQLite DB, ChromaDB, uploaded files ────────────
volume = modal.Volume.from_name("plum-data", create_if_missing=True)

# ── Container image ───────────────────────────────────────────────────────────
image = (
    modal.Image.debian_slim(python_version="3.12")
    # System libs required by OpenCV (EasyOCR dependency)
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install(
        "fastapi==0.115.0",
        "uvicorn[standard]==0.30.6",
        "sqlmodel==0.0.21",
        "openai>=1.50.0",
        "chromadb==0.5.15",
        "python-multipart==0.0.12",
        "python-dotenv==1.0.1",
        "pydantic-settings==2.5.2",
        "pymupdf==1.24.11",
        "pillow==10.4.0",
        "easyocr",
        "requests==2.32.3",
    )
    # Pre-download EasyOCR models at build time so first request isn't slow
    .run_commands(
        "python -c \"import easyocr; easyocr.Reader(['en'], gpu=False, verbose=False)\""
    )
    # Bake entire backend directory into the image (must come last per Modal rules)
    .add_local_dir(".", "/app")
)

# ── Modal app ─────────────────────────────────────────────────────────────────
app = modal.App("plum-claims-api", image=image)


@app.function(
    secrets=[modal.Secret.from_name("plum-secrets")],
    volumes={VOLUME_MOUNT: volume},
    memory=2048,       # EasyOCR needs ~1.5GB
    timeout=300,       # 5 min — allow for OCR + adjudication on cold start
)
@modal.concurrent(max_inputs=10)
@modal.asgi_app()
def fastapi_app():
    import os
    import sys

    sys.path.insert(0, "/app")

    # Point all paths at the persistent volume
    os.environ.setdefault("DATABASE_URL",       f"sqlite:////{VOLUME_MOUNT}/claims.db")
    os.environ.setdefault("CHROMA_PERSIST_DIR",  f"{VOLUME_MOUNT}/chroma_db")
    os.environ.setdefault("UPLOAD_DIR",          f"{VOLUME_MOUNT}/uploads")
    os.environ.setdefault("POLICY_TERMS_PATH",   "/app/policy_terms.json")
    os.environ.setdefault("ALLOWED_ORIGINS",     "*")

    from main import app as fastapi_application
    return fastapi_application
