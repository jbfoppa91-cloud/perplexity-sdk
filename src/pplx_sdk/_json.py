from __future__ import annotations

import json
from typing import Protocol, cast

_PATCHED_ATTR = "_pplx_sdk_json_encoder_installed"


class _SdkJsonable(Protocol):
    def to_dict(self) -> object: ...


def _is_sdk_jsonable(value: object) -> bool:
    value_type = type(value)
    module = value_type.__module__
    if module != "pplx_sdk" and not module.startswith("pplx_sdk."):
        return False
    return callable(getattr(value, "to_dict", None))


def _to_jsonable(value: object) -> object:
    return cast(_SdkJsonable, value).to_dict()


def install_json_encoder() -> None:
    encoder_cls = json.JSONEncoder
    if getattr(encoder_cls, _PATCHED_ATTR, False):
        return

    previous_default = encoder_cls.default

    def default(self: json.JSONEncoder, value: object) -> object:
        if _is_sdk_jsonable(value):
            return _to_jsonable(value)
        return previous_default(self, value)

    setattr(encoder_cls, "default", default)
    setattr(encoder_cls, _PATCHED_ATTR, True)
