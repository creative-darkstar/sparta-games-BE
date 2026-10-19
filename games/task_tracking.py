"""TTL indexes only; task outcomes remain in the Celery result backend."""
import hashlib
import json
import logging
import time
from uuid import uuid4

import redis
from django.conf import settings
from django.db import transaction

logger = logging.getLogger("sparta_games")
TTL = 7 * 24 * 60 * 60


def connection():
    return redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_connect_timeout=2, socket_timeout=2)


def task_key(task_id):
    return f"submission:task:{task_id}"


def file_key(game_id, name):
    return f"submission:file:{game_id}:{hashlib.sha256(name.encode()).hexdigest()}"


def lookup(task_id):
    raw = connection().get(task_key(task_id))
    return json.loads(raw) if raw else None


def current_submission(game):
    try:
        raw = connection().get(file_key(game.pk, game.gamefile.name))
        if not raw:
            return {"lookup_status": "unavailable"}
        record = json.loads(raw)
        return {key: record[key] for key in ("task_id", "submission_id", "publish_status", "created_at")}
    except (redis.RedisError, ValueError):
        return {"lookup_status": "unavailable"}


def prepare(game, kind="game_zip_validation"):
    return dict(task_id=str(uuid4()), submission_id=str(uuid4()), kind=kind,
                owner_id=game.maker_id, game_id=game.pk, file_key=game.gamefile.name,
                created_at=time.time(), publish_status="prepared")


def publish(record, task):
    """Never raise after DB commit: acceptance and dispatch are separate facts."""
    try:
        client = connection()
        payload = json.dumps(record)
        with client.pipeline(transaction=True) as pipe:
            pipe.set(task_key(record["task_id"]), payload, ex=TTL)
            if record["kind"] == "game_zip_validation":
                pipe.set(file_key(record["game_id"], record["file_key"]), payload, ex=TTL)
            pipe.execute()
        args = [record["game_id"]]
        if record["kind"] == "game_zip_validation":
            args += [record["file_key"], record["submission_id"]]
        task.apply_async(args=args, task_id=record["task_id"])
        record["publish_status"] = "published"
    except Exception:
        record["publish_status"] = "failed"
        logger.exception("Task dispatch unavailable: %s", record["task_id"])
    try:
        # Each submission has an immutable file index: old callbacks cannot replace a new file.
        client = connection()
        with client.pipeline(transaction=True) as pipe:
            pipe.set(task_key(record["task_id"]), json.dumps(record), ex=TTL)
            if record["kind"] == "game_zip_validation":
                pipe.set(file_key(record["game_id"], record["file_key"]), json.dumps(record), ex=TTL)
            pipe.execute()
    except Exception:
        logger.exception("Task dispatch index unavailable: %s", record["task_id"])


def schedule(game, task):
    record = prepare(game)
    transaction.on_commit(lambda: publish(record, task), robust=True)
    return record


def receipt(record):
    return {key: record[key] for key in ("game_id", "task_id", "submission_id", "publish_status")}


def claim_file(name):
    """Reserve a single immutable upload for one submission, including concurrent POSTs."""
    from .models import Game
    if Game.objects.filter(gamefile=name).exists():
        return False
    return bool(connection().set("submission:claimed:" + hashlib.sha256(name.encode()).hexdigest(), "1", nx=True, ex=TTL))


def upload_key(name):
    return "submission:upload:" + hashlib.sha256(name.encode()).hexdigest()


def remember_upload(name, owner_id):
    # An expired presign cannot be recycled as a later submission, even if S3 deletion failed.
    connection().set(upload_key(name), str(owner_id), ex=1800)


def owns_upload(name, owner_id):
    value = connection().get(upload_key(name))
    return value is not None and value.decode() == str(owner_id)
