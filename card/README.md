# Lawn Vision Card

A custom Lovelace card for the
[Lawn Vision](https://github.com/schwarzbr0t/lawn-vision) Home Assistant
integration. Displays growth score, phase, care guide, 7-day plan and
per-action recommendations as a themed card with an optional
background image.

## Install

### Manual

1. Copy `dist/lawn-vision.js` to
   `<config>/www/community/lawn-vision/lawn-vision.js`.
2. Add it as a Lovelace resource:

   ```yaml
   url: /local/community/lawn-vision/lawn-vision.js
   type: module
   ```

3. Reload resources and create a card with `type: custom:lawn-vision-card`.

### HACS (planned)

This subdirectory is laid out so it can be moved into its own
repository, e.g. `schwarzbr0t/lawn-vision-card`, which would then be
addable as a HACS *Lovelace plugin* repository. Until that move
happens, install manually using the steps above.

## Configuration

See the main repository [README](../README.md) and
[examples/lovelace.yaml](../examples/lovelace.yaml) for the full list
of options and entity bindings. The card auto-fills sensible defaults
via `getStubConfig`, so dropping it into a dashboard works without
manual wiring when entities follow the default `sensor.lawn_vision_*`
naming.

## Preview

[preview/index.html](../preview/index.html) renders the card with
sample state so you can iterate on the design without a running
Home Assistant.
