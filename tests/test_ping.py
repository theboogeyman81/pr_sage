from app.tasks.ping import ping


def test_ping_task():
    result = ping.apply()
    assert result.get() == "pong"
