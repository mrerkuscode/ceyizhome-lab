import socket
import pytest


def _server_running(host: str = "127.0.0.1", port: int = 8000) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def pytest_collection_modifyitems(config, items):
    """localhost:8000 ayakta degilse needs_server testlerini SKIP et."""
    if _server_running():
        return
    skip = pytest.mark.skip(reason="localhost:8000 calismiyor — sunucu gerektiren testler atlandi")
    for item in items:
        if "test_browser_smoke" in str(item.fspath):
            item.add_marker(skip)
