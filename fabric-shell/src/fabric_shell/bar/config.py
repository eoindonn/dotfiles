import psutil
from fabric import Application, Fabricator
from fabric.widgets.box import Box
from fabric.widgets.image import Image
from fabric.widgets.eventbox import EventBox
from fabric.widgets.datetime import DateTime
from fabric.widgets.centerbox import CenterBox
from fabric.system_tray.widgets import SystemTray
from fabric.widgets.circularprogressbar import CircularProgressBar
from fabric.widgets.wayland import WaylandWindow as Window
from fabric.widgets.button import Button
from fabric.hyprland.widgets import (
    HyprlandActiveWindow,
    HyprlandWorkspaces,
    WorkspaceButton,
)
from fabric.utils import FormattedString, get_relative_path, bulk_replace
import os
import subprocess
AUDIO_WIDGET = True

if AUDIO_WIDGET is True:
    try:
        from fabric.audio.service import Audio
    except Exception as e:
        AUDIO_WIDGET = False
        print(e)

class NotificationCenter(Window):
    def __init__(self):
        super().__init__(
            name="notification-center",
            anchor="top right",
            margin="50px 10px 0px 0px",
            visible=False,
        )

class PowerNotch(Window):
    def __init__(self):
        self._open = True
        menu = Box(
            orientation="h",
            spacing=10,
            name="power-notch",
            children=[
                Button(name="power-off-button", label="", on_clicked=lambda *_: os.system("systemctl poweroff")),
                Button(name="reboot-button", label="", on_clicked=lambda *_: os.system("systemctl reboot")),
                Button(name="suspend-button", label="", on_clicked=lambda *_: os.system("systemctl suspend")),
            ],
        )

        super().__init__(
            name="power-notch-window",
            anchor="top right",
            margin="0px 10px 0px 0px",
            visible=True,
            child=menu,
        )
        self.hide()

    def toggle(self):
        self._open = not self._open
        if self._open:
            self.hide()
        else:
            self.show()

class PowerWidget(Box):
    def __init__(self, notch: PowerNotch, **kwargs):
        self.notch = notch

        self.button = Button(
            name="power-button",
            image=Image(icon_name="system-shutdown-symbolic", icon_size=18),
            on_clicked=lambda *_: self.notch.toggle(),
        )

        super().__init__(
            children=[self.button],
            **kwargs,
        )


class VolumeWidget(Box):
    def __init__(self, **kwargs):
        self.progress_bar = CircularProgressBar(
            name="volume-progress-bar",
            pie=True,
            child=Image(icon_name="audio-speakers-symbolic", icon_size=20),
            size=24,
        )

        super().__init__(
            children=EventBox(
                events="scroll",
                child=self.progress_bar,
                on_scroll_event=self.on_scroll
            ),
            **kwargs,
        )

        Fabricator(
            interval=1000,
            poll_from=lambda _: self.get_volume(),
            on_changed=lambda _, v: self.progress_bar.set_value(v),
        )

    def get_volume(self):
        out = subprocess.check_output(
            ["wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@"]
        ).decode()

        return float(out.split()[1])

    def set_volume(self, delta):
        subprocess.call([
            "wpctl",
            "set-volume",
            "@DEFAULT_AUDIO_SINK@",
            delta
        ])

    def on_scroll(self, _, event):
        if event.direction == 0:
            self.set_volume("+5%")
        else:
            self.set_volume("-5%")

        self.progress_bar.set_value(self.get_volume())


class StatusBar(Window):
    def __init__(
        self,
        monitor,
    ):
        super().__init__(
            name="bar",
            layer="top",
            anchor="left top right",
            margin="10px 10px -2px 10px",
            exclusivity="auto",
            visible=False,
            monitor=monitor
        )

        def update_battery_style(widget, value):
            battery = psutil.sensors_battery()

            widget.remove_style_class("charging")
            widget.remove_style_class("critical")
            widget.remove_style_class("plugged")

            if battery.power_plugged:
                widget.add_style_class("plugged")
            else:
                widget.add_style_class("discharging")

            if value <= 0.15:
                widget.add_style_class("critical")

        self.notification_button = Button(
            name="notification-button",
            image=Image(icon_name="message-new-symbolic", icon_size=18),
            on_clicked=lambda *_: os.system("swaync-client -t"),
        )

        self.system_status = Box(
            name="system-status",
            spacing=4,
            orientation="h",
            children=[
                CircularProgressBar(
                    name="ram-progress-bar",
                    pie=True,
                    child=Image(icon_name="memory-symbolic", icon_size=18),
                    size=24,
                ).build(
                    lambda progres: Fabricator(
                        interval=1000,
                        poll_from=lambda f: psutil.virtual_memory().percent / 100,
                        on_changed=lambda _, value: progres.set_value(value),
                    )
                ),
                CircularProgressBar(
                        name="cpu-progress-bar",
                        pie=True,
                        child=Image(icon_name="cpu-symbolic", icon_size=16),
                        size=24,
                ).build(
                    lambda progres: Fabricator(
                        interval=1000,
                        poll_from=lambda f: psutil.cpu_percent() / 100,
                        on_changed=lambda _, value: progres.set_value(value),
                    )
                ),
                CircularProgressBar(
                        name="battery-progress-bar",
                        pie=True,
                        child=Image(icon_name="battery-symbolic", icon_size=17),
                        size=24,
                ).build(
                    lambda progres: Fabricator(
                        interval=1000,
                        poll_from=lambda f: psutil.sensors_battery().percent / 100,
                        on_changed=lambda _, value:( progres.set_value(value),
                        update_battery_style(progres, value),
                        ),
                    )
                )
            ]
            # create a volume widget if enabled
            + ([VolumeWidget()] if AUDIO_WIDGET else []),
        )


        self.notch = PowerNotch()
        self.power_widget = PowerWidget(notch=self.notch)
        self.children = CenterBox(
            name="bar-inner",
            start_children=Box(
                name="start-container",
                children=HyprlandWorkspaces(
                    name="workspaces",
                    spacing=4,
                    buttons_factory=lambda ws_id: WorkspaceButton(id=ws_id, label=None),
                ),
            ),
            center_children=Box(
                name="center-container",
                children=HyprlandActiveWindow(name="hyprland-window"),
            ),
            end_children=Box(
                name="end-container",
                spacing=4,
                orientation="h",
                children=[
                    self.system_status,
                    SystemTray(name="system-tray", spacing=4),
                    self.notification_button,
                    DateTime(name="date-time"),
                    self.power_widget,
                ],
            ),
        )

        return self.show_all()

def get_monitors():
    import gi
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gdk
    display = Gdk.Display.get_default()
    return list(range(display.get_n_monitors()))

if __name__ == "__main__":
    app = Application("bar")

    monitors = get_monitors()

    bars = []
    for m in monitors:
        bar = StatusBar(monitor=m)
        bars.append(bar)

    for bar in bars:
        app.add_window(bar)

    app.set_stylesheet_from_file(get_relative_path("./style.css"))
    app.run()