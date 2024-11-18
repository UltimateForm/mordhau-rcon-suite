from common import parsers, models


def test_parses_login_event():
    event_raw = "Login: 2024.10.12-21.23.58: John Wayne (SA213123AKA872) logged in"
    event_expected = models.LoginEvent(
        "Login", "2024.10.12-21.23.58", "John Wayne", "SA213123AKA872", "in"
    )
    event_parsed = parsers.parse_login_event(event_raw)
    assert event_expected == event_parsed


def test_parses_chat_event():
    event_raw = "Chat: SA213123AKA872, John Wayne, (ALL) hello"
    event_expected = models.ChatEvent(
        "Chat", "SA213123AKA872", "John Wayne", "ALL", "hello"
    )
    event_parsed = parsers.parse_chat_event(event_raw)
    assert event_expected == event_parsed


def test_parses_killfeed_event():
    event_raw = "Killfeed: 2024.10.12-21.33.28: SA213123AKA872 (John Wayne (smartass)) killed ASDDU1231215GR (Blattant Ottobloking)"
    event_expected = models.KillfeedEvent(
        "Killfeed",
        "2024.10.12-21.33.28",
        "SA213123AKA872",
        "John Wayne (smartass)",
        "ASDDU1231215GR",
        "Blattant Ottobloking",
    )
    event_parsed = parsers.parse_killfeed_event(event_raw)
    assert event_expected == event_parsed
