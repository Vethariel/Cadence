"""Tests de restricciones técnicas explícitas en el prompt."""

from cadence.music.prompt_technical_constraints import (
    parse_prompt_instrument_requests,
    prompt_context_tokens,
)


def test_guitar_and_piano_split_layers():
    reqs = parse_prompt_instrument_requests(
        "musica lofi instrumental con guitarra y piano",
    )
    assert len(reqs) == 2
    assert reqs[0].instrument_id == "melody"
    assert reqs[0].gm_program in range(24, 31)
    assert reqs[1].instrument_id == "chord_stab"
    assert reqs[1].gm_program in {0, 1, 2, 3, 4, 5}


def test_single_piano_on_melody():
    reqs = parse_prompt_instrument_requests("pieza con piano solamente")
    assert len(reqs) == 1
    assert reqs[0].instrument_id == "melody"
    assert reqs[0].gm_program in {0, 1, 2, 3, 4, 5}


def test_fretless_bass_on_bass_layer():
    reqs = parse_prompt_instrument_requests("groove con bajo fretless")
    assert len(reqs) == 1
    assert reqs[0].instrument_id == "bass"
    assert reqs[0].gm_program == 35


def test_harp_on_arp_layer():
    reqs = parse_prompt_instrument_requests("melodía con arpa y violín")
    assert len(reqs) == 2
    by_layer = {r.instrument_id: r.gm_program for r in reqs}
    assert by_layer["arp_synth"] == 46
    assert by_layer["melody"] == 40


def test_strings_on_pad():
    reqs = parse_prompt_instrument_requests("fondo de cuerdas suaves")
    assert len(reqs) == 1
    assert reqs[0].instrument_id == "pad"
    assert reqs[0].gm_program == 48


def test_violin_and_cello_countermelody():
    reqs = parse_prompt_instrument_requests("dúo de violín y violonchelo")
    assert len(reqs) == 2
    assert reqs[0].instrument_id == "melody"
    assert reqs[0].gm_program == 40
    assert reqs[1].instrument_id == "countermelody"
    assert reqs[1].gm_program == 42


def test_square_lead_chiptune():
    reqs = parse_prompt_instrument_requests("lead square 8-bit")
    assert reqs[0].instrument_id == "melody"
    assert reqs[0].gm_program == 80


def test_no_instruments_without_explicit_mention():
    assert parse_prompt_instrument_requests("musica lofi instrumental") == []


def test_organ_not_matched_inside_organizacion():
    assert parse_prompt_instrument_requests("música para organización del evento") == []


def test_prompt_context_tokens_only_when_mentioned():
    assert "guitar" in prompt_context_tokens("con guitarra")
    assert "piano" in prompt_context_tokens("con piano")
    assert "bass" in prompt_context_tokens("bajo fretless")
    assert "guitar" not in prompt_context_tokens("musica ambiente")


if __name__ == "__main__":
    test_guitar_and_piano_split_layers()
    test_single_piano_on_melody()
    test_fretless_bass_on_bass_layer()
    test_harp_on_arp_layer()
    test_strings_on_pad()
    test_violin_and_cello_countermelody()
    test_square_lead_chiptune()
    test_no_instruments_without_explicit_mention()
    test_organ_not_matched_inside_organizacion()
    test_prompt_context_tokens_only_when_mentioned()
    print("✓ prompt_technical_constraints tests passed")
