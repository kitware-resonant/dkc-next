import djclick as click
import requests

from dkc.core.models import File

DKC_API = 'https://data.kitware.com/api/v1'


def copy_file(pending_file: File, token: str) -> None:
    with requests.get(
        f'{DKC_API}/file/{pending_file.legacy_file_id}/download',
        stream=True,
        headers={'Girder-Token': token},
    ) as resp:
        resp.raise_for_status()
        pending_file.blob = File(resp.raw, name=pending_file.name)
        pending_file.save(update_fields=['blob'])


@click.command()
@click.argument('dkc_api_key')
def command(dkc_api_key) -> None:
    resp = requests.post(f'{DKC_API}/api_key/token', data={'key': dkc_api_key})
    resp.raise_for_status()
    token = resp['authToken']['token']

    while True:
        pending_files = list(File.objects.filter(blob='').exclude(legacy_file_id='')[:1000])
        if not pending_files:
            break

        for pending_file in pending_files:
            print(pending_file.id, pending_file.name, pending_file.size)
            copy_file(pending_file, token)
