#!/usr/bin/env python3
"""
Layout:
- Top-left: menu/help
- Top-right: doorbell animation (CENTERED in its panel)
- Bottom: dashboard/status
- g: opens Wave Viewer screen (SIM waveform)

Main keys:
  q  quit
  d  toggle animation
  g  open wave viewer

Wave Viewer keys:
  1/2/3  scenario
  space  pause/resume
  r      regenerate
  b/esc  back (guaranteed)
"""

import math
from dataclasses import dataclass
from typing import List

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Header, Footer, Static
from textual.reactive import reactive


# ASCII ART
DOORBELL_ART = r"""
  .----.
 / .--. \
| | () | |
|  `--'  |
 \      /
  `----'
"""

LAPTOP_ART = r"""
   _____________
  |  _________  |
  | |         | |
  | |         | |
  | |_________| |
  |_____________|
   \___________/
"""

HOUSE_ART = r"""
      /\
     /  \
    /____\
    | __ |
    ||  ||
    ||__||
    |____|
"""


def build_scene(signal_index: int, stage: int, term_w: int = 80) -> str:
    """Build one frame of the doorbell->laptop->house ASCII animation, centered to term_w."""
    left_pad = 2
    col_width = 24
    bell_col = 0 * col_width + left_pad
    laptop_col = 1 * col_width + left_pad
    house_col = 2 * col_width + left_pad

    bell = DOORBELL_ART.strip("\n").splitlines()
    laptop = LAPTOP_ART.strip("\n").splitlines()
    house = HOUSE_ART.strip("\n").splitlines()

    art_h = max(len(bell), len(laptop), len(house))
    scene_w = house_col + 22
    term_w = max(term_w, scene_w + 4)

    pad_left = max(0, (term_w - scene_w) // 2)
    width = pad_left + scene_w

    canvas: List[str] = []
    for i in range(art_h):
        line = [" "] * width
        if i < len(bell):
            seg = bell[i]
            line[pad_left + bell_col : pad_left + bell_col + len(seg)] = seg
        if i < len(laptop):
            seg = laptop[i]
            line[pad_left + laptop_col : pad_left + laptop_col + len(seg)] = seg
        if i < len(house):
            seg = house[i]
            line[pad_left + house_col : pad_left + house_col + len(seg)] = seg
        canvas.append("".join(line))

    path_y = art_h + 2
    while len(canvas) <= path_y + 3:
        canvas.append(" " * width)

    # path
    base = list(canvas[path_y])
    for x in range(pad_left + bell_col + 10, pad_left + house_col + 8):
        if 0 <= x < width:
            base[x] = "-"
    canvas[path_y] = "".join(base)

    # labels
    labels_y = path_y + 2
    for label, col in [("[Doorbell]", bell_col), ("[Laptop]", laptop_col), ("[House]", house_col)]:
        row = list(canvas[labels_y])
        for i, ch in enumerate(label):
            xx = pad_left + col + i
            if 0 <= xx < len(row):
                row[xx] = ch
        canvas[labels_y] = "".join(row)

    # signal
    sig_y = path_y - 1
    if stage == 0:
        start_x = pad_left + bell_col + 10
        end_x = pad_left + laptop_col - 2
    else:
        start_x = pad_left + laptop_col + 8
        end_x = pad_left + house_col - 2

    span = max(1, end_x - start_x)
    x = start_x + max(0, min(signal_index, span))
    row = list(canvas[sig_y])
    for i, ch in enumerate(")))"):
        xx = x + i
        if 0 <= xx < width:
            row[xx] = ch
    canvas[sig_y] = "".join(row)

    return "\n".join(canvas)


# Wave render helpers
def samples_to_sparkline(samples: List[float], width: int) -> str:
    if not samples:
        return "(no samples)"
    width = max(10, width)
    step = max(1, len(samples) // width)
    pts = [samples[i] for i in range(0, len(samples), step)][:width]
    peak = max(1e-9, max(abs(x) for x in pts))
    blocks = " ▁▂▃▄▅▆▇█"
    out = []
    for x in pts:
        level = int(round((abs(x) / peak) * 8))
        level = max(0, min(8, level))
        out.append(blocks[level])
    return "".join(out)


def bits_from_samples(samples: List[float], chunk: int = 240, thresh: float = 0.18) -> str:
    if not samples:
        return ""
    bits = []
    for i in range(0, len(samples), chunk):
        seg = samples[i : i + chunk]
        if not seg:
            break
        avg = sum(abs(x) for x in seg) / len(seg)
        bits.append("1" if avg >= thresh else "0")
    return "".join(bits)


#SIM signal generator
@dataclass
class SimSignal:
    sr: int
    samples: List[float]
    label: str


def gen_sim_signal(scenario: int, seconds: float = 1.25, sr: int = 48000) -> SimSignal:
    n = int(seconds * sr)
    out: List[float] = [0.0] * n

    def env_decay(t: float, k: float) -> float:
        return math.exp(-k * t)

    if scenario == 1:
        label = "Scenario 1: pulse train"
        for i in range(n):
            t = i / sr
            burst = 1.0 if (t % 0.22) < 0.06 else 0.0
            out[i] = 0.8 * burst * math.sin(2 * math.pi * 880 * t)

    elif scenario == 2:
        label = "Scenario 2: FSK-ish"
        bit_rate = 120
        f0, f1 = 900, 1400
        for i in range(n):
            t = i / sr
            bit_i = int(t * bit_rate)
            b = 1 if (bit_i % 3) else 0
            f = f1 if b else f0
            out[i] = 0.75 * math.sin(2 * math.pi * f * t)

    else:
        label = "Scenario 3: doorbell burst"
        for i in range(n):
            t = i / sr
            if t > 0.85:
                out[i] = 0.0
                continue
            f = 500 + (1500 * min(1.0, t / 0.35))
            out[i] = 0.95 * env_decay(t, 3.2) * math.sin(2 * math.pi * f * t)

    return SimSignal(sr=sr, samples=out, label=label)


# Wave Viewer Screen 
class WaveViewerScreen(Screen):
    scenario = reactive(3)
    paused = reactive(False)

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield Static("", id="wave_top")
        yield Static("", id="wave_bottom")
        yield Footer()

    def on_mount(self) -> None:
        self._regenerate()
        self.set_interval(0.15, self._tick)

    def _regenerate(self) -> None:
        self._sig = gen_sim_signal(self.scenario)
        self._cursor = 0

    def _tick(self) -> None:
        top = self.query_one("#wave_top", Static)
        bot = self.query_one("#wave_bottom", Static)

        if not self.paused:
            self._cursor += int(self._sig.sr * 0.03)
            if self._cursor >= len(self._sig.samples):
                self._cursor = 0

        w = max(60, self.size.width - 6)
        window = int(self._sig.sr * 0.18)
        start = self._cursor
        end = min(len(self._sig.samples), start + window)
        seg = self._sig.samples[start:end]

        wave = samples_to_sparkline(seg, width=min(w, 180))
        bits = bits_from_samples(self._sig.samples, chunk=240, thresh=0.18)
        bits_tail = bits[-256:] if bits else ""

        top.update(
            "Wave Viewer (SIM)\n"
            "------------------\n"
            f"{self._sig.label}\n"
            f"Sample rate: {self._sig.sr} Hz | paused={self.paused}\n\n"
            "Wave blip:\n"
            f"{wave}\n"
        )

        bot.update(
            "Derived 01s (simple amplitude threshold, tail):\n"
            f"{bits_tail}\n\n"
            "Keys:\n"
            "  1/2/3  scenario\n"
            "  space  pause/resume\n"
            "  r      regenerate\n"
            "  b/esc  back\n"
        )

    def on_key(self, event) -> None:
        k = event.key

        if k in ("escape", "b"):
            event.prevent_default()
            event.stop()
            self.app.pop_screen()
            return

        if k == "space":
            event.prevent_default()
            event.stop()
            self.paused = not self.paused
            return

        if k == "r":
            event.prevent_default()
            event.stop()
            self._regenerate()
            return

        if k in ("1", "2", "3"):
            event.prevent_default()
            event.stop()
            self.scenario = int(k)
            self._regenerate()
            return


# Main App
class SDRForgeApp(App):
    CSS = """
    Screen { layout: vertical; }
    #top-row { height: 60%; }
    #menu-panel { width: 40%; border: solid #666666; padding: 1 2; }
    #doorbell-panel { width: 60%; border: solid #666666; padding: 0 1; }
    #dashboard-panel { border: solid #666666; padding: 1 2; }
    #wave_top { height: 60%; border: solid #666666; padding: 1 2; }
    #wave_bottom { height: 40%; border: solid #666666; padding: 1 2; }
    """

    BINDINGS = [
        ("q", "quit_app", "Quit"),
        ("d", "toggle_doorbell", "Toggle Doorbell"),
        ("g", "open_wave", "Open Wave Viewer"),
    ]

    _anim_idx = 0
    _anim_stage = 0
    _anim_running = True

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="top-row"):
            with Vertical():
                yield Static(
                    "SDRForge Menu\n"
                    "----------------\n"
                    "Keys:\n"
                    "  d  – Toggle doorbell animation\n"
                    "  g  – Open Wave Viewer (SIM)\n"
                    "  q  – Quit\n",
                    id="menu-panel",
                )
            yield Static("", id="doorbell-panel")
        yield Static(
            "SDRForge Dashboard\n"
            "-------------------\n"
            "Status: Ready.\n\n"
            "Keys:\n"
            "  d  – Toggle doorbell animation\n"
            "  g  – Open Wave Viewer (SIM)\n"
            "  q  – Quit\n",
            id="dashboard-panel",
        )
        yield Footer()

    def on_mount(self) -> None:
        self.set_interval(0.04, self._tick_doorbell)

    def _set_status(self, msg: str) -> None:
        dash = self.query_one("#dashboard-panel", Static)
        dash.update(
            "SDRForge Dashboard\n"
            "-------------------\n"
            f"Status: {msg}\n\n"
            "Keys:\n"
            "  d  – Toggle doorbell animation\n"
            "  g  – Open Wave Viewer (SIM)\n"
            "  q  – Quit\n"
        )

    def _tick_doorbell(self) -> None:
        if not self._anim_running:
            return

        self._anim_idx += 1
        if self._anim_idx >= 30:
            self._anim_idx = 0
            self._anim_stage = 1 - self._anim_stage

        panel = self.query_one("#doorbell-panel", Static)
        panel_width = panel.size.width or self.size.width

        panel.update(build_scene(self._anim_idx, self._anim_stage, term_w=panel_width))

    def action_quit_app(self) -> None:
        self.exit()

    def action_toggle_doorbell(self) -> None:
        self._anim_running = not self._anim_running
        if not self._anim_running:
            self.query_one("#doorbell-panel", Static).update("(animation paused)")
        self._set_status("Doorbell animation toggled.")

    def action_open_wave(self) -> None:
        self.push_screen(WaveViewerScreen())


if __name__ == "__main__":
    SDRForgeApp().run()

