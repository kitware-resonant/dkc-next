from __future__ import annotations

from datetime import datetime
import logging
from typing import Iterable, Optional

import humanize
from pydantic import BaseModel
import requests
from rich.logging import RichHandler

from rvt.utils import pager, results

FORMAT = "%(message)s"
logging.basicConfig(format=FORMAT, datefmt="[%X]", handlers=[RichHandler()])
logger = logging.getLogger(__name__)

__version__ = '0.0000'


class RemoteFolder(BaseModel):
    id: int
    name: str
    size: int

    def __hash__(self):
        return hash((type(self),) + tuple(self.__dict__.values()))

    def ls_repr(self) -> str:
        size = humanize.naturalsize(self.size, gnu=True)
        return f'id={self.id} size={size} {self.name}'

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

    def rm(self, ctx):
        r = ctx.session.delete(f'folders/{self.id}')
        r.raise_for_status()

    # TODO: note that this is expensive
    def walk(self, ctx):
        yield ([self], self.folders(ctx), self.files(ctx))

        for child_folder in self.folders(ctx):
            for roots, folders, files in child_folder.walk(ctx):
                roots.insert(0, self)
                yield roots, folders, files

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


class DoesNotExistException(Exception):
    pass


class RemoteFile(BaseModel):
    id: int
    name: str
    size: int
    modified: datetime

    @classmethod
    def from_id(cls, ctx, id) -> RemoteFile:
        r = ctx.session.get(f'files/{id}')
        r.raise_for_status()
        return cls(**r.json())

    def download(self, ctx) -> requests.Response:
        return ctx.session.get(f'files/{self.id}/download', stream=True)

    def delete(self, ctx) -> requests.Response:
        r = ctx.session.delete(f'files/{self.id}')
        r.raise_for_status()
        return r

    def ls_repr(self) -> str:
        size = humanize.naturalsize(self.size, gnu=True)
        return f'id={self.id} size={size} {self.name}'

    @classmethod
    def create(
        cls, ctx: CliContext, name: str, blob: str, size: int, parent: RemoteFolder, **kwargs
    ):
        r = ctx.session.post(
            'files',
            data={**{'name': name, 'folder': parent.id, 'blob': blob, 'size': size}, **kwargs},
        )
        r.raise_for_status()
        return cls(**r.json())
