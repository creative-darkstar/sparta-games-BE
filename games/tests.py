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
