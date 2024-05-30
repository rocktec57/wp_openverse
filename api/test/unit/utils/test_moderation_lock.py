from datetime import datetime, timedelta

from django.contrib.auth.models import Group

import pytest
from freezegun import freeze_time

from api.utils.moderation_lock import TTL, LockManager


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def moderators(django_user_model):
    for username in ["one", "two"]:
        user = django_user_model.objects.create(username=username, password=username)
        group, _ = Group.objects.get_or_create(name="Content Moderators")
        group.user_set.add(user)


@pytest.mark.parametrize(
    "is_cache_reachable, cache_name",
    [(True, "redis"), (False, "unreachable_redis")],
)
def test_lock_manager_handles_missing_redis(is_cache_reachable, cache_name, request):
    request.getfixturevalue(cache_name)

    lm = LockManager("media_type")
    expiration = lm.add_locks("one", 10)

    if is_cache_reachable:
        assert expiration is not None
        assert lm.prune() == {"one": {"media_type:10"}}
        assert lm.moderator_set(10) == {"one"}
        assert lm.score("one", 10) == expiration
    else:
        assert expiration is None
        assert lm.prune() is None
        assert lm.moderator_set(10) == set()
        assert lm.score("one", 10) == expiration


def test_lock_manager_adds_and_removes_locks():
    lm = LockManager("media_type")

    lm.add_locks("one", 10)
    assert lm.moderator_set(10) == {"one"}
    lm.add_locks("two", 10)
    assert lm.moderator_set(10) == {"one", "two"}
    lm.remove_locks("two", 10)
    assert lm.moderator_set(10) == {"one"}


def test_relocking_updates_score(redis):
    lm = LockManager("media_type")
    now = datetime.now()

    with freeze_time(now):
        lm.add_locks("one", 10)
        init_score = lm.score("one", 10)

    with freeze_time(now + timedelta(seconds=TTL / 2)):
        lm.add_locks("one", 10)
        updated_score = lm.score("one", 10)

    assert updated_score == init_score + TTL / 2


def test_lock_manager_prunes_after_timeout():
    lm = LockManager("media_type")
    now = datetime.now()

    with freeze_time(now):
        lm.add_locks("one", 10)

    with freeze_time(now + timedelta(seconds=TTL - 1)):
        assert lm.moderator_set(10) == {"one"}

    with freeze_time(now + timedelta(seconds=TTL + 1)):
        assert lm.moderator_set(10) == set()
