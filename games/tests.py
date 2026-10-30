from unittest import mock

from botocore.exceptions import ClientError
from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Game
from .tasks import validate_game_zip_task


FILE_KEY = "zips/20261030120000000000_game.zip"


def make_user(email="maker@example.com", nickname="maker", **extra):
    return get_user_model().objects.create_user(email=email, password="pw-test-1234", nickname=nickname, **extra)


def make_game(maker, gamefile=FILE_KEY, register_state=0):
    return Game.objects.create(
        title="테스트 게임", thumbnail="images/thumbnail/t.png", maker=maker,
        content="설명", gamefile=gamefile, register_state=register_state, star=0, review_cnt=0,
    )


class FakeBody:
    def iter_chunks(self, chunk_size=8192):
        yield b"PK"


def fake_s3(get_object_error=None):
    s3 = mock.Mock()
    if get_object_error:
        s3.get_object.side_effect = get_object_error
    else:
        s3.get_object.return_value = {"Body": FakeBody()}
    return s3


@mock.patch("games.tasks.create_notification")
class ValidateGameZipTaskTests(TestCase):
    """F03: Celery 실행 상태와 파일 판정(valid/invalid/skipped) 분리"""

    def setUp(self):
        self.maker = make_user()
        self.game = make_game(self.maker)

    def run_task(self, *args):
        return validate_game_zip_task.apply(args=args)

    @mock.patch("games.tasks.safe_s3_tag")
    @mock.patch("games.tasks.validate_zip_file", return_value=(True, None))
    @mock.patch("games.tasks.get_s3_client")
    def test_valid(self, get_s3, _validate, tag, _notify):
        get_s3.return_value = fake_s3()
        result = self.run_task(self.game.id, FILE_KEY)
        self.assertEqual(result.state, "SUCCESS")
        self.assertEqual(result.result["outcome"], "valid")
        self.assertEqual(result.result["kind"], "game_zip_validation")
        self.assertEqual(result.result["file_key"], FILE_KEY)
        tag.assert_called_once()
        self.game.refresh_from_db()
        self.assertEqual(self.game.register_state, 0)

    @mock.patch("games.tasks.validate_zip_file", return_value=(False, "심볼릭 링크를 확인했습니다."))
    @mock.patch("games.tasks.get_s3_client")
    def test_invalid_rejects_once(self, get_s3, _validate, notify):
        get_s3.return_value = fake_s3()
        first = self.run_task(self.game.id, FILE_KEY)
        self.assertEqual(first.state, "SUCCESS")
        self.assertEqual(first.result["outcome"], "invalid")
        self.assertEqual(first.result["reason"], "심볼릭 링크를 확인했습니다.")
        self.game.refresh_from_db()
        self.assertEqual(self.game.register_state, 2)
        self.assertEqual(self.game.logs_game.count(), 1)

        # 같은 작업 재실행: 이미 반려됨 → skipped, 로그·알림 중복 없음
        second = self.run_task(self.game.id, FILE_KEY)
        self.assertEqual(second.result["outcome"], "skipped")
        self.assertEqual(self.game.logs_game.count(), 1)
        self.assertEqual(notify.call_count, 1)

    @mock.patch("games.tasks.get_s3_client")
    def test_missing_object_is_invalid(self, get_s3, _notify):
        err = ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
        get_s3.return_value = fake_s3(get_object_error=err)
        result = self.run_task(self.game.id, FILE_KEY)
        self.assertEqual(result.result["outcome"], "invalid")
        self.assertEqual(result.result["reason_code"], "FILE_NOT_FOUND")

    def test_replaced_file_is_skipped(self, _notify):
        result = self.run_task(self.game.id, "zips/20261030110000000000_old.zip")
        self.assertEqual(result.result["outcome"], "skipped")
        self.assertEqual(result.result["reason_code"], "FILE_REPLACED")

    @mock.patch("games.tasks.validate_zip_file", return_value=(False, "잘못된 파일"))
    @mock.patch("games.tasks.get_s3_client")
    def test_replaced_during_check_is_skipped(self, get_s3, _validate, notify):
        s3 = fake_s3()
        get_s3.return_value = s3

        def replace_file(**_kwargs):
            Game.objects.filter(pk=self.game.id).update(gamefile="zips/20261030130000000000_new.zip")
            return {"Body": FakeBody()}

        s3.get_object.side_effect = replace_file
        result = self.run_task(self.game.id, FILE_KEY)
        self.assertEqual(result.result["outcome"], "skipped")
        self.game.refresh_from_db()
        self.assertEqual(self.game.register_state, 0)
        notify.assert_not_called()

    def test_legacy_args_skipped(self, _notify):
        result = self.run_task(self.game.id)
        self.assertEqual(result.result["outcome"], "skipped")
        self.assertEqual(result.result["reason_code"], "LEGACY_ARGS")

    @mock.patch("games.tasks.get_s3_client")
    def test_retries_exhausted_is_failure(self, get_s3, _notify):
        get_s3.return_value = fake_s3(get_object_error=RuntimeError("s3 down"))
        result = self.run_task(self.game.id, FILE_KEY)
        self.assertEqual(result.state, "FAILURE")
        self.game.refresh_from_db()
        self.assertEqual(self.game.register_state, 0)

    @mock.patch("games.tasks.safe_s3_tag", side_effect=RuntimeError("tag failed"))
    @mock.patch("games.tasks.validate_zip_file", return_value=(True, None))
    @mock.patch("games.tasks.get_s3_client")
    def test_tag_failure_is_not_valid(self, get_s3, _validate, _tag, _notify):
        get_s3.return_value = fake_s3()
        result = self.run_task(self.game.id, FILE_KEY)
        self.assertEqual(result.state, "FAILURE")


from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.test import override_settings
from rest_framework.test import APIClient

from .utils import is_zip_result_expired, zip_validation_task_id

# RequestContextMiddleware는 async __call__이라 동기 테스트 클라이언트에서 제외한다.
SYNC_MIDDLEWARE = [m for m in settings.MIDDLEWARE if not m.endswith("RequestContextMiddleware")]


def recent_key(name="game"):
    stamp = datetime.now(dt_timezone.utc).strftime("%Y%m%d%H%M%S%f")
    return f"zips/{stamp}_{name}.zip"


class ZipTaskIdTests(TestCase):
    """F01: 결정적 task_id와 보관기간 판정"""

    def test_deterministic_and_distinct(self):
        self.assertEqual(zip_validation_task_id(1, FILE_KEY), zip_validation_task_id(1, FILE_KEY))
        self.assertNotEqual(zip_validation_task_id(1, FILE_KEY), zip_validation_task_id(2, FILE_KEY))
        self.assertNotEqual(zip_validation_task_id(1, FILE_KEY), zip_validation_task_id(1, recent_key()))

    def test_expiry_from_key_timestamp(self):
        self.assertFalse(is_zip_result_expired(recent_key()))
        old = (datetime.now(dt_timezone.utc) - timedelta(days=8)).strftime("%Y%m%d%H%M%S%f")
        self.assertTrue(is_zip_result_expired(f"zips/{old}_game.zip"))
        self.assertFalse(is_zip_result_expired("zips/legacy.zip"))


@override_settings(MIDDLEWARE=SYNC_MIDDLEWARE)
class TaskStatusApiTests(TestCase):
    """F01: 기존 get_task_status의 game_id 기반 권한·현재 파일 확인"""

    def setUp(self):
        self.client = APIClient()
        self.maker = make_user()
        self.other = make_user("other@example.com", "other")
        self.admin = make_user("admin@example.com", "admin", is_staff=True)
        self.key = recent_key()
        self.game = make_game(self.maker, gamefile=self.key)
        self.task_id = zip_validation_task_id(self.game.id, self.key)

    def url(self, task_id=None, game_id=None):
        url = f"/directs/api/list/task-status/{task_id or self.task_id}/"
        return url if game_id is None else f"{url}?game_id={game_id}"

    def get(self, user, url):
        self.client.force_authenticate(user)
        return self.client.get(url)

    def test_anonymous_401(self):
        self.assertEqual(self.client.get(self.url(game_id=self.game.id)).status_code, 401)

    def test_other_user_403(self):
        self.assertEqual(self.get(self.other, self.url(game_id=self.game.id)).status_code, 403)

    def test_maker_and_admin_ok(self):
        for user in (self.maker, self.admin):
            res = self.get(user, self.url(game_id=self.game.id))
            self.assertEqual(res.status_code, 200)
            body = res.json()["data"]
            self.assertEqual(body["task_id"], self.task_id)
            self.assertEqual(body["status"], "PENDING")
            self.assertEqual(body["lookup_status"], "ok")

    def test_stale_task_id_409(self):
        old_id = zip_validation_task_id(self.game.id, "zips/20261030110000000000_old.zip")
        self.assertEqual(self.get(self.maker, self.url(old_id, self.game.id)).status_code, 409)

    def test_missing_game_404(self):
        self.assertEqual(self.get(self.maker, self.url(game_id=999999)).status_code, 404)

    def test_without_game_id_admin_only(self):
        self.assertEqual(self.get(self.maker, self.url()).status_code, 403)
        self.assertEqual(self.get(self.admin, self.url()).status_code, 200)

    def test_expired_pending(self):
        old = (datetime.now(dt_timezone.utc) - timedelta(days=8)).strftime("%Y%m%d%H%M%S%f")
        key = f"zips/{old}_game.zip"
        Game.objects.filter(pk=self.game.id).update(gamefile=key)
        res = self.get(self.maker, self.url(zip_validation_task_id(self.game.id, key), self.game.id))
        self.assertEqual(res.json()["data"]["lookup_status"], "expired")


@override_settings(MIDDLEWARE=SYNC_MIDDLEWARE)
class ZipTaskIdExposureTests(TestCase):
    """F01: 목록·상세의 zip_task_id는 제작자·관리자에게만"""

    def setUp(self):
        self.client = APIClient()
        self.maker = make_user()
        self.other = make_user("other@example.com", "other")
        self.game = make_game(self.maker, register_state=1)

    def detail(self, user):
        self.client.force_authenticate(user)
        return self.client.get(f"/games/api/list/{self.game.id}/").json()["data"]

    def my_games(self, user):
        self.client.force_authenticate(user)
        return self.client.get(f"/users/api/{self.maker.id}/games/").json()["data"]

    def test_detail(self):
        self.assertEqual(self.detail(self.maker)["zip_task_id"], zip_validation_task_id(self.game.id, FILE_KEY))
        self.assertIsNone(self.detail(self.other)["zip_task_id"])

    def test_my_games(self):
        self.assertEqual(self.my_games(self.maker)[0]["zip_task_id"], zip_validation_task_id(self.game.id, FILE_KEY))
        self.assertIsNone(self.my_games(self.other)[0]["zip_task_id"])
