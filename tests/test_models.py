from src.cleanmail.models import Action, MessageSummary


def test_action_enum_values():
    assert Action.KEEP.value == "keep"
    assert Action.ARCHIVE.value == "archive"
    assert Action.TRASH.value == "trash"
    assert Action.LABEL.value == "label"


def test_message_summary_factory(factory_message):
    msg = factory_message()
    assert msg.id == "m1"
    assert "INBOX" in msg.labels

