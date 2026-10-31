"""One immutable original per byte fingerprint; names are presentation, not identity."""
import hashlib
import re
import time
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import unquote, urlparse
from api.config import ROOT


@contextmanager
def document_lock(folder):
    lock=folder/'.write-lock'
    for _ in range(100):
        try:
            lock.mkdir()
            break
        except FileExistsError:
            time.sleep(0.05)
        except PermissionError as exc:
            # Windows may report a just-deleted lock directory as access denied
            # while another thread's directory handle is still closing.
            if getattr(exc, 'winerror', None) not in (5, 32):
                raise
            time.sleep(0.05)
    else:
        raise ValueError('Document store busy; retry the download')
    try:
        yield
    finally:
        lock.rmdir()


def file_extension(raw):
    if raw.startswith(b'%PDF-'):
        return '.pdf'
    if raw.startswith(b'PK\x03\x04'):
        return '.docx'
    if raw.startswith(bytes.fromhex('d0cf11e0a1b11ae1')):
        return '.doc'
    raise ValueError('Download is not a supported DOC, DOCX or PDF file')


def store_document(raw, url, filename=None):
    extension = file_extension(raw)
    sha = hashlib.sha256(raw).hexdigest()
    original_name = Path((filename or unquote(urlparse(url).path).rsplit('/', 1)[-1] or 'document').replace('\\', '/')).name
    stem = re.sub(r'[^\w.-]+', '_', Path(original_name).stem, flags=re.UNICODE).strip('._')[:70] or 'document'
    folder = ROOT/'data/forms/_objects'/sha
    folder.mkdir(parents=True, exist_ok=True)
    # An identical file obtained under another name reuses the first stored name.
    with document_lock(folder):
        existing = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in ('.doc', '.docx', '.pdf') and hashlib.sha256(p.read_bytes()).hexdigest() == sha]
        target = existing[0] if existing else folder/f'{stem}--{sha[:12]}{extension}'
        if not target.exists():
            temporary=folder/'.download.tmp'
            temporary.write_bytes(raw)
            temporary.replace(target)
        elif hashlib.sha256(target.read_bytes()).hexdigest() != sha:
            raise ValueError('Stored original fingerprint mismatch')
    return dict(sha256=sha, raw_path=target.relative_to(ROOT).as_posix(), original_filename=original_name, stored_filename=target.name)
