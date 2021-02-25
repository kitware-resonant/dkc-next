from __future__ import annotations

from datetime import datetime
import logging
import os
from pathlib import Path
import pdb
import platform
import sys
import traceback
from typing import Any, Iterable, List, Optional
from urllib.parse import urlparse, urlunparse

from cachetools import cached
from cachetools.keys import hashkey
import click
from click import ClickException
from pydantic import BaseModel
import requests
from requests_toolbelt.sessions import BaseUrlSession
import rich
from rich.logging import RichHandler
from rich.tree import Tree
from s3_file_field_client import S3FileFieldClient
import toml
from xdg import BaseDirectory

from rvt.types import RemoteOrLocalPath, RemotePath
from rvt.utils import pager, results

FORMAT = "%(message)s"
logging.basicConfig(format=FORMAT, datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger(__name__)

__version__ = '0.0000'


class RemoteFolder(BaseModel):
    id: int
    name: str

    def __hash__(self):
        return hash((type(self),) + tuple(self.__dict__.values()))

    @classmethod
    def from_id(cls, ctx, id) -> RemoteFolder:
        r = ctx.session.get(f'folders/{id}')
        r.raise_for_status()
        return cls(**r.json())

    @classmethod
    # @cached(cache={}, key=lambda cls, ctx, name, parent: hashkey(name, parent))
    def get_or_create(cls, ctx: CliContext, name: str, parent: RemoteFolder):
        r = ctx.session.get('folders', params={'parent': parent.id, 'name': name})
        if r.ok and r.json()['results']:
            return cls(**r.json()['results'][0])
        else:
            r = ctx.session.post('folders', data={'name': name, 'parent': parent.id})
            r.raise_for_status()
            return cls(**r.json())

    def folders(self, ctx) -> Iterable[RemoteFolder]:
        for result in results(pager(ctx.session, f'folders?parent={self.id}')):
            yield RemoteFolder(**result)

    def files(self, ctx) -> Iterable[RemoteFile]:
        for result in results(pager(ctx.session, f'files?folder={self.id}')):
            yield RemoteFile(**result)

    def file_by_name(self, ctx, name: str) -> Optional[RemoteFile]:
        r = ctx.session.get(
            'files',
            params={
                'folder': self.id,
                'name': name,
            },
        )
        r.raise_for_status()
        if r.json()['count'] == 0:
            return None
        else:
            return RemoteFile(**r.json()['results'][0])


class RemoteFile(BaseModel):
    id: int
    name: str
    size: int
    modified: datetime

    def download(self, ctx) -> requests.Response:
        return ctx.session.get(f'files/{self.id}/download')

    @classmethod
    def create(cls, ctx: CliContext, name: str, blob: str, parent: RemoteFolder, **kwargs):
        r = ctx.session.post(
            'files', data={**{'name': name, 'folder': parent.id, 'blob': blob}, **kwargs}
        )
        r.raise_for_status()
        return cls(**r.json())

    def update_blob(self, field_value: str):
        r = ctx.session.patch(
            f'files/{self.id}',
            data={
                'blob': field_value,
            },
        )
        r.raise_for_status()


class RvtSession(BaseUrlSession):
    page_size = 50

    def __init__(self, base_url: str):
        base_url = f'{base_url.rstrip("/")}/'  # tolerate input with or without trailing slash
        super().__init__(base_url=base_url)
        self.headers.update(
            {
                'User-agent': f'rvt/{__version__}',
                'Accept': 'application/json',
                'Authorization': 'Basic ZGFuLmxhbWFubmFAa2l0d2FyZS5jb206cGFzc3dvcmQ=',
            }
        )


class CliContext(BaseModel):
    session: RvtSession
    s3ff: S3FileFieldClient
    url: str
    config: Path
    skipped_files: List[RemoteFile] = []
    synced_files: List[RemoteFile] = []

    class Config:
        arbitrary_types_allowed = True


def default_url(url):
    def f():
        config = Path(BaseDirectory.load_first_config('rvt')) / 'config'

        if os.environ.get('RVT_URL'):
            logger.debug(f'using {os.environ["RVT_URL"]} as url from the environ')
            return os.environ['RVT_URL']
        elif config.exists():
            logger.debug(f'loading config file {config}')
            with open(config) as infile:
                profile = toml.load(infile)
            logger.debug(f'using {profile["default"]["url"]} as url from the config file')
            return profile['default']['url']
        else:
            return url

    return f


@click.group()
@click.option('--url', default=default_url('http://127.0.0.1:8000/api/v2/'))
@click.option('-v', '--verbose', count=True)
@click.version_option()
@click.pass_context
def cli(ctx, url, verbose: int):
    if verbose >= 2:
        logger.setLevel(logging.DEBUG)
    elif verbose >= 1:
        logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.WARN)

    session = RvtSession(url)
    ctx.obj = CliContext(
        session=session,
        url=url.rstrip('/'),
        config=BaseDirectory.save_config_path('rvt'),
        s3ff=S3FileFieldClient(url.rstrip('/') + '/s3-upload/', session),
    )


def main():
    try:
        cli()
    except Exception:
        if os.environ.get('DEBUG'):
            _, _, tb = sys.exc_info()
            traceback.print_exc()
            pdb.post_mortem(tb)
            return

        click.echo(
            click.style(
                'The following unexpected error occurred while attempting your operation:\n',
                fg='red',
            ),
            err=True,
        )

        click.echo(traceback.format_exc(), err=True)

        click.echo(f'rvt:     v{__version__}', err=True)
        click.echo(f'python:  v{platform.python_version()}', err=True)
        click.echo(f'time:    {datetime.utcnow().isoformat()}', err=True)
        click.echo(f'os:      {platform.platform()}', err=True)
        click.echo(f'command: rvt {" ".join(sys.argv[1:])}\n', err=True)

        click.echo(
            click.style(
                'This is a bug in rvt and should be reported. You can open an issue below: ',
                fg='yellow',
            ),
            err=True,
        )
        click.echo(
            'https://github.com/girder/dkc-next/issues/new',
            err=True,
        )


@cli.command(name='ls', help='list contents of a dkc folder')
@click.argument('folder', type=RemotePath())
@click.option('--tree', default=False, is_flag=True, help='display folder as a hierarchical tree')
@click.pass_obj
def ls(ctx, folder, tree):
    def _ls(folder: dict, tree=None, prefix='.'):
        for child_folder in results(pager(ctx.session, f'folders?parent={folder["id"]}')):
            branch = tree.add(f'[{child_folder["id"]}] {child_folder["name"]}' if tree else None)
            if not tree:
                click.echo(f'{child_folder["id"]}\t{prefix}/{child_folder["name"]}/')

            for child_file in results(pager(ctx.session, f'files?folder={child_folder["id"]}')):
                if not tree:
                    click.echo(f'{child_file["id"]}\t{prefix}/{child_file["name"]}')
                else:
                    tree.add(f'[{child_file["id"]}] {child_file["name"]}')

            _ls(child_folder, branch, f'{prefix}/{child_folder["name"]}')

        for child_file in results(pager(ctx.session, f'files?folder={folder["id"]}')):
            if not tree:
                click.echo(f'{child_file["id"]}\t{prefix}/{child_file["name"]}')
            else:
                tree.add(f'[{child_file["id"]}] {child_file["name"]}')

    tree = Tree(label=folder.name) if tree else None
    _ls(folder.dict(), tree, folder.name)

    if tree:
        rich.print(tree)


@cli.command(name='sync', help='sync a directory')
@click.argument('source', type=RemoteOrLocalPath())
@click.argument('dest', type=RemoteOrLocalPath())
@click.pass_obj
def sync(ctx, source, dest):
    if isinstance(source, RemoteFolder) and isinstance(dest, Path):
        download(ctx, source, dest)
        click.echo(f'skipped files: {len(ctx.skipped_files)}')
        click.echo(f'synced files:  {len(ctx.synced_files)}')
    elif isinstance(source, Path) and isinstance(dest, RemoteFolder):
        upload(ctx, source, dest)
        click.echo(f'skipped files: {len(ctx.skipped_files)}')
        click.echo(f'synced files:  {len(ctx.synced_files)}')
    else:
        raise ClickException(
            'one of source|dest must be a dkc:// folder and the other must be a local path'
        )


@cli.command(name='configure', help='configure rvt')
@click.pass_obj
def configure(ctx):
    def url_from_prompt():

        url = click.prompt('DKC URL (e.g. data.kitware.com)').strip()
        o = urlparse(url)
        scheme = 'https' if o.scheme == '' else o.scheme
        url = urlunparse([scheme, o.netloc, o.path, o.params, o.query, o.fragment])
        url = url.rstrip('/')
        if not url.endswith('/api/v2'):
            url += '/api/v2'
        return url

    while True:
        url = url_from_prompt()
        try:
            r = requests.get(url + '/files')
            r.raise_for_status()
            break
        except Exception:  # TODO: scope to requests
            click.echo('That URL doesn\'t appear to work.')

    with open(ctx.config / 'config', 'w') as target:
        toml.dump({'default': {'url': url}}, target)


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


if __name__ == '__main__':
    main()
