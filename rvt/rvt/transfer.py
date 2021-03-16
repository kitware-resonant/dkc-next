from __future__ import annotations

from datetime import datetime
import logging
import os
from pathlib import Path

from rich.progress import track

from rvt.models import RemoteFile, RemoteFolder

logger = logging.getLogger(__name__)

CHUNK_SIZE = 32 * 1024 * 1024


def _maybe_download_file(ctx, rfile: RemoteFile, dest: Path, skip_existing=True):
    lfilename = dest / rfile.name

    if (
        skip_existing
        and lfilename.exists()
        and lfilename.stat().st_mtime == rfile.modified.timestamp()
    ):
        logger.debug(f'skipping file {lfilename} (same mtime).')
        ctx.skipped_files.append(rfile)
        return

    logger.debug(f'downloading {lfilename}')
    with open(lfilename, 'wb') as lfile:
        resp = rfile.download(ctx)
        resp.raise_for_status()
        for chunk in track(
            resp.iter_content(chunk_size=CHUNK_SIZE),
            total=rfile.size / CHUNK_SIZE,
            description=rfile.name,
        ):
            lfile.write(chunk)
    os.utime(lfilename, (datetime.now().timestamp(), rfile.modified.timestamp()))
    ctx.synced_files.append(rfile)


def download(ctx, source: RemoteFolder, dest: Path, skip_existing=True):
    dest.mkdir(exist_ok=True)

    for roots, folders, files in source.walk(ctx):
        root_path = Path(dest, *[r.name for r in roots[1:]])
        root_path.mkdir(exist_ok=True)

        for rfile in files:
            _maybe_download_file(ctx, rfile, root_path, skip_existing)

        for rfolder in folders:
            lfolder = root_path / rfolder.name
            lfolder.mkdir(exist_ok=True)


def _maybe_upload_file(ctx, rfolder: RemoteFolder, lpath: Path):
    rfile = rfolder.file_by_name(ctx, lpath.name)

    if rfile and lpath.stat().st_mtime == rfile.modified.timestamp():
        logger.debug(f'skipping file {lpath} (same mtime).')
        ctx.skipped_files.append(rfile)
        return

    logger.info(f'uploading {lpath}')
    with open(lpath, 'rb') as stream:
        uploaded_file = ctx.s3ff.upload_file(stream, lpath.name, 'core.File.blob')['field_value']

        if rfile:
            # TODO: how to changed modified?
            rfile.delete(ctx)

        RemoteFile.create(ctx, lpath.name, uploaded_file, lpath.stat().st_size, rfolder)

    ctx.synced_files.append(rfile)


def upload(ctx, source: Path, dest: RemoteFolder):
    def get_or_create_remote_path(path: Path, parent: RemoteFolder) -> RemoteFolder:
        for part in path.parts:
            parent = RemoteFolder.get_or_create(ctx, part, parent)
        return parent

    for root, folders, files in os.walk(source):
        lpath = Path(root)
        paths = root.split('/')[1:]
        if not paths:
            root = dest
        else:
            root = get_or_create_remote_path(Path(*paths), dest)

        for lfolder in folders:
            RemoteFolder.get_or_create(ctx, lfolder, root)

        for lfile in files:
            _maybe_upload_file(ctx, root, lpath / Path(lfile))
