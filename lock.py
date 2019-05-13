
import os
import sys
import time
import getpass
from ctypes import byref, cast
from ctypes import POINTER, c_int, c_uint32, c_char

from xdg.BaseDirectory import load_data_paths

from pyxtrlock.cursor_file import load_cursor
from pyxtrlock import panic
from pyxtrlock import require_x11_session

try:
    import pyxtrlock.xcb as xcb
except ImportError as err:
    panic(err)

import subprocess

try:
    import pyxtrlock.X as X
except ImportError as err:
    panic(err)

def lock_screen(log1,timer_set):

    subprocess.call(["gedit", log1])

    require_x11_session()

    if getpass.getuser() == 'root' and sys.argv[1:] != ['-f']:
        msg = (
            "refusing to run as root. Use -f to force. Warning: "
            "Your PAM configuration may deny unlocking as root."
        )
        panic(msg)

    # load cursor data file 
    try:
        for directory in load_data_paths("pyxtrlock"):
            f_name = os.path.join(directory, "cursor.json")
            if os.path.exists(f_name):
                with open(f_name, "r") as f:
                    cursor = load_cursor(f)
                break
        else:
            from pyxtrlock.default_cursor import DEFAULT_CURSOR as cursor
    except OSError as e:
        panic("error reading cursor:", e.strerror)
    except Exception as e:
        panic("error reading cursor:", str(e))

    display = X.create_window(None)
    conn = X.get_xcb_connection(display)

    if not display:
        panic("Could not connect to X server")

    screen_num = c_int()

    setup = xcb.get_setup(conn)

    iter_ = xcb.setup_roots_iterator(setup)

    while screen_num.value:
        xcb.screen_next(byref(iter_))
        screen_num.value -= 1

    screen = iter_.data.contents

    # create window
    window = xcb.generate_id(conn)

    attribs = (c_uint32 * 2)(1, xcb.EVENT_MASK_KEY_PRESS)
    ret = xcb.create_window(conn, xcb.COPY_FROM_PARENT, window, screen.root,
                            0, 0, 1, 1, 0, xcb.WINDOW_CLASS_INPUT_ONLY,
                            xcb.VisualID(xcb.COPY_FROM_PARENT),
                            xcb.CW_OVERRIDE_REDIRECT | xcb.CW_EVENT_MASK,
                            cast(byref(attribs), POINTER(c_uint32)))

    # create cursor
    csr_map = xcb.image_create_pixmap_from_bitmap_data(conn, window,
                                                       cursor["fg_bitmap"],
                                                       cursor["width"],
                                                       cursor["height"],
                                                       1, 0, 0, None)
    csr_mask = xcb.image_create_pixmap_from_bitmap_data(conn, window,
                                                        cursor["bg_bitmap"],
                                                        cursor["width"],
                                                        cursor["height"],
                                                        1, 0, 0, None)

    try:
        r, g, b = cursor["bg_color"]
        csr_bg = xcb.alloc_color_sync(conn, screen.default_colormap,
                                      r, g, b)
        r, g, b = cursor["fg_color"]
        csr_fg = xcb.alloc_color_sync(conn, screen.default_colormap,
                                      r, g, b)
    except ValueError as e:
        panic(str(e))
    except xcb.XCBError as e:
        panic("Could not allocate colors")

    try:
        cursor = xcb.create_cursor_sync(conn, csr_map, csr_mask, csr_fg, csr_bg,
                                        cursor["x_hot"], cursor["y_hot"])
    except xcb.XCBError as e:
        panic("Could not create cursor")

    # map window
    xcb.map_window(conn, window)

    # Grab keyboard
    # Use the method from the original xtrlock code:
    #  "Sometimes the WM doesn't ungrab the keyboard quickly enough if
    #  launching xtrlock from a keystroke shortcut, meaning xtrlock fails
    #  to start We deal with this by waiting (up to 100 times) for 10,000
    #  microsecs and trying to grab each time. If we still fail
    #  (i.e. after 1s in total), then give up, and emit an error"

    for i in range(100):
        try:
            status = xcb.grab_keyboard_sync(conn, 0, window,
                                            xcb.CURRENT_TIME,
                                            xcb.GRAB_MODE_ASYNC,
                                            xcb.GRAB_MODE_ASYNC)

            if status == xcb.GrabSuccess:
                break
            else:
                time.sleep(0.01)
        except xcb.XCBError as e:
            time.sleep(0.01)
    else:
        panic("Could not grab keyboard")

    # Grab pointer
    for i in range(100):
        try:
            status = xcb.grab_pointer_sync(conn, False, window, 0,
                                           xcb.GRAB_MODE_ASYNC,
                                           xcb.GRAB_MODE_ASYNC,
                                           xcb.WINDOW_NONE, cursor,
                                           xcb.CURRENT_TIME)

            if status == xcb.GrabSuccess:
                break
            else:
                time.sleep(0.01)
        except xcb.XCBError as e:
            time.sleep(0.01)
    else:
        panic("Could not grab pointing device")

    xcb.flush(conn)

    # implement the XSS_SLEEP_LOCK_FD sleep delay protocol
    xss_fd = os.getenv("XSS_SLEEP_LOCK_FD")
    if xss_fd is not None:
        try:
            os.close(int(xss_fd))
        except OSError:
            # ignore if the fd was invalid
            pass
        except ValueError:
            # ignore if the variable did not contain an fd
            pass

    # Prepare X Input
    im = X.open_IM(display, None, None, None)
    if not im:
        panic("Could not open Input Method")

    ic = X.create_IC(im, X.N_INPUT_STYLE,
                     X.IM_PRE_EDIT_NOTHING | X.IM_STATUS_NOTHING, None)
    if not ic:
        panic("Could not open Input Context")

    X.set_ic_focus(ic)

    time.sleep(timer_set)

    X.close_window(display)
