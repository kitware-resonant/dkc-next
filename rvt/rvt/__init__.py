from __future__ import annotations

from datetime import datetime
import logging
import os
from pathlib import Path
import pdb
import platform
import sys
import traceback
from typing import List, Optional
from urllib.parse import urlparse, urlunparse

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

from rvt.models import RemoteFile, RemoteFolder
from rvt.transfer import download, upload
from rvt.types import RemoteOrLocalPath, RemotePath
from rvt.utils import pager, results

FORMAT = "%(message)s"
logging.basicConfig(format=FORMAT, datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger(__name__)

__version__ = '0.0000'


class RvtSession(BaseUrlSession):
    page_size = 50

    def __init__(self, base_url: str, auth_header: Optional[str] = None):
        base_url = f'{base_url.rstrip("/")}/'  # tolerate input with or without trailing slash
        super().__init__(base_url=base_url)
        self.headers.update(
            {
                'User-agent': f'rvt/{__version__}',
                'Accept': 'application/json',
            }
        )

        if auth_header:
            self.headers['Authorization'] = auth_header


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
        config = Path(click.get_app_dir('rvt')) / 'config'

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

    config_path = Path(click.get_app_dir('rvt'))
    config_file = config_path / 'config'
    os.makedirs(config_path, exist_ok=True)

    auth_header = None
    if config_file.exists():
        with open(config_file) as infile:
            profile = toml.load(infile)

        if profile.get('default', {}).get('auth'):
            auth_header = profile['default']['auth']

    session = RvtSession(url, auth_header)
    ctx.obj = CliContext(
        session=session,
        url=url.rstrip('/'),
        config=config_file,
        s3ff=S3FileFieldClient(url.rstrip('/') + '/s3-upload/', session),
    )


@cli.command(name='ls', help='list contents of a dkc folder')
@click.argument('folder', type=RemotePath())
@click.option('--tree', default=False, is_flag=True, help='display folder as a hierarchical tree')
@click.pass_obj
def ls(ctx, folder, tree):
    def _ls(folder: dict, tree=None, prefix='.'):
        for child_folder in results(pager(ctx.session, f'folders?parent={folder["id"]}')):
            if tree:
                branch = tree.add(
                    f'[{child_folder["id"]}] {child_folder["name"]}' if tree else None
                )
            else:
                branch = None
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


if __name__ == '__main__':
    main()
