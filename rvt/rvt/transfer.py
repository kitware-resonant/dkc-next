from __future__ import annotations

from datetime import datetime
import logging
import os
from pathlib import Path

import click

from rvt.models import RemoteFile, RemoteFolder

logger = logging.getLogger(__name__)


def _maybe_download_file(ctx, rfile: RemoteFile, dest: Path):
    lfilename = dest / rfile.name

    if lfilename.exists() and lfilename.stat().st_mtime == rfile.modified.timestamp():
        logger.debug(f'skipping file {lfilename} (same mtime).')
        ctx.skipped_files.append(rfile)
        return

    logger.info(f'downloading {lfilename}')
    with open(lfilename, 'wb') as lfile:
        lfile.write(rfile.download(ctx).content)
    os.utime(lfilename, (datetime.now().timestamp(), rfile.modified.timestamp()))
    ctx.synced_files.append(rfile)


def download(ctx, source: RemoteFolder, dest: Path):
    def _download(source: RemoteFolder, dest: Path):
        dest.mkdir(exist_ok=True)

        for rfile in source.files(ctx):
            _maybe_download_file(ctx, rfile, dest)

        for rfolder in source.folders(ctx):
            lfolder = dest / rfolder.name
            lfolder.mkdir(exist_ok=True)

            for rfile in rfolder.files(ctx):
                _maybe_download_file(ctx, rfile, lfolder)

            _download(rfolder, lfolder)

    _download(source, dest)


def _maybe_upload_file(ctx, rfolder: RemoteFolder, lpath: Path):
    rfile = rfolder.file_by_name(ctx, lpath.name)

    if lpath.exists() and rfile and lpath.stat().st_mtime == rfile.modified.timestamp():
        logger.debug(f'skipping file {lpath} (same mtime).')
        ctx.skipped_files.append(rfile)
        return

    logger.info(f'uploading {lpath}')
    with open(lpath, 'wb') as stream:
        uploaded_file = ctx.s3ff.upload_file(stream, lpath.name, 'core.File.blob')['field_value']

        if rfile:
            rfile.update_blob(uploaded_file)
        else:
            print('create remote file')

    ctx.synced_files.append(rfile)


def upload(ctx, source: Path, dest: RemoteFolder):
    def _upload(source: Path, dest: RemoteFolder):
        logger.info(f'creating {source.name} under {dest}')
        for lchild in source.iterdir():
            print(lchild)
            if lchild.is_file():
                _maybe_upload_file(ctx, dest, lchild)
            elif lchild.is_dir():
                _upload(lchild, dest)
            else:
                click.echo(f'ignoring {lchild}')

    _upload(source, dest)
