from pathlib import Path

import click


class RemotePath(click.ParamType):
    name = "remote-path"

    def convert(self, value, param, ctx):
        from rvt import RemoteFolder

        if not value.startswith('dkc://'):
            self.fail(f'remote path must start with dkc://')

        value = value.replace('dkc://', '')
        r = ctx.obj.session.get(f'folders/{value}')
        if r.ok:
            return RemoteFolder(**r.json())
        elif r.status_code == 404:
            self.fail(f'folder with id {value} doesn\'t exist.')
        else:
            r.raise_for_status()


class RemoteOrLocalPath(click.ParamType):
    name = "remote-or-local-path"

    def convert(self, value, param, ctx):
        from rvt import RemoteFolder

        if value.startswith('dkc://'):
            value = value.replace('dkc://', '')
            r = ctx.obj.session.get(f'folders/{value}')
            if r.ok:
                return RemoteFolder(**r.json())
            elif r.status_code == 404:
                self.fail(f'folder with id {value} doesn\'t exist.')
            else:
                r.raise_for_status()
        else:
            return Path(value)
