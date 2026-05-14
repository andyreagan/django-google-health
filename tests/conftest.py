import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def customer(db):
    User = get_user_model()
    return User.objects.create_user(username="test-customer")
