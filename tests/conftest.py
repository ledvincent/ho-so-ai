import os
import socket
import pytest

# Apply before test collection imports api.config. Fixtures run too late.
os.environ["HOSO_LOAD_DOTENV"] = "0"
for name in ("OPENAI_API_KEY", "ASSISTANT_API_KEY"):
    os.environ.pop(name, None)


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("Tests must not access the network")
    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
