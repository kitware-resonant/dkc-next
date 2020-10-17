from hashlib import md5

import pytest

from dkc.core.models import TermsAgreement


@pytest.mark.django_db
def test_terms_checksum_computed(terms_factory):
    terms = terms_factory(text='hello')
    assert terms.checksum == md5(b'hello').hexdigest()


@pytest.mark.django_db
def test_rest_get_terms(api_client, terms):
    resp = api_client.get(f'/api/v2/folders/{terms.tree.root_folder.id}/terms')
    assert resp.status_code == 200
    assert resp.data['text'] == terms.text
    assert resp.data['checksum'] == terms.checksum


@pytest.mark.django_db
def test_terms_agreement_unauthenticated(api_client, terms):
    resp = api_client.get(f'/api/v2/folders/{terms.tree.root_folder.id}/terms/agreement')
    assert resp.status_code == 200
    assert resp.data['text'] == terms.text
    assert resp.data['checksum'] == terms.checksum


@pytest.mark.django_db
def test_terms_post_agreement(api_client, terms, user):
    api_client.force_authenticate(user=user)
    resp = api_client.post(
        f'/api/v2/folders/{terms.tree.root_folder.id}/terms/agreement/{terms.checksum}'
    )
    assert resp.status_code == 204

    agreement = TermsAgreement.objects.get(terms=terms, user=user)
    assert agreement.checksum == terms.checksum


@pytest.mark.django_db
def test_terms_skip_existing_agreement(api_client, terms_agreement):
    api_client.force_authenticate(user=terms_agreement.user)
    resp = api_client.get(
        f'/api/v2/folders/{terms_agreement.terms.tree.root_folder.id}/terms/agreement'
    )
    assert resp.status_code == 204


@pytest.mark.django_db
def test_terms_agree_invalid_checksum(api_client, terms, user):
    api_client.force_authenticate(user=user)
    resp = api_client.post(f'/api/v2/folders/{terms.tree.root_folder.id}/terms/agreement/invalid')
    assert resp.status_code == 400
    assert resp.json()['checksum'] == 'Mismatched checksum. Your terms may be out of date.'


@pytest.mark.django_db
def test_terms_agree_invalid_folder(api_client, folder, user):
    api_client.force_authenticate(user=user)
    resp = api_client.post(f'/api/v2/folders/{folder.id}/terms/agreement/a_checksum')
    assert resp.status_code == 400
    assert resp.json()['folder'] == 'This folder has no associated terms of use.'


@pytest.mark.django_db
def test_terms_update_requires_reagreement(api_client, terms_agreement):
    terms_agreement.terms.text += 'extra content'
    terms_agreement.terms.save()

    api_client.force_authenticate(user=terms_agreement.user)
    resp = api_client.get(
        f'/api/v2/folders/{terms_agreement.terms.tree.root_folder.id}/terms/agreement'
    )
    assert resp.status_code == 200
    assert resp.data['text'] == terms_agreement.terms.text
