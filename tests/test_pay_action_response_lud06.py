from lnurl import LnurlErrorResponse
from lnurl.models import LnurlPayActionResponse, LnurlResponse


def test_from_dict_pay_action_response_without_routes():
    """
    LUD-06 success form: callback response that only contains `pr`
    (and optional fields like `successAction`, `disposable`) MUST
    be parsed as LnurlPayActionResponse even when `routes` is omitted.
    """
    data = {
        "pr": (
            "lnbc1pnsu5z3pp57getmdaxhg5kc9yh2a2qsh7cjf4gnccgkw0qenm8vsqv50w7s"
            "ygqdqj0fjhymeqv9kk7atwwscqzzsxqyz5vqsp5e2yyqcp0a3ujeesp24ya0glej"
            "srh703md8mrx0g2lyvjxy5w27ss9qxpqysgqyjreasng8a086kpkczv48er5c6l5"
            "73aym6ynrdl9nkzqnag49vt3sjjn8qdfq5cr6ha0vrdz5c5r3v4aghndly0hplmv"
            "6hjxepwp93cq398l3s"
        ),
        "successAction": {
            "tag": "message",
            "message": "LNURL pay to user@example.com",
        },
        "disposable": False,
        # NOTE: `routes` is intentionally omitted here.
    }

    res = LnurlResponse.from_dict(data)

    assert isinstance(res, LnurlPayActionResponse)
    assert res.pr == data["pr"]
    assert res.successAction is not None
    assert res.disposable is False


def test_from_dict_pay_action_response_pr_only_no_status():
    """
    Regression test for the original reported error:
        LnurlResponseException: Expected Success or Error response. But no 'status' given.

    A callback response body that contains only `pr` (no `routes`, no `status`) must
    not raise that exception — it must be parsed as LnurlPayActionResponse.
    Even though LUD06 specified an required empty `routes` array some services omit it.
    """
    data = {
        "pr": (
            "lnbc1pnsu5z3pp57getmdaxhg5kc9yh2a2qsh7cjf4gnccgkw0qenm8vsqv50w7s"
            "ygqdqj0fjhymeqv9kk7atwwscqzzsxqyz5vqsp5e2yyqcp0a3ujeesp24ya0glej"
            "srh703md8mrx0g2lyvjxy5w27ss9qxpqysgqyjreasng8a086kpkczv48er5c6l5"
            "73aym6ynrdl9nkzqnag49vt3sjjn8qdfq5cr6ha0vrdz5c5r3v4aghndly0hplmv"
            "6hjxepwp93cq398l3s"
        ),
        # NOTE: no `routes`, no `status` — the minimal real-world payload that
        # triggered "Expected Success or Error response. But no 'status' given."
    }

    res = LnurlResponse.from_dict(data)

    assert isinstance(res, LnurlPayActionResponse)
    assert res.pr == data["pr"]
    assert res.routes == []


def test_from_dict_error_response_with_status_error():
    """
    LUD-06 error form: any response shaped as
        {"status": "ERROR", "reason": "error details..."}
    must be parsed as LnurlErrorResponse with the correct reason.
    """
    data = {
        "status": "ERROR",
        "reason": "error details...",
    }

    res = LnurlResponse.from_dict(data)

    assert isinstance(res, LnurlErrorResponse)
    assert res.reason == "error details..."
    assert res.ok is False
