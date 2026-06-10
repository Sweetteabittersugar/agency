"""测试统一错误类型"""
import pytest
from maestro.api_errors import (
    AppError, bad_request, not_found, permission_denied,
    invalid_input, internal_error, handle_app_error
)


class TestAppErrors:
    def test_bad_request(self):
        err = bad_request("测试错误")
        assert err.code == "BAD_REQUEST"
        assert err.http_status == 400

    def test_not_found(self):
        err = not_found("Agent", "test")
        assert err.code == "NOT_FOUND"
        assert err.http_status == 404
        assert "Agent" in err.message

    def test_permission_denied(self):
        err = permission_denied()
        assert err.code == "PERMISSION_DENIED"
        assert err.http_status == 403

    def test_invalid_input(self):
        err = invalid_input("name")
        assert err.code == "INVALID_INPUT"

    def test_internal_error(self):
        err = internal_error()
        assert err.code == "INTERNAL_ERROR"
        assert err.http_status == 500

    def test_handle_app_error(self, mock_handler):
        err = bad_request("测试")
        handle_app_error(mock_handler, err)
        assert mock_handler.status == 400
        assert mock_handler.response["ok"] == False
        assert mock_handler.response["error"]["code"] == "BAD_REQUEST"
