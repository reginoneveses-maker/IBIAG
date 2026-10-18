"""Bound imports before parsers allocate memory or persist records."""
import io
import zipfile
from fastapi import HTTPException

MAX_IMPORT_BYTES = 50 * 1024 * 1024
MAX_EXPANDED_BYTES = 100 * 1024 * 1024


async def read_import(file):
    raw = await file.read(MAX_IMPORT_BYTES + 1)
    if not raw or len(raw) > MAX_IMPORT_BYTES:
        raise HTTPException(413, "Arquivo vazio ou acima do limite de 50 MB")
    if zipfile.is_zipfile(io.BytesIO(raw)):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > 2000 or sum(item.file_size for item in entries) > MAX_EXPANDED_BYTES:
                raise HTTPException(413, "Conteúdo descompactado excede o limite permitido")
    return raw
