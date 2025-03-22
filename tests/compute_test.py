from common.compute import (
    compute_gate,
    compute_next_gate,
    compute_gate_text,
    compute_next_gate_text,
    compute_time_txt,
    slice_text_array_at_total_length,
    split_chunks,
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


def test_compute_time_txt_one_sec():
    txt = compute_time_txt(0.0166666666666667)
    assert txt == "1 sec"


def test_compute_time_txt_thirty_secs():
    txt = compute_time_txt(0.5)
    assert txt == "30 secs"


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


def test_split_chunks_splits_chunks_max_chunk_size():
    sample_text = """
this line is at up to length 033
this line is at up to length 066
this line is at up to length 099
this line is at up to length 132
this line is at up to length 165
this line is at up to length 198
this line is at up to length 231
"""
    chunks = split_chunks(sample_text, 100)
    assert len(chunks) == 3
    assert chunks[0].splitlines()[-1] == "this line is at up to length 099"


def test_split_chunks_empty_string():
    sample_text = ""
    chunks = split_chunks(sample_text, 100)
    assert len(chunks) == 0


def test_split_chunks_single_line():
    sample_text = "this is a single line"
    chunks = split_chunks(sample_text, 100)
    assert len(chunks) == 1
    assert chunks[0] == "this is a single line\n"


def test_split_chunks_exact_chunk_size():
    sample_text = """
this line is at up to length 033
this line is at up to length 066
this line is at up to length 099
"""
    chunks = split_chunks(sample_text.strip(), 33)
    assert len(chunks) == 3
    assert chunks[0] == "this line is at up to length 033\n"
    assert chunks[1] == "this line is at up to length 066\n"
    assert chunks[2] == "this line is at up to length 099\n"


def test_split_chunks_large_chunk_size():
    sample_text = """
this line is at up to length 033
this line is at up to length 066
this line is at up to length 099
"""
    chunks = split_chunks(sample_text, 1000)
    assert len(chunks) == 1
    assert chunks[0].splitlines()[-1] == "this line is at up to length 099"
