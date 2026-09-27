import pytest
from pynput import keyboard

from dictate import get_hotkey, hotkey_label


@pytest.mark.parametrize("value", ["0x1008ffb1", "0X1008FFB1", "269025201"])
def test_key_number_builds_matching_keycode(value):
    assert get_hotkey(value) == keyboard.KeyCode.from_vk(0x1008FFB1)


def test_unknown_key_falls_back_to_cmd(capsys):
    assert get_hotkey("not_a_key") is keyboard.Key.cmd
    # The dummy backend folds every named Key into one member, so only the warning proves the fallback ran.
    assert "Unknown key: not_a_key" in capsys.readouterr().out


def test_label_for_key_number_is_hex():
    assert hotkey_label(get_hotkey("0x1008ffb1")) == "0x1008ffb1"


def test_label_for_char_key():
    assert hotkey_label(get_hotkey("a")) == "a"

