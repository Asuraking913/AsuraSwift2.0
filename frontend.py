"""AsuraSwift -- offline file and folder transfer over a local network.

A four-step guided flow. Addresses are discovered over UDP broadcast rather
than typed, so there is no IP, port or buffer field to fill in.

Sending:   Mode -> Device -> Files -> Transfer
Receiving: Mode -> Save to -> Waiting -> Transfer
"""
import os
import socket
import threading
import time
from pathlib import Path

import PySimpleGUI as sg

import client
import discovery
import filepicker
import server
from protocol import DEFAULT_PORT, build_manifest, human_bytes, human_time

THEME = "DarkGrey13"
ACCENT = "#4FC3F7"
MUTED = "#6E7681"
OK_GREEN = "#5CB85C"
FIELD_BG = "#21262D"
FIELD_FG = "#C9D1D9"
RULE = "#30363D"
ERR_RED = "#D9534F"

FONT_TITLE = ("Helvetica", 19, "bold")
FONT_CRUMB = ("Helvetica", 9)
FONT_STEP = ("Helvetica", 13, "bold")
FONT_BODY = ("Helvetica", 11)
FONT_SMALL = ("Helvetica", 9)
FONT_BTN = ("Helvetica", 11, "bold")

CRUMBS = {
    "send": ["Mode", "Device", "Files", "Transfer"],
    "recv": ["Mode", "Save to", "Waiting", "Transfer"],
}
NUMERALS = "①②③④"

HELP_TEXT = """AsuraSwift - User Guide

Both computers must be on the same network. A phone hotspot works well:
have both machines join it. No internet or mobile data is used - the
files travel directly between the two computers.

To receive:
  1. Click RECEIVE.
  2. Choose the folder to save into.
  3. Wait. Your computer announces itself automatically.

To send:
  1. Click SEND.
  2. Pick the receiving computer from the list. It appears on its own -
     there is no address to type. Start the receiver first.
  3. Choose files and/or folders, then press Send.

If the list stays empty, the network may be blocking device discovery.
Use "Enter address manually" and type the address shown on the
receiving computer's waiting screen."""

ABOUT_TEXT = """AsuraSwift

Developed by AsuraKing913 (Israel Shedrack)

A graphical tool for moving files and folders between two computers on
the same local network, with no internet connection required.

Feedback: israelshedrack913@gmail.com"""


def crumb_bar():
    row = []
    for i in range(4):
        if i:
            row.append(sg.Text("-", font=FONT_CRUMB, text_color=MUTED, pad=((4, 4), 0)))
        row.append(sg.Text("", font=FONT_CRUMB, text_color=MUTED,
                           key=f"crumb-{i}", pad=(0, 0)))
    return row


def build_window():
    sg.theme(THEME)

    step_mode = [
        [sg.Text("What would you like to do?", font=FONT_STEP, pad=(0, (18, 4)))],
        [sg.Text("Start the receiving computer first.",
                 font=FONT_SMALL, text_color=MUTED, pad=(0, (0, 22)))],
        [sg.Button("SEND", key="mode-send", size=(13, 2), font=FONT_BTN,
                   button_color=("white", "#1F6FEB")),
         sg.Text("  "),
         sg.Button("RECEIVE", key="mode-recv", size=(13, 2), font=FONT_BTN,
                   button_color=("white", "#2C974B"))],
    ]

    step_device = [
        [sg.Text("Choose a device", font=FONT_STEP, pad=(0, (14, 2)))],
        [sg.Text("Nearby computers running AsuraSwift appear here.",
                 font=FONT_SMALL, text_color=MUTED, pad=(0, (0, 8)))],
        [sg.Listbox([], size=(44, 7), key="device-list", font=FONT_BODY,
                    enable_events=True, background_color=FIELD_BG,
                    text_color=FIELD_FG, no_scrollbar=True,
                    highlight_background_color=ACCENT,
                    highlight_text_color="black")],
        [sg.Text("Searching...", key="device-status", font=FONT_SMALL,
                 text_color=MUTED, size=(44, 1), pad=(0, (4, 6)))],
        [sg.Button("Test on this computer", key="device-test",
                   font=FONT_SMALL, border_width=0),
         sg.Button("Enter address manually", key="device-manual",
                   font=FONT_SMALL, border_width=0)],
    ]

    step_dest = [
        [sg.Text("Where should files be saved?", font=FONT_STEP, pad=(0, (14, 2)))],
        [sg.Text("Incoming files are written into this folder.",
                 font=FONT_SMALL, text_color=MUTED, pad=(0, (0, 12)))],
        [sg.Input(str(Path.home() / "Downloads"), key="dest-input", size=(34, 1),
                  font=FONT_BODY, disabled=True, text_color=FIELD_FG,
                  disabled_readonly_background_color=FIELD_BG,
                  disabled_readonly_text_color=FIELD_FG),
         sg.Button("Browse", key="dest-browse", font=FONT_SMALL)],
        [sg.Text("", key="dest-warn", font=FONT_SMALL, text_color=ERR_RED,
                 size=(46, 1), pad=(0, (10, 0)))],
    ]

    step_files = [
        [sg.Text("What do you want to send?", font=FONT_STEP, pad=(0, (14, 2)))],
        [sg.Text("Add as many files and folders as you like.",
                 font=FONT_SMALL, text_color=MUTED, pad=(0, (0, 8)))],
        [sg.Button("Add files", key="files-add", font=FONT_SMALL),
         sg.Button("Add folder", key="folder-add", font=FONT_SMALL),
         sg.Button("Remove", key="files-remove", font=FONT_SMALL),
         sg.Button("Clear", key="files-clear", font=FONT_SMALL)],
        [sg.Listbox([], size=(44, 6), key="files-list", font=FONT_SMALL,
                    enable_events=True, background_color=FIELD_BG,
                    text_color=FIELD_FG, no_scrollbar=True,
                    highlight_background_color=ACCENT,
                    highlight_text_color="black")],
        [sg.Text("Nothing selected", key="files-summary", font=FONT_SMALL,
                 text_color=MUTED, size=(46, 1))],
    ]

    step_wait = [
        [sg.Text("Waiting for a sender...", font=FONT_STEP, pad=(0, (26, 6)))],
        [sg.Text("This computer is visible to senders on the network.",
                 font=FONT_SMALL, text_color=MUTED, pad=(0, (0, 16)))],
        [sg.Text("", key="wait-addr", font=("Helvetica", 15, "bold"),
                 text_color=ACCENT)],
        [sg.Text("", key="wait-name", font=FONT_SMALL, text_color=MUTED,
                 pad=(0, (2, 16)))],
        [sg.Text("If the sender cannot find this computer, have them enter\n"
                 "the address above manually.",
                 font=FONT_SMALL, text_color=MUTED, justification="center")],
    ]

    step_transfer = [
        [sg.Text("Transfer", key="xfer-title", font=FONT_STEP, pad=(0, (20, 8)))],
        [sg.Text("", key="xfer-file", font=FONT_SMALL, text_color=MUTED,
                 size=(48, 1))],
        [sg.ProgressBar(1000, orientation="h", size=(38, 22), key="xfer-bar",
                        bar_color=(ACCENT, "#30363D"), pad=(0, (6, 6)))],
        [sg.Text("0%", key="xfer-pct", font=FONT_BODY, size=(6, 1)),
         sg.Text("", key="xfer-rate", font=FONT_SMALL, text_color=MUTED,
                 size=(38, 1))],
        [sg.Text("", key="xfer-status", font=FONT_BODY, size=(48, 2),
                 pad=(0, (12, 0)))],
    ]

    def col(layout, key, visible=False):
        return sg.Column(layout, key=key, visible=visible,
                         element_justification="center", pad=(0, 0))

    layout = [
        [sg.Menu([["Info", ["Help", "About"]]], key="menu",
                 background_color=FIELD_BG, text_color=FIELD_FG)],
        [sg.Text("AsuraSwift", font=FONT_TITLE, pad=(0, (10, 2)))],
        crumb_bar(),
        [sg.HorizontalSeparator(color=RULE, pad=(0, 10))],
        [col(step_mode, "step-mode", visible=True),
         col(step_device, "step-device"),
         col(step_dest, "step-dest"),
         col(step_files, "step-files"),
         col(step_wait, "step-wait"),
         col(step_transfer, "step-transfer")],
        [sg.VPush()],
        [sg.HorizontalSeparator(color=RULE, pad=(0, (10, 8)))],
        [sg.Button("Back", key="nav-back", font=FONT_BTN, size=(11, 1),
                   visible=False),
         sg.Push(),
         sg.Button("Next", key="nav-next", font=FONT_BTN, size=(12, 1),
                   visible=False, button_color=("white", "#1F6FEB"))],
    ]

    return sg.Window("AsuraSwift", layout, size=(470, 505), finalize=True,
                     element_justification="center", margins=(16, 8))


class Progress:
    """Rate-limits transport callbacks into GUI events and tracks speed/ETA."""

    def __init__(self, window, interval=0.12):
        self.window = window
        self.interval = interval
        self.start = time.time()
        self.last = 0.0

    def __call__(self, done, total, name):
        now = time.time()
        if now - self.last < self.interval and done != total:
            return
        self.last = now
        elapsed = max(now - self.start, 1e-6)
        rate = done / elapsed
        eta = (total - done) / rate if rate > 0 and total else 0
        self.window.write_event_value("-PROGRESS-", (done, total, name, rate, eta))


def main():
    window = build_window()
    state = {
        "mode": None,      # 'send' | 'recv'
        "step": 0,
        "browser": None,
        "beacon": None,
        "peers": [],
        "peer": None,
        "self_peer": None,   # this machine, added on demand for same-PC testing
        "paths": [],
        "busy": False,
    }
    cancel = threading.Event()

    def set_crumbs():
        labels = CRUMBS.get(state["mode"], CRUMBS["send"])
        for i, label in enumerate(labels):
            window[f"crumb-{i}"].update(
                f"{NUMERALS[i]} {label}",
                text_color=ACCENT if i == state["step"] else MUTED)

    def show(panel):
        for key in ("step-mode", "step-device", "step-dest", "step-files",
                    "step-wait", "step-transfer"):
            window[key].update(visible=(key == panel))

    def stop_browser():
        if state["browser"]:
            state["browser"].stop()
            state["browser"] = None

    def stop_beacon():
        if state["beacon"]:
            state["beacon"].stop()
            state["beacon"] = None

    def shorten(path, width=52):
        return path if len(path) <= width else "..." + path[-(width - 3):]

    def refresh_devices(keep_selection=True):
        """Redraw the device list: this computer first if added, then the network."""
        found = state["browser"].peers() if state["browser"] else []
        if state["self_peer"]:
            # A beacon from our own address is filtered out by discovery, so the
            # self entry never arrives over the network -- it is added here.
            found = [state["self_peer"]] + [p for p in found
                                            if p["ip"] != state["self_peer"]["ip"]]
        state["peers"] = found
        window["device-list"].update(
            [f"{p['name']}    {p['ip']}" for p in found])

        if state["peer"] and keep_selection:
            for i, p in enumerate(found):
                if p["ip"] == state["peer"]["ip"]:
                    window["device-list"].update(set_to_index=[i])
                    break

        network = [p for p in found if p is not state["self_peer"]]
        if network:
            window["device-status"].update(f"{len(network)} device(s) found",
                                           text_color=OK_GREEN)
        elif state["self_peer"]:
            window["device-status"].update("Testing on this computer",
                                           text_color=ACCENT)
        else:
            window["device-status"].update("Searching...", text_color=MUTED)

    def refresh_files():
        paths = state["paths"]
        window["files-list"].update([shorten(p) for p in paths])
        if not paths:
            window["files-summary"].update("Nothing selected", text_color=MUTED)
            window["nav-next"].update("Send", disabled=True)
            return
        try:
            _, files, total = build_manifest(paths)
        except OSError as exc:
            window["files-summary"].update(f"Cannot read selection: {exc}",
                                           text_color=ERR_RED)
            window["nav-next"].update("Send", disabled=True)
            return
        window["files-summary"].update(
            f"{len(files)} file(s) - {human_bytes(total)}", text_color=ACCENT)
        window["nav-next"].update("Send", disabled=(len(files) == 0))

    def start_send():
        state["busy"] = True
        cancel.clear()
        peer = state["peer"]
        window["xfer-title"].update(f"Sending to {peer['name']}")
        window["xfer-status"].update("", text_color=sg.theme_text_color())
        report = Progress(window)

        def work():
            try:
                count, sent = client.send_session(
                    peer["ip"], peer["port"], list(state["paths"]),
                    on_progress=report,
                    on_status=lambda m: window.write_event_value("-STATUS-", m),
                    cancel=cancel)
                window.write_event_value("-DONE-", (count, sent))
            except Exception as exc:
                window.write_event_value("-ERROR-", str(exc))

        threading.Thread(target=work, daemon=True).start()

    def start_receive():
        state["busy"] = True
        cancel.clear()
        dest = window["dest-input"].get()
        state["beacon"] = discovery.Beacon(port=DEFAULT_PORT)
        state["beacon"].start()
        report = Progress(window)

        def work():
            listener = None
            try:
                listener = server.listen(DEFAULT_PORT)
                count, got = server.receive_session(
                    dest, server=listener,
                    on_progress=report,
                    on_status=lambda m: window.write_event_value("-STATUS-", m),
                    on_peer=lambda ip: window.write_event_value("-PEER-", ip),
                    cancel=cancel)
                window.write_event_value("-DONE-", (count, got))
            except Exception as exc:
                window.write_event_value("-ERROR-", str(exc))
            finally:
                if listener:
                    listener.close()

        threading.Thread(target=work, daemon=True).start()

    def goto(new_step):
        state["step"] = new_step
        set_crumbs()

        if new_step == 0:
            stop_browser()
            stop_beacon()
            show("step-mode")
            window["nav-back"].update(visible=False)
            window["nav-next"].update(visible=False)
            return

        window["nav-back"].update(visible=True, disabled=False)
        window["nav-next"].update(visible=True)

        if state["mode"] == "send":
            if new_step == 1:
                show("step-device")
                if state["browser"] is None:
                    state["browser"] = discovery.Browser()
                    state["browser"].start()
                refresh_devices()
                window["nav-next"].update("Next", disabled=(state["peer"] is None))
            elif new_step == 2:
                stop_browser()
                show("step-files")
                refresh_files()
            elif new_step == 3:
                show("step-transfer")
                window["nav-next"].update(visible=False)
                window["nav-back"].update(disabled=True)
                start_send()
        else:
            if new_step == 1:
                stop_beacon()
                show("step-dest")
                window["nav-next"].update("Next", disabled=False)
            elif new_step == 2:
                show("step-wait")
                window["wait-addr"].update(f"{discovery.local_ip()}:{DEFAULT_PORT}")
                window["wait-name"].update(socket.gethostname())
                window["nav-next"].update(visible=False)
                start_receive()
            elif new_step == 3:
                show("step-transfer")
                window["nav-next"].update(visible=False)
                window["nav-back"].update(disabled=True)

    def finish(text, color):
        state["busy"] = False
        stop_beacon()
        window["xfer-status"].update(text, text_color=color)
        window["xfer-file"].update("")
        window["nav-back"].update(visible=True, disabled=False, text="Start over")

    goto(0)

    while True:
        event, value = window.read(timeout=400)

        if event in (sg.WINDOW_CLOSED, None):
            break

        if event == "Help":
            sg.popup_scrolled(HELP_TEXT, title="Help", size=(60, 24), font=FONT_BODY)
        elif event == "About":
            sg.popup(ABOUT_TEXT, title="About", font=FONT_BODY)

        elif event == "mode-send":
            state["mode"] = "send"
            state["peer"] = None
            state["self_peer"] = None
            state["paths"].clear()
            goto(1)
        elif event == "mode-recv":
            state["mode"] = "recv"
            goto(1)

        elif event == "device-list":
            idxs = window["device-list"].get_indexes()
            if idxs and idxs[0] < len(state["peers"]):
                state["peer"] = state["peers"][idxs[0]]
                window["nav-next"].update(disabled=False)
        elif event == "device-test":
            # local_ip() already falls back to loopback if no LAN interface is up
            state["self_peer"] = {"name": "This computer (test)",
                                  "ip": discovery.local_ip(),
                                  "port": DEFAULT_PORT}
            state["peer"] = state["self_peer"]
            refresh_devices()
            window["nav-next"].update(disabled=False)
        elif event == "device-manual":
            entered = sg.popup_get_text(
                "Address shown on the receiving computer\n(for example 10.106.251.88)",
                title="Enter address", font=FONT_BODY)
            if entered:
                host, _, port_txt = entered.strip().partition(":")
                try:
                    port = int(port_txt) if port_txt else DEFAULT_PORT
                except ValueError:
                    sg.popup_error("That port is not a number.", font=FONT_BODY)
                else:
                    state["peer"] = {"name": host, "ip": host, "port": port}
                    window["device-status"].update(f"Using {host}", text_color=ACCENT)
                    window["nav-next"].update(disabled=False)

        elif event == "dest-browse":
            chosen = filepicker.pick_folder("Save received files into")
            if chosen:
                window["dest-input"].update(chosen)
                window["dest-warn"].update("")

        elif event == "files-add":
            picked = filepicker.pick_files("Select files to send")
            if picked:
                state["paths"].extend(picked)
                refresh_files()
        elif event == "folder-add":
            picked = filepicker.pick_folder("Select folder to send")
            if picked:
                state["paths"].append(picked)
                refresh_files()
        elif event == "files-remove":
            for i in sorted(window["files-list"].get_indexes(), reverse=True):
                if i < len(state["paths"]):
                    state["paths"].pop(i)
            refresh_files()
        elif event == "files-clear":
            state["paths"].clear()
            refresh_files()

        elif event == "nav-next":
            if state["mode"] == "recv" and state["step"] == 1:
                dest = window["dest-input"].get()
                try:
                    os.makedirs(dest, exist_ok=True)
                except OSError as exc:
                    window["dest-warn"].update(f"Cannot use that folder: {exc}")
                    continue
                if not os.access(dest, os.W_OK):
                    window["dest-warn"].update("That folder is not writable.")
                    continue
            goto(state["step"] + 1)
        elif event == "nav-back":
            if state["busy"] or state["step"] >= 3:
                cancel.set()
                state["busy"] = False
                window["nav-back"].update(text="Back")
                window["xfer-bar"].update(0)
                window["xfer-pct"].update("0%")
                window["xfer-rate"].update("")
                window["xfer-status"].update("")
                state["mode"] = None
                goto(0)
            else:
                goto(state["step"] - 1)

        elif event == "-PROGRESS-":
            done, total, name, rate, eta = value[event]
            if state["step"] == 2:
                goto(3)
            frac = (done / total) if total else 0
            window["xfer-bar"].update(int(frac * 1000))
            window["xfer-pct"].update(f"{frac * 100:.0f}%")
            window["xfer-rate"].update(
                f"{human_bytes(rate)}/s - {human_time(eta)} left - "
                f"{human_bytes(done)} of {human_bytes(total)}")
            if name:
                window["xfer-file"].update(shorten(name))
        elif event == "-STATUS-":
            window["xfer-status"].update(value[event],
                                         text_color=sg.theme_text_color())
        elif event == "-PEER-":
            window["xfer-title"].update(f"Receiving from {value[event]}")
            if state["step"] == 2:
                goto(3)
        elif event == "-DONE-":
            count, moved = value[event]
            verb = "Sent" if state["mode"] == "send" else "Received"
            finish(f"{verb} {count} file(s) - {human_bytes(moved)}", OK_GREEN)
        elif event == "-ERROR-":
            finish(f"Transfer failed:\n{value[event]}", ERR_RED)

        if (event == sg.TIMEOUT_KEY and state["mode"] == "send"
                and state["step"] == 1 and state["browser"]):
            refresh_devices()

    cancel.set()
    stop_browser()
    stop_beacon()
    window.close()


if __name__ == "__main__":
    main()
