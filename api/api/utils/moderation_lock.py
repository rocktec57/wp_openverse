import functools
import time

import django_redis
import structlog
from redis.exceptions import ConnectionError

from api.models.moderation import get_moderators


LOCK_PREFIX = "moderation_lock"
TTL = 10  # seconds

logger = structlog.get_logger(__name__)


def handle_redis_exception(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ConnectionError:
            return None

    return wrapper


class LockManager:
    """
    Kudos to this Google Group discussion for the solution using a
    ranked-set:
    https://web.archive.org/web/20211205091916/https://groups.google.com/g/redis-db/c/rXXMCLNkNSs
    """

    def __init__(self, media_type):
        self.media_type = media_type

    @handle_redis_exception
    def prune(self) -> dict[str, set[str]]:
        """
        Delete all expired locks and get a mapping of usernames to
        media items that have active locks.

        :return: a mapping of moderators to media items they are viewing
        """

        redis = django_redis.get_redis_connection("default")
        valid_locks = {}

        now = int(time.time())
        pipe = redis.pipeline()
        for username in get_moderators().values_list("username", flat=True):
            key = f"{LOCK_PREFIX}:{username}"
            for value, score in redis.zrange(key, 0, -1, withscores=True):
                if score <= now:
                    logger.info("Deleting expired lock", key=key, value=value)
                    pipe.zrem(key, value)
                else:
                    logger.info("Keeping valid lock", key=key, value=value)
                    valid_locks.setdefault(username, set()).add(value.decode())
        pipe.execute()

        return valid_locks

    @handle_redis_exception
    def add_locks(self, username, object_id) -> int:
        """
        Add a soft-lock for a given media item to the given moderator.

        :param username: the username of the moderator viewing a media item
        :param object_id: the ID of the media item being viewed
        """

        redis = django_redis.get_redis_connection("default")

        object = f"{self.media_type}:{object_id}"

        expiration = int(time.time()) + TTL
        logger.info("Adding lock", object=object, user=username, expiration=expiration)
        redis.zadd(f"{LOCK_PREFIX}:{username}", {object: expiration})
        return expiration

    @handle_redis_exception
    def remove_locks(self, username, object_id):
        """
        Remove the soft-lock for a given media item from the given moderator.

        :param username: the username of the moderator not viewing a media item
        :param object_id: the ID of the media item not being viewed
        """

        redis = django_redis.get_redis_connection("default")

        object = f"{self.media_type}:{object_id}"

        logger.info("Removing lock", object=object, user=username)
        redis.zrem(f"{LOCK_PREFIX}:{username}", object)

    def moderator_set(self, object_id) -> set[str]:
        """
        Get the list of moderators on a particular item.

        :param object_id: the ID of the media item being viewed
        :return: the list of moderators on a particular item
        """

        valid_locks = self.prune() or {}

        object = f"{self.media_type}:{object_id}"
        mods = {mod for mod, objects in valid_locks.items() if object in objects}
        logger.info("Retrieved moderators", object=object, mods=mods)
        return mods

    @handle_redis_exception
    def score(self, username, object_id) -> int:
        """
        Get the score of a particular moderator on a particular item.

        :param username: the username of the moderator viewing a media item
        :param object_id: the ID of the media item being viewed
        :return: the score of a particular moderator on a particular item
        """

        redis = django_redis.get_redis_connection("default")

        object = f"{self.media_type}:{object_id}"
        score = redis.zscore(f"{LOCK_PREFIX}:{username}", object)
        logger.info("Retrieved score", object=object, user=username, score=score)
        return score
