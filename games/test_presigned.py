from io import BytesIO
from unittest.mock import Mock, patch
from uuid import uuid4
import time

from django.contrib.auth import get_user_model
from django.test import TestCase, SimpleTestCase
from rest_framework.test import APIRequestFactory, force_authenticate
from games.models import Game
from games.tasks import validate_game_zip_task
from games.task_tracking import prepare, publish, current_submission
from qnas.views import get_task_status


class ZipContractTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(email="zip@test.invalid", nickname="zip")
        self.other = get_user_model().objects.create_user(email="other@test.invalid", nickname="other")
        self.game = Game.objects.create(maker=self.owner, title="test", content="test", gamefile="zips/one.zip", star=0, review_cnt=0)
        self.submission = str(uuid4())
        self.s3 = Mock()
        self.s3.get_object.return_value = {"Body": Mock(iter_chunks=lambda **kw: iter([b"zip"]))}

    def run_task(self):
        return validate_game_zip_task.run(self.game.pk, "zips/one.zip", self.submission)

    @patch("games.tasks.safe_s3_tag")
    @patch("games.tasks.validate_zip_file", return_value=(True, None))
    @patch("games.tasks.get_s3_client")
    def test_valid_keeps_admin_pending(self, client, validate, tag):
        client.return_value = self.s3
        self.assertEqual(self.run_task()["outcome"], "valid")
        self.game.refresh_from_db()
        self.assertEqual(self.game.register_state, 0)
        tag.assert_called_once()

    @patch("games.tasks.validate_zip_file", return_value=(False, "심볼릭 링크를 확인했습니다."))
    @patch("games.tasks.get_s3_client")
    def test_invalid_and_duplicate_log(self, client, validate):
        client.return_value = self.s3
        result = self.run_task()
        self.run_task()
        self.game.refresh_from_db()
        self.assertEqual(result["outcome"], "invalid")
        self.assertEqual(result["reason_code"], "SYMLINK_NOT_ALLOWED")
        self.assertEqual(self.game.register_state, 2)
        self.assertEqual(self.game.logs_game.count(), 1)

    @patch("games.tasks.get_s3_client")
    def test_old_file_and_legacy_skip(self, client):
        self.game.gamefile = "zips/two.zip"
        self.game.save()
        self.assertEqual(self.run_task()["outcome"], "skipped")
        self.assertEqual(validate_game_zip_task.run(self.game.pk)["outcome"], "skipped")
        client.assert_not_called()

    @patch("games.tasks.validate_zip_file")
    @patch("games.tasks.get_s3_client")
    def test_replacement_during_validation_cannot_reject(self, client, validate):
        client.return_value = self.s3
        def replace(_):
            Game.objects.filter(pk=self.game.pk).update(gamefile="zips/two.zip")
            return False, "bad zip"
        validate.side_effect = replace
        self.assertEqual(self.run_task()["outcome"], "skipped")
        self.game.refresh_from_db()
        self.assertEqual(self.game.register_state, 0)
        self.assertEqual(self.game.logs_game.count(), 0)

    @patch("games.tasks.safe_s3_tag", side_effect=RuntimeError("tag unavailable"))
    @patch("games.tasks.validate_zip_file", return_value=(True, None))
    @patch("games.tasks.get_s3_client")
    def test_retry_exhaustion_is_failure(self, client, validate, tag):
        client.return_value = self.s3
        result = validate_game_zip_task.apply(args=[self.game.pk, "zips/one.zip", self.submission], throw=False)
        self.assertEqual(result.status, "FAILURE")
        self.game.refresh_from_db()
        self.assertEqual(self.game.register_state, 0)

    def status_request(self, user, record, result=None):
        request = APIRequestFactory().get("/task")
        if user:
            force_authenticate(request, user=user)
        with patch("games.task_tracking.lookup", return_value=record), patch("qnas.views.AsyncResult", return_value=result or Mock(status="SUCCESS", result=None)):
            return get_task_status(request, "task")

    def test_status_permissions_and_missing(self):
        record = prepare(self.game)
        record["publish_status"] = "published"
        self.assertEqual(self.status_request(None, record).status_code, 401)
        self.assertEqual(self.status_request(self.other, record).status_code, 403)
        self.assertEqual(self.status_request(self.owner, record).status_code, 200)
        self.assertEqual(self.status_request(self.owner, None).status_code, 404)
        record["kind"] = "game_publication"
        self.assertEqual(self.status_request(self.owner, record).status_code, 403)
        self.other.is_staff = True
        self.assertEqual(self.status_request(self.other, record).status_code, 200)

    def test_status_failure_hides_exception_and_pending_is_bounded(self):
        record = prepare(self.game)
        record.update(publish_status="published", created_at=time.time()-700)
        response = self.status_request(self.owner, record, Mock(status="FAILURE", result=RuntimeError("secret")))
        self.assertIsNone(response.data["result"])
        response = self.status_request(self.owner, record, Mock(status="PENDING"))
        self.assertEqual(response.data["lookup_status"], "unconfirmed")

    @patch("games.task_tracking.connection")
    def test_dispatch_failure_is_recorded_without_raising(self, client):
        record = prepare(self.game)
        task = Mock()
        task.apply_async.side_effect = RuntimeError("broker unavailable")
        publish(record, task)
        self.assertEqual(record["publish_status"], "failed")
        self.assertTrue(client.return_value.pipeline.called)

    @patch("games.task_tracking.connection")
    def test_missing_mapping_does_not_hide_game(self, client):
        client.return_value.get.return_value = None
        self.assertEqual(current_submission(self.game), {"lookup_status": "unavailable"})
        self.assertTrue(Game.objects.filter(pk=self.game.pk).exists())

    @patch("games.task_tracking.publish")
    def test_metadata_edit_does_not_schedule_validation(self, publish_task):
        from games.views import GameDetailAPIView
        request = APIRequestFactory().put("/game", {"title": "changed"}, format="multipart")
        force_authenticate(request, user=self.owner)
        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            response = GameDetailAPIView.as_view()(request, game_id=self.game.pk)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("task_id", response.data["data"])
        publish_task.assert_not_called()
        # Metadata edits must not generate new review notifications either.
        self.assertEqual(len(callbacks), 0)

    @patch("games.views.claim_file", return_value=True)
    @patch("games.views.assert_gamefile_key", return_value=("zips/two.zip", None))
    def test_replacement_receipt_and_mapping_are_for_new_file(self, assert_key, claim):
        from games.views import GameDetailAPIView
        request = APIRequestFactory().put("/game", {"gamefile": "zips/two.zip"}, format="multipart")
        force_authenticate(request, user=self.owner)
        with self.captureOnCommitCallbacks(execute=False):
            response = GameDetailAPIView.as_view()(request, game_id=self.game.pk)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["data"]["task_id"])
        self.assertTrue(response.data["data"]["submission_id"])
        self.game.refresh_from_db()
        self.assertEqual(self.game.gamefile.name, "zips/two.zip")

    def test_empty_owner_list_is_200_and_public_hides_pending(self):
        from users.views import my_games
        for user, target in [(self.other, self.other), (self.other, self.owner)]:
            request = APIRequestFactory().get("/games")
            force_authenticate(request, user=user)
            response = my_games(request, user_id=target.pk)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["data"], [])

    def test_response_wrapper_preserves_task_state(self):
        from spartagames.custom_middleware import DRFStandardResponseMiddleware
        record = prepare(self.game)
        record["publish_status"] = "published"
        response = self.status_request(self.owner, record, Mock(status="SUCCESS", result={"status": "success", "game_id": self.game.pk}))
        wrapped = DRFStandardResponseMiddleware(lambda _: None).process_response(None, response)
        self.assertEqual(wrapped.data["status"], "success")
        self.assertEqual(wrapped.data["data"]["status"], "SUCCESS")
        self.assertEqual(wrapped.data["data"]["result"]["game_id"], self.game.pk)


class PresignTests(SimpleTestCase):
    def test_if_none_match_is_signed_with_installed_botocore(self):
        import boto3
        from botocore.config import Config
        from commons.views import generate_presigned_url_for_upload
        from urllib.parse import urlparse, parse_qs
        s3 = boto3.client("s3", region_name="ap-northeast-2", aws_access_key_id="test", aws_secret_access_key="test", config=Config(signature_version="s3v4"))
        with patch("commons.views.get_s3_client", return_value=s3):
            url, _, _, _ = generate_presigned_url_for_upload("zips", "zip", "test.zip")
        self.assertIn("if-none-match", parse_qs(urlparse(url).query)["X-Amz-SignedHeaders"][0])
