import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main


class CookieTests(unittest.TestCase):
    def test_both_current_and_legacy_prefixes(self):
        for prefix in ("gld", "koa", "future-name"):
            with self.subTest(prefix=prefix):
                valid, detected = main.validate_cookie(
                    f"other=x; {prefix}:sess=value=1; {prefix}:sess.sig=signature"
                )
                self.assertTrue(valid)
                self.assertEqual(detected, prefix)

    def test_missing_signature_or_mismatched_prefix(self):
        for cookie in ("gld:sess=abc", "gld:sess=abc; koa:sess.sig=def",
                       "gld:sess=; gld:sess.sig=def", "x=1"):
            with self.subTest(cookie=cookie):
                self.assertFalse(main.validate_cookie(cookie)[0])

    def test_copied_request_header_normalizes_without_rewriting_keys(self):
        self.assertEqual(
            main.normalize_cookie('Cookie: "gld:sess=abc; gld:sess.sig=def"'),
            "gld:sess=abc; gld:sess.sig=def",
        )
        self.assertEqual(
            main.normalize_cookie('"Cookie: koa:sess=abc; koa:sess.sig=def"'),
            "koa:sess=abc; koa:sess.sig=def",
        )


class CheckinTests(unittest.TestCase):
    def setUp(self):
        self.mail = patch.object(main, "send_mail").start()
        self.addCleanup(patch.stopall)

    def run_checkin(self, cookie, post_response, get_response=None):
        env = {"GLADOS_COOKIE": cookie, "GLADOS_TOKEN": "glados.cloud"}
        with patch.dict(os.environ, env, clear=True), \
                patch.object(main.requests, "post", return_value=post_response) as post, \
                patch.object(main.requests, "get", return_value=get_response) as get:
            result = main.checkin()
        return result, post, get

    def test_gld_and_koa_sent_unchanged(self):
        for prefix in ("gld", "koa"):
            with self.subTest(prefix=prefix):
                cookie = f"{prefix}:sess=session; {prefix}:sess.sig=signed"
                response = Mock(status_code=200)
                response.json.return_value = {"code": 0, "message": "success"}
                status = Mock(status_code=200)
                status.json.return_value = {"data": {"leftDays": 100.5}}
                result, post, get = self.run_checkin(cookie, response, status)
                self.assertEqual(result, 0)
                self.assertEqual(post.call_args.kwargs["headers"]["Cookie"], cookie)
                self.assertEqual(get.call_count, 1)

    def test_auth_failure_sets_nonzero_exit_and_skips_status_request(self):
        response = Mock(status_code=200)
        response.json.return_value = {"code": -2, "message": "没有权限"}
        result, _, get = self.run_checkin("gld:sess=abc; gld:sess.sig=def", response)
        self.assertEqual(result, 1)
        get.assert_not_called()
        self.assertIn("重新复制完整 Cookie", self.mail.call_args.args[1])

    def test_http_forbidden_is_actionable(self):
        result, _, get = self.run_checkin(
            "koa:sess=abc; koa:sess.sig=def", Mock(status_code=403)
        )
        self.assertEqual(result, 1)
        get.assert_not_called()
        self.assertIn("GitHub Secret", self.mail.call_args.args[1])

    def test_invalid_cookie_stops_before_request(self):
        result, post, _ = self.run_checkin("gld:sess=abc", Mock())
        self.assertEqual(result, 1)
        post.assert_not_called()

    def test_repeat_is_success(self):
        response = Mock(status_code=200)
        response.json.return_value = {"code": 1, "message": "already checked in"}
        result, _, _ = self.run_checkin("koa:sess=abc; koa:sess.sig=def", response, Mock(status_code=503))
        self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
