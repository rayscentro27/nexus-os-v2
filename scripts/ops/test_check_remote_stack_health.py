from check_remote_stack_health import _url_status


def test_unavailable_local_endpoint_is_safe_and_secret_free():
    assert _url_status("http://127.0.0.1:1/health") == "UNAVAILABLE"
