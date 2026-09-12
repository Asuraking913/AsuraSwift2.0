"""Native file and folder choosers, with a fallback for machines that lack one.

PySimpleGUI's popup_get_file/popup_get_folder go through tkinter.filedialog,
which on Linux draws Tk's own chooser rather than the desktop's. It has no
sidebar, no thumbnails and no path bar, so getting anywhere takes a lot of
double-clicking.

This asks the desktop for its real dialog instead -- kdialog on KDE, zenity on
GNOME and friends -- and only falls back to the Tk chooser when neither is
installed, so the app still runs anywhere.
"""
import os
import shutil
import subprocess

TIMEOUT = 600           # a dialog left open this long is treated as abandoned
_last_dir = None        # reopen where the user last was


def _backend():
    for name in ("kdialog", "zenity"):
        if shutil.which(name):
            return name
    return None


def _start_dir(start):
    candidate = start or _last_dir or os.path.expanduser("~")
    if not os.path.isdir(candidate):
        candidate = os.path.expanduser("~")
    return candidate


def _remember(paths):
    global _last_dir
    if paths:
        first = paths[0]
        _last_dir = first if os.path.isdir(first) else os.path.dirname(first)
    return paths


def _run(args):
    """Return a list of chosen paths, or [] if cancelled/unavailable."""
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=TIMEOUT)
    except (OSError, subprocess.SubprocessError):
        return None                      # backend unusable; caller falls back
    if done.returncode != 0:
        return []                        # user cancelled
    return [line for line in done.stdout.strip().splitlines() if line]


def pick_files(title="Select files", start=None):
    """One or more files. Returns a list, empty if the user cancelled."""
    where = _start_dir(start)
    backend = _backend()

    if backend == "kdialog":
        got = _run(["kdialog", "--title", title, "--getopenfilename",
                    where, "--multiple", "--separate-output"])
    elif backend == "zenity":
        got = _run(["zenity", "--file-selection", f"--title={title}",
                    f"--filename={where}{os.sep}", "--multiple",
                    "--separator=\n"])
    else:
        got = None

    if got is None:
        import PySimpleGUI as sg
        raw = sg.popup_get_file(title, no_window=True, multiple_files=True,
                                initial_folder=where)
        got = [p for p in str(raw).split(";") if p] if raw else []

    return _remember(got)


def pick_folder(title="Select folder", start=None):
    """A single folder. Returns a path, or None if the user cancelled."""
    where = _start_dir(start)
    backend = _backend()

    if backend == "kdialog":
        got = _run(["kdialog", "--title", title,
                    "--getexistingdirectory", where])
    elif backend == "zenity":
        got = _run(["zenity", "--file-selection", "--directory",
                    f"--title={title}", f"--filename={where}{os.sep}"])
    else:
        got = None

    if got is None:
        import PySimpleGUI as sg
        chosen = sg.popup_get_folder(title, no_window=True,
                                     initial_folder=where)
        got = [chosen] if chosen else []

    got = _remember(got)
    return got[0] if got else None


def describe():
    """Which chooser is in use -- handy when a bug report says 'the dialog'."""
    return {"kdialog": "KDE native", "zenity": "GTK native"}.get(
        _backend(), "tkinter fallback")
