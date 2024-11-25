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


def test_parses_server_info():
    event_raw = "HostName: TEST_DEKSTOP\nServerName: Server\nVersion: Release 26, Revision 25635, Enforced 1, Release Ver: 7\nGameMode: Skirmish\nMap: Grad\n\x00\x00"
    expected_data = models.ServerInfo(
        "TEST_DEKSTOP",
        "Server",
        "Release 26, Revision 25635, Enforced 1, Release Ver: 7",
        "Skirmish",
        "Grad",
    )
    parsed_data = parsers.parse_server_info(event_raw)
    assert parsed_data == expected_data


def test_parses_playerlist_row():
    raw_row = "SA213123AKA872, John Wayne (smartass), 32 ms, team 0"
    expected_data = models.Player("SA213123AKA872", "John Wayne (smartass)")
    parsed_data = parsers.parse_playerlist_row(raw_row)
    assert parsed_data == expected_data


def test_parses_playerlist():
    raw_row = "SA213123AKA872, John Wayne (smartass), 32 ms, team 0\nASDDU1231215GR, Blattant Ottobloking, 32 ms, team 0\n3 bots"
    expected_data = [
        models.Player("SA213123AKA872", "John Wayne (smartass)"),
        models.Player("ASDDU1231215GR", "Blattant Ottobloking"),
    ]
    parsed_data = parsers.parse_playerlist(raw_row)
    assert parsed_data == expected_data


def test_transforms_kill_records_to_db_mutation():
    kill_record = models.KillRecord(
        "SA213123AKA872",
        "John Wayne (smartass)",
        {"ASDDU1231215GR": 2, "ASEEU81712181G": 5},
    )
    expected_mutation = {
        "$set": {"playfab_id": "SA213123AKA872", "user_name": "John Wayne (smartass)"},
        "$inc": {"kill_count": 7, "kills.ASDDU1231215GR": 2, "kills.ASEEU81712181G": 5},
    }
    expected_death_updates = [
        {"$set": {"playfab_id": "ASDDU1231215GR"}, "$inc": {"death_count": 2}},
        {"$set": {"playfab_id": "ASEEU81712181G"}, "$inc": {"death_count": 5}},
    ]
    (death_updates, mutation) = parsers.transform_kill_record_to_db(kill_record)
    assert mutation == expected_mutation
    assert death_updates == expected_death_updates
