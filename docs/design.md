# Design

## Layout of the repo

| Path | What's there |
|---|---|
| `collector/` | Standard-library Python. Reads `/proc`, `/sys` and NVIDIA's NVML library through `ctypes`. |
| `BarWidget.qml` | One instance per monitor. Shows the bar text, connects to the collector and owns the three popups. |
| `ui/` | The report, shared pieces such as graphs and rings, and one file per card in `ui/cards/`. |
| `lib/` | Plain JavaScript with no UI, so it can be tested without a display: `format.js` for text, `metrics.js` for graphs, `layout.js` for the card list and builder operations. |
| `tests/` | Python collector tests, plus QML tests for `lib/` in `tests/qml/`. |

The collector sends one JSON line every 2 seconds over a Unix socket at
`$XDG_RUNTIME_DIR/omaview.sock`. The UI only depends on that JSON, so the collector can move
to another language later.

## Why it's cheap when idle

Each message normally carries only the bar numbers, while history keeps recording in the
collector. Per-process data, the history and full details are only collected or sent after a
client sends `detail on`, which happens while a report is open. Report contents are only
created while they're open.

The first time a report opens after a gap, the collector takes a 0.25-second process baseline
so the list shows real CPU numbers straight away.

## One collector, many monitors

Every bar starts a collector when it has no connection. A `flock` lets one win, and the rest
exit immediately. If that collector or its bar goes away, the others lose their connection
and start another within about 2 seconds.

## Following the pointer

While a report is open, the bar's hover state stops following the pointer: moving along the bar
doesn't reach the section buttons. So while a report is open, and once just before one opens,
the widget asks `hyprctl cursorpos` where the pointer is and compares it with the section
rectangles. This polls every 80 ms, and only while a report is open.

Reports open after 250 ms on CPU or GPU and 400 ms on System, switch immediately while one is
open, and close 300 ms after the pointer leaves both the bar sections and the report.

## Layouts

A layout is a list of columns of cards, such as
`{ "card": "history", "metric": "cpu.load", "size": "m" }`. Only reports that differ from the
defaults are saved, in the widget's `layouts` setting in `shell.json`, so improved defaults
still reach reports nobody customised. Unknown cards and values are dropped when loading.

Edits go to a draft while the report is pinned open, and are written once on Done or when
the report closes.

## Adding a card

1. Add it to `catalog` in `lib/layout.js`, with any sensor choices and whether it can resize.
2. Add `ui/cards/<Name>.qml`, where `<Name>` is the card id with a capital first letter. The
   card gets a `host` property with `stats`, `spec`, `theme` and `fahrenheit`. Set
   `hasContent: false` to hide it when there's nothing to show.
3. If it needs new data, add it to `collector/omaview/sampler.py` and to `mock.py`.

## Things that are easy to get wrong

- Settings arrive as Qt sequences, which fail `Array.isArray`. `layout.resolve` copies them
  into plain JavaScript first.
- A widget is created before its settings arrive, so don't act once on a setting's first value.
- Network totals count physical interfaces only, because VM bridges double count traffic.
- Process lists show names resolved from the PID, never command lines, which can hold tokens.
