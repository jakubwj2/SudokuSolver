"""Type stubs for python-for-android's android.permissions (device builds only)."""

from collections.abc import Callable, Sequence

class Permission:
    CAMERA: str
    READ_EXTERNAL_STORAGE: str
    WRITE_EXTERNAL_STORAGE: str

def request_permissions(
    permissions: Sequence[str],
    callback: Callable[..., object] | None = None,
) -> None: ...
