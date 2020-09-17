import pytest


def test_file_checksum(file_factory):
    # Use "build" strategy, so database is not required
    file = file_factory.build()
    file.compute_sha512()
    assert len(file.sha512) == 128


@pytest.mark.django_db
def test_file_rest_retrieve(api_client, file):
    resp = api_client.get(f'/api/v2/files/{file.id}')
    assert resp.status_code == 200
    # Inspect .data to avoid parsing the response content
    assert resp.data['name'] == file.name
