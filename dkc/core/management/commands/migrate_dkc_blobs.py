import tempfile

from django.core.files import File as DjangoFile
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
        if 400 <= resp.status_code < 500:
            print('Skipped due to 4xx')
            return

        resp.raise_for_status()

        with tempfile.SpooledTemporaryFile(max_size=10 << 20) as tmp:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                tmp.write(chunk)
            tmp.seek(0)
            pending_file.blob = DjangoFile(tmp, name=pending_file.name)
            pending_file.save(update_fields=['blob'])


@click.command()
@click.argument('dkc_api_key')
def command(dkc_api_key) -> None:
    resp = requests.post(f'{DKC_API}/api_key/token', data={'key': dkc_api_key})
    resp.raise_for_status()
    token = resp.json()['authToken']['token']

    while True:
        pending_files = list(
            File.objects.filter(blob='').exclude(legacy_file_id='').order_by()[:1000]
        )
        if not pending_files:
            break

        for pending_file in pending_files:
            print(pending_file.id, pending_file.name, pending_file.size)
            copy_file(pending_file, token)
