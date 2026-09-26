import pytest

from dictate import remove_fillers


@pytest.mark.parametrize(
    "text, expected",
    [
        ("Well, um, I think", "Well, I think"),
        ("uh hello world", "Hello world"),
        ("hello world, uh.", "hello world."),
        ("Um, so we go.", "So we go."),
        ("Uh, um.", ""),
        ("The umbrella and summer herb, ahead.", "The umbrella and summer herb, ahead."),
        ("UM okay", "Okay"),
        ("The vim, uh, the editor, um, is fast.", "The vim, the editor, is fast."),
        ("I said 5 mm of cloth.", "I said 5 mm of cloth."),
        ("...um... okay", "Okay"),
        ("I think, um.", "I think."),
        ("So, uh, you know, er, it works", "So, you know, it works"),
        ("Hmm? What?", "What?"),
        ("hello world", "hello world"),
        ("Uh-oh, it broke.", "Uh-oh, it broke."),
        ("uh-huh, sure", "uh-huh, sure"),
        ("He said mm-hmm.", "He said mm-hmm."),
        ("It's mm-hmm, I agree.", "It's mm-hmm, I agree."),
        ("um's a thing", "um's a thing"),
        ("5'er", "5'er"),
        ('"Um," she said.', "She said."),
        ('He said "um" loudly', "He said loudly"),
        ("Pāḷi um mettā", "Pāḷi mettā"),
        ("hello (um) world", "hello world"),
        ("[uh] okay then", "Okay then"),
        ("‘Um,’ she said.", "She said."),
        ("(see above) okay", "(see above) okay"),
    ],
)
def test_remove_fillers(text, expected):
    assert remove_fillers(text) == expected
