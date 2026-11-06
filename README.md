# omaview

PC stats for the [Omarchy](https://omarchy.org) bar. The bar shows live CPU, GPU and network
numbers, and hovering a section opens a detailed report whose cards you can rearrange.

**Made by AI — use at your own peril.** I've reviewed the code, but that doesn't make it
bulletproof. Expect sharp edges.

```text
CPU 41% 45° 120W    GPU 37% 29° 36W    ↑ 1.2 MB/s ↓ 8.4 MB/s
```

<p>
  <img src="docs/images/cpu.png" alt="CPU report" height="420">
  <img src="docs/images/gpu.png" alt="GPU report" height="420">
  <img src="docs/images/system.png" alt="System report" height="420">
</p>

<sub>Screenshots use the built-in fake data, which pegs values on purpose.</sub>

## Reports

| Section | Bar shows | Report shows |
|---|---|---|
| **CPU** | Usage, temperature, power | Load graph, per-core load, top processes, load averages, uptime |
| **GPU** | Usage, temperature, power | Load, memory, temperature and clock; load graph; 3D and compute, encode, decode, JPEG and optical flow use; per-process list; GPUs passed through to a VM |
| **System** | Upload and download speed | Network and interfaces, disk space and activity, memory, swap, top processes, temperatures, fans |

## Requirements

- Omarchy with its Quickshell bar
- Python 3.11 or newer, with no extra packages and no build step
- An NVIDIA card and driver for GPU data. Other GPUs aren't read yet, but everything else
  still works.

## Install

From a checkout of this repo:

```bash
plugin=~/.config/omarchy/plugins/io.github.qnlbnsl.omaview
mkdir -p "$plugin"
cp -r BarWidget.qml manifest.json collector lib ui "$plugin/"
omarchy-shell shell rescanPlugins
omarchy plugin enable io.github.qnlbnsl.omaview
```

To remove it from the bar, run `omarchy plugin disable io.github.qnlbnsl.omaview`.

## Use

**Open a report:** hover or click a section. It closes when the pointer leaves both the
section and the report.

**Rearrange a report:** click the pencil at the top right of the report. It stays open while
you edit, and each card gets these controls:

| Control | What it does |
|---|---|
| `CPU load ›` | Switches the sensor the card shows, on cards that have a choice |
| `S` / `M` / `L` | Changes the size, on graphs and process lists |
| `↑` `↓` `←` `→` | Moves the card, including into a new column (up to three) |
| `✕` | Removes the card |

**+ Add card** adds a card to that column, **Reset** restores the report's defaults, and
**Done** saves.

**Open from a keybinding or script:** these act on the focused monitor.

```bash
omarchy-shell omaview open cpu    # or gpu, system
omarchy-shell omaview edit        # edit the report that's open
omarchy-shell omaview close
```

**Use Fahrenheit:**

```bash
omarchy bar set io.github.qnlbnsl.omaview temperatureUnit Fahrenheit
```

## Limits

- 3D and compute are one number, because that's how NVIDIA reports them.
- Per-process disk rates only cover your own processes. Other users' need root.
- Graphs cover the last 4 minutes and start empty whenever the collector restarts, which
  includes bar reloads.
- Vertical bars show a shorter form that hasn't been tested yet.
- Tested on one PC so far: Hyprland 0.56, Ryzen 9 5950X and RTX 3090.

## Development

Tests need `qt6-declarative` for the QML logic tests:

```bash
tests/run.sh                         # everything
OMAVIEW_SKIP_QML=1 tests/run.sh      # Python only
collector/omaview-collector --once   # print one full sample as JSON
```

To work on the UI with awkward values (pegged readings, long names), turn on fake data, and
set it back to `false` when you're done:

```bash
omarchy bar set io.github.qnlbnsl.omaview mock true --json
```

After changing QML, copy the files to the plugin folder and run `omarchy restart shell`. The
shell notices saved files, but didn't reliably pick up the new code in testing.

[docs/design.md](docs/design.md) explains how the parts fit together.

## License

[MIT](LICENSE)
