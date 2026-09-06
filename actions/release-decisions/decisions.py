from typing import Literal, NamedTuple

Severity = Literal["notice", "error"]


class ReleaseVerdict(NamedTuple):
    proceed: bool
    severity: Severity
    message: str
