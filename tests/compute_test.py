from common.compute import (
    compute_gate,
    compute_next_gate,
    compute_gate_text,
    compute_next_gate_text,
    compute_time_txt,
    slice_text_array_at_total_length,
)


def test_current_gate():
    gates = [20, 10, 500, 55, 1000, 250]
    current_gate = compute_gate(300, gates)
    assert current_gate == 250


def test_current_gate_is_exact():
    gates = [20, 10, 500, 55, 1000, 250]
    current_gate = compute_gate(500, gates)
    assert current_gate == 500


def test_current_gate_none():
    gates = [20, 10, 500, 55, 1000, 250]
    current_gate = compute_gate(5, gates)
    assert current_gate is None


def test_next_gate():
    gates = [20, 10, 500, 55, 1000, 250]
    next_gate = compute_next_gate(435, gates)
    assert next_gate == 500


def test_next_gate_without_current_gate():
    gates = [20, 10, 500, 55, 1000, 250]
    next_gate = compute_next_gate(5, gates)
    assert next_gate == 10


def test_no_next_gate():
    gates = [20, 10, 500, 55, 1000, 250]
    next_gate = compute_next_gate(2000, gates)
    assert next_gate is None


def test_gate_txt():
    gates = {
        "30": "Initiant",
        "60": "Squire",
        "120": "Veteran",
        "300": "Expert",
        "45": "Test",
    }
    (gate, txt) = compute_gate_text(70, gates)
    assert gate == 60
    assert txt == "Squire"


def test_compute_gate_text():
    gates = {
        "30": "Initiant",
        "60": "Squire",
        "120": "Veteran",
        "300": "Expert",
        "45": "Test",
    }
    (gate, txt) = compute_gate_text(70, gates)
    assert gate == 60
    assert txt == "Squire"


def test_compute_gate_text_none():
    gates = {
        "30": "Initiant",
        "60": "Squire",
        "120": "Veteran",
        "300": "Expert",
        "45": "Test",
    }
    (gate, txt) = compute_gate_text(20, gates)
    assert gate is None
    assert txt is None


def test_compute_next_gate_text():
    gates = {
        "30": "Initiant",
        "60": "Squire",
        "120": "Veteran",
        "300": "Expert",
        "45": "Test",
    }
    (gate, txt) = compute_next_gate_text(70, gates)
    assert gate == 120
    assert txt == "Veteran"


def test_compute_next_gate_text_none():
    gates = {
        "30": "Initiant",
        "60": "Squire",
        "120": "Veteran",
        "300": "Expert",
        "45": "Test",
    }
    (gate, txt) = compute_next_gate_text(400, gates)
    assert gate is None
    assert txt is None


def test_compute_time_txt():
    txt = compute_time_txt(45)
    assert txt == "45 mins"


def test_compute_time_txt_one_hours():
    txt = compute_time_txt(60)
    assert txt == "1 hour"


def test_compute_time_txt_one_min():
    txt = compute_time_txt(1)
    assert txt == "1 min"


def test_compute_time_txt_hours():
    txt = compute_time_txt(125)
    assert txt == "2.1 hours"


def test_compute_time_txt_hours_big():
    txt = compute_time_txt(12000)
    assert txt == "200 hours"


def test_slice_text_array_at_total_length():
    txt = ["hello", "world", "my", "name", "is", "jon", "doe"]
    r = slice_text_array_at_total_length(10, txt)
    assert r[0] == ["hello", "world"]
    assert len(r) == 3
