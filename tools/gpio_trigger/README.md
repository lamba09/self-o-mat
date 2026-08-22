# GPIO trigger panel

Drives the hand trigger, print switch and status LEDs from the Pi's GPIO header.
It talks to the booth over HTTP, so no controller board is needed. Run self-o-mat
with `"has_button": false`.

## Wiring

Pin number is the physical pin on the 40-pin header. GPIO number is the BCM
number used in `selfomat_gpio_trigger.py`. Inputs use the Pi's pull-ups: close
them to ground. LEDs need a series resistor to ground.

| Signal | Pin number | GPIO number |
| --- | --- | --- |
| Hand trigger | 11 | 17 |
| Print switch | 13 | 27 |
| Confirm print | 18 | 24 |
| Cancel print | 22 | 25 |
| Ready LED | 15 | 22 |
| Busy LED | 16 | 23 |

Closing the switch disables printing. Flip `SWITCH_CLOSED_ENABLES_PRINTING` if
yours is wired the other way round.

## Behaviour

- Trigger posts `/trigger`. When printing is on, further presses are ignored for
  `--dead-time` (55 s by default) so the print queue cannot pile up. With printing
  off there is no dead time. The booth rejects triggers with HTTP 503 while the
  captured image is still on screen.
- The switch sets the printer enabled flag at startup and whenever it is flipped.
  A change in the web UI lasts until the next flip. Turning printing off also
  clears any remaining dead time.
- Confirm posts `/confirm_print`. That only matters with "Additionally confirm
  print with a button press" enabled; the booth's `print_decision_millis` is the
  window in which a press counts.
- Cancel posts `/cancel_print`. With confirmation off, that is how you skip a
  print; with it on, it is the counterpart to confirm.
- Ready LED: a trigger would be accepted. Busy LED: dead time.
- Capture is immediate. There is no countdown.

## Install

Needs `python3-libgpiod` (2.x). The service uses group `dialout` for
`/dev/gpiochip0`.

```bash
sudo cp selfomat-gpio-trigger.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now selfomat-gpio-trigger
journalctl -u selfomat-gpio-trigger -f
```

Check wiring without taking pictures:

```bash
./selfomat_gpio_trigger.py --dry-run --verbose
```
