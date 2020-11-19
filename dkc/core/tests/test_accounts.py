from allauth.account.forms import SignupForm
import pytest


@pytest.mark.django_db
@pytest.mark.parametrize(
    'value',
    [
        'email@gmail.com',
        '-startswithhyphen',
        'endswithhyphen-',
        'consecutive--hyphens',
    ],
)
def test_username_validation_fails(value):
    form = SignupForm(data={'username': value})
    assert form.errors['username'] == [
        'Username may only contain alphanumeric characters and hyphens. It cannot begin or '
        'end with a hyphen, and may not have consecutive hyphens.'
    ]


@pytest.mark.django_db
def test_username_too_long_fails():
    form = SignupForm(data={'username': 'x' * 60})
    assert form.errors['username'] == ['Username may not be more than 50 characters.']


@pytest.mark.django_db
@pytest.mark.parametrize(
    'value',
    [
        'contains-hyphen',
        '4lphanum3r1c',
        'contains-CAPITALS',
    ],
)
def test_username_validation_succeeds(value):
    form = SignupForm(data={'username': value})
    assert 'username' not in form.errors
