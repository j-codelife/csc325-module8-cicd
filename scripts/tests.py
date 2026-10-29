import io
import json
from contextlib import redirect_stdout
from unittest import TestCase
from unittest.mock import patch
from urllib.error import HTTPError

from scripts import deploy_render


class RenderDeploymentTests(TestCase):
    def setUp(self):
        self.enterContext(redirect_stdout(io.StringIO()))
        self.environment = {
            "RENDER_API_KEY": "test-token",
            "RENDER_SERVICE_ID": "srv-test",
            "RENDER_SERVICE_URL": "https://backend.example.com/",
            "GITHUB_SHA": "a" * 40,
        }
        self.api_url = "https://api.render.com/v1/services/srv-test/deploys"
        self.live_deployment = {
            "status": "live",
            "commit": {"id": self.environment["GITHUB_SHA"]},
        }

    @patch.dict("os.environ", {}, clear=True)
    @patch("scripts.deploy_render.request_json")
    def test_missing_configuration_stops_before_any_request(self, request):
        with self.assertRaisesRegex(RuntimeError, "Missing required configuration"):
            deploy_render.main()

        request.assert_not_called()

    @patch("scripts.deploy_render.request_json")
    def test_invalid_public_url_stops_before_deployment(self, request):
        for url in ("http://backend.example.com", "https://backend.example.com/api/health/"):
            with self.subTest(url=url):
                self.environment["RENDER_SERVICE_URL"] = url
                with patch.dict("os.environ", self.environment, clear=True):
                    with self.assertRaisesRegex(RuntimeError, "HTTPS origin"):
                        deploy_render.main()

        request.assert_not_called()

    @patch("scripts.deploy_render.time.sleep")
    @patch("scripts.deploy_render.request_json")
    def test_deploys_tested_commit_and_verifies_health_only_after_live(self, request, sleep):
        request.side_effect = [
            {"id": "dep-test"},
            {"status": "build_in_progress"},
            self.live_deployment,
            {"status": "ok"},
        ]

        with patch.dict("os.environ", self.environment, clear=True):
            deploy_render.main()

        self.assertEqual(request.call_args_list[0].args, (
            self.api_url, "test-token", {"commitId": "a" * 40}
        ))
        self.assertEqual(request.call_args_list[2].args, (
            f"{self.api_url}/dep-test", "test-token"
        ))
        self.assertEqual(request.call_args_list[3].args, (
            "https://backend.example.com/api/health/",
        ))

    @patch("scripts.deploy_render.request_json", return_value={})
    def test_missing_deployment_id_is_a_failure(self, request):
        with patch.dict("os.environ", self.environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "deployment ID"):
                deploy_render.main()

        self.assertEqual(request.call_count, 1)

    @patch("scripts.deploy_render.request_json")
    def test_failed_or_canceled_deployment_never_checks_health(self, request):
        for status in (
            "build_failed", "pre_deploy_failed", "update_failed", "canceled", "deactivated"
        ):
            with self.subTest(status=status):
                request.side_effect = [{"id": "dep-test"}, {"status": status}]
                request.reset_mock()
                with patch.dict("os.environ", self.environment, clear=True):
                    with self.assertRaisesRegex(RuntimeError, status):
                        deploy_render.main()
                self.assertEqual(request.call_count, 2)

    @patch("scripts.deploy_render.request_json")
    def test_live_deployment_must_match_the_tested_commit(self, request):
        request.return_value = {"status": "live", "commit": {"id": "b" * 40}}

        with self.assertRaisesRegex(RuntimeError, "does not match"):
            deploy_render.wait_for_deployment(self.api_url, "test-token", "a" * 40)

    @patch("scripts.deploy_render.time.monotonic", side_effect=[0, 901])
    @patch("scripts.deploy_render.request_json")
    def test_deployment_timeout_is_a_failure(self, request, monotonic):
        with self.assertRaisesRegex(RuntimeError, "Timed out"):
            deploy_render.wait_for_deployment(self.api_url, "test-token", "a" * 40)

        request.assert_not_called()

    @patch("scripts.deploy_render.time.sleep")
    @patch("scripts.deploy_render.request_json")
    def test_health_check_retries_startup_errors(self, request, sleep):
        request.side_effect = [RuntimeError("Starting"), {"status": "ok"}]

        deploy_render.verify_health("https://backend.example.com")

        self.assertEqual(request.call_count, 2)

    @patch("scripts.deploy_render.time.monotonic", side_effect=[0, 0, 121])
    @patch("scripts.deploy_render.time.sleep")
    @patch("scripts.deploy_render.request_json", return_value={"status": "unhealthy"})
    def test_unhealthy_public_response_fails_verification(self, request, sleep, monotonic):
        with self.assertRaisesRegex(RuntimeError, "expected JSON"):
            deploy_render.verify_health("https://backend.example.com")

    @patch("scripts.deploy_render.urlopen")
    def test_api_request_authenticates_and_sends_commit_as_json(self, urlopen):
        urlopen.return_value.__enter__.return_value = io.BytesIO(b'{"id": "dep-test"}')

        response = deploy_render.request_json(
            self.api_url, "test-token", {"commitId": "a" * 40}
        )

        self.assertEqual(response["id"], "dep-test")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer test-token")
        self.assertEqual(json.loads(request.data), {"commitId": "a" * 40})

    @patch("scripts.deploy_render.urlopen")
    def test_http_errors_do_not_expose_credentials_or_response_body(self, urlopen):
        urlopen.side_effect = HTTPError(self.api_url, 401, "test-token", {}, None)

        with self.assertRaisesRegex(RuntimeError, "status 401") as error:
            deploy_render.request_json(self.api_url, "test-token")

        self.assertNotIn("test-token", str(error.exception))
