from src.cleanmail.policies import is_whitelisted, is_protected, fast_heuristics, policy_decide
from src.cleanmail.models import Action


def test_is_whitelisted(factory_message):
    msg = factory_message(from_addr="boss@company.com")
    assert is_whitelisted(msg, ["boss@company.com"], [])
    msg2 = factory_message(from_addr="alerts@company.com")
    assert is_whitelisted(msg2, [], ["company.com"]) is True


def test_is_protected(factory_message):
    msg = factory_message(labels=["INBOX", "STARRED"])
    assert is_protected(msg, ["STARRED"]) is True


def test_fast_heuristics(factory_message):
    msg = factory_message(subject="WIN MONEY now!!!")
    action, reason = fast_heuristics(msg)
    assert action in (Action.TRASH, Action.ARCHIVE)


def test_policy_decide_conservative(factory_message):
    msg = factory_message(subject="WIN MONEY now!!!")
    cfg = {"safety": {"whitelist_senders": [], "whitelist_domains": [], "never_touch_labels": []}}
    decision = policy_decide(msg, cfg)
    assert decision is not None
    # spammy subject downgraded to ARCHIVE by conservative policy
    assert decision.action in (Action.ARCHIVE, Action.KEEP)

