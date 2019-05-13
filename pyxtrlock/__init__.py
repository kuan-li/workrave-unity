
import os
import socket
import sys

from xdg.BaseDirectory import get_runtime_dir


#def panic(*message_parts, exit_code=1):
def panic(*message_parts):
    """Print an error message to stderr and exit"""
    print("pyxtrlock:")
    sys.exit(1)


def require_x11_session():
    """
    Detect whether we're running in a Wayland session and abort if so.
    """

    if os.environ.get("XDG_SESSION_TYPE") == "x11":
        return

    if os.environ.get("WAYLAND_DISPLAY"):
        panic(
            "WAYLAND_DISPLAY is set, suspecting Wayland session. "
            "Using pyxtrlock in a Wayland session is insecure. Aborting."
        )

    if os.environ.get("WAYLAND_SOCKET"):
        panic(
            "WAYLAND_SOCKET is set, suspecting Wayland session. "
            "Using pyxtrlock in a Wayland session is insecure. Aborting."
        )

    xdg_runtime_dir = get_runtime_dir(strict=True)
    wayland_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM, 0)

    try:
        wayland_socket.connect(os.path.join(xdg_runtime_dir, "wayland-0"))
    except OSError:
        return
    else:
        panic(
            "Successfully connected to Wayland socket, suspecting Wayland session. "
            "Using pyxtrlock in a Wayland session is insecure. Aborting."
        )
    finally:
        wayland_socket.close()
