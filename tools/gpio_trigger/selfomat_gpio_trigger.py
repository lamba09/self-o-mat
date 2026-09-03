#!/usr/bin/env python3
"""Drives the photobooth's buttons, print switch and status LEDs from the Pi.

This replaces the external trigger board. Rather than speaking the board's serial
protocol, it uses self-o-mat's HTTP API: with no controller connected, a remote
trigger captures directly, so the booth needs no microcontroller at all. Run
self-o-mat with "has_button": false alongside this.
"""

import argparse
import logging
import signal
import subprocess
import time
import urllib.error
import urllib.request
from datetime import timedelta

import gpiod
from gpiod.line import Bias, Direction, Edge, Value

# --- Wiring -----------------------------------------------------------------
# Line offsets on gpiochip0, which are the BCM pin numbers on a Pi 4. Buttons
# and the switch close to ground and use the internal pull-ups, so nothing but
# the switch itself is needed. LEDs need a series resistor to ground.
GPIO_CHIP = "/dev/gpiochip0"
TRIGGER_LINE = 17
SWITCH_LINE = 27
CONFIRM_LINE = 24
CANCEL_LINE = 25
SHUTDOWN_LINE = 5
READY_LED_LINE = 22
BUSY_LED_LINE = 23

SHUTDOWN_HOLD_SECONDS = 3.0

# The switch selected "test image" mode on the board this replaces: closed meant
# take pictures but do not print. Set True if yours is wired the other way round.
SWITCH_CLOSED_ENABLES_PRINTING = False

DEBOUNCE = timedelta(milliseconds=20)
POLL_INTERVAL = timedelta(milliseconds=200)
RETRY_SECONDS = 2.0

LOG = logging.getLogger("gpio-trigger")


class BoothApi:
    """The few endpoints needed to stand in for the trigger board."""

    def __init__(self, base_url, timeout=3.0, dry_run=False):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.dry_run = dry_run

    def _post(self, path, body=b""):
        """Returns the HTTP status, or None if the booth could not be reached."""
        if self.dry_run:
            LOG.info("would POST %s (%d bytes)", path, len(body))
            return 200

        request = urllib.request.Request(self.base_url + path, data=body, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.status
        except urllib.error.HTTPError as error:
            return error.code
        except OSError as error:
            LOG.warning("cannot reach the booth at %s: %s", self.base_url, error)
            return None

    def trigger(self):
        return self._post("/trigger")

    def confirm_print(self):
        return self._post("/confirm_print")

    def cancel_print(self):
        return self._post("/cancel_print")

    def set_printer_enabled(self, enabled):
        # A BoolUpdate is a single varint field, so the body is two bytes and
        # this needs no protobuf runtime.
        return self._post(
            "/booth_settings/printer/enabled", b"\x08\x01" if enabled else b"\x08\x00"
        )


def printing_from_switch(switch_closed):
    if SWITCH_CLOSED_ENABLES_PRINTING:
        return switch_closed
    return not switch_closed


def request_app_shutdown(dry_run=False):
    """Ask self-o-mat to exit the same way Ctrl-C would."""
    if dry_run:
        LOG.info("would send SIGINT to self_o_mat.app")
        return True

    result = subprocess.run(
        ["pkill", "-INT", "-f", "self_o_mat.app"],
        check=False,
    )
    if result.returncode == 0:
        LOG.info("sent SIGINT to self-o-mat")
        return True

    LOG.warning("self-o-mat is not running")
    return False


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default="http://127.0.0.1:9080",
                        help="base URL of the self-o-mat API")
    parser.add_argument("--dead-time", type=float, default=55.0, metavar="SECONDS",
                        help="how long to ignore the trigger after a capture when "
                             "printing is on, so prints cannot pile up in the queue")
    parser.add_argument("--dry-run", action="store_true",
                        help="log requests instead of sending them, to check wiring")
    parser.add_argument("--shutdown-hold", type=float, default=SHUTDOWN_HOLD_SECONDS,
                        metavar="SECONDS",
                        help="how long the shutdown button must stay pressed")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    api = BoothApi(args.api, dry_run=args.dry_run)
    running = True

    def request_stop(signum, _frame):
        nonlocal running
        LOG.info("got signal %d, shutting down", signum)
        running = False

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    button = gpiod.LineSettings(
        direction=Direction.INPUT,
        bias=Bias.PULL_UP,
        active_low=True,
        edge_detection=Edge.BOTH,
        debounce_period=DEBOUNCE,
    )
    led = gpiod.LineSettings(direction=Direction.OUTPUT, output_value=Value.INACTIVE)

    with gpiod.request_lines(
        GPIO_CHIP,
        consumer="selfomat-gpio-trigger",
        config={
            TRIGGER_LINE: button,
            SWITCH_LINE: button,
            CONFIRM_LINE: button,
            CANCEL_LINE: button,
            SHUTDOWN_LINE: button,
            READY_LED_LINE: led,
            BUSY_LED_LINE: led,
        },
    ) as lines:
        pressed = lines.get_value(TRIGGER_LINE) == Value.ACTIVE
        switch_closed = lines.get_value(SWITCH_LINE) == Value.ACTIVE
        confirm_pressed = lines.get_value(CONFIRM_LINE) == Value.ACTIVE
        cancel_pressed = lines.get_value(CANCEL_LINE) == Value.ACTIVE
        LOG.info("trigger %s, printing %s",
                 "pressed" if pressed else "released",
                 "on" if printing_from_switch(switch_closed) else "off")

        # Push the switch position once at startup so the panel and the booth
        # agree. Beyond that only changes are sent: the booth persists the
        # setting to disk on every request, and it reloads it on startup, so
        # resending periodically would just wear out the card.
        printing_enabled = printing_from_switch(switch_closed)
        wanted_printing = printing_enabled
        next_attempt = 0.0
        busy_until = 0.0
        shutdown_hold_since = None
        shutdown_sent = False

        while running:
            now = time.monotonic()

            if wanted_printing is not None and now >= next_attempt:
                status = api.set_printer_enabled(wanted_printing)
                if status == 200:
                    LOG.info("printing %s", "enabled" if wanted_printing else "disabled")
                    wanted_printing = None
                else:
                    LOG.warning("could not set printing (status %s), retrying", status)
                    next_attempt = now + RETRY_SECONDS

            busy = printing_enabled and now < busy_until
            lines.set_value(BUSY_LED_LINE, Value.ACTIVE if busy else Value.INACTIVE)
            lines.set_value(READY_LED_LINE, Value.INACTIVE if busy else Value.ACTIVE)

            shutdown_pressed = lines.get_value(SHUTDOWN_LINE) == Value.ACTIVE
            if shutdown_pressed:
                if shutdown_hold_since is None:
                    shutdown_hold_since = now
                    shutdown_sent = False
                elif (
                    not shutdown_sent
                    and now - shutdown_hold_since >= args.shutdown_hold
                ):
                    if request_app_shutdown(args.dry_run):
                        shutdown_sent = True
            else:
                shutdown_hold_since = None
                shutdown_sent = False

            try:
                if not lines.wait_edge_events(POLL_INTERVAL):
                    continue
                lines.read_edge_events()
            except OSError as error:
                if not running:
                    break
                LOG.warning("edge wait failed: %s", error)
                continue

            # The event tells us a line moved; the current levels tell us where
            # it ended up, which avoids reasoning about edge direction under
            # active_low and collapses any bounce we did not debounce away.
            was_pressed, pressed = pressed, lines.get_value(TRIGGER_LINE) == Value.ACTIVE
            was_closed, switch_closed = switch_closed, lines.get_value(SWITCH_LINE) == Value.ACTIVE
            was_confirming, confirm_pressed = (
                confirm_pressed, lines.get_value(CONFIRM_LINE) == Value.ACTIVE
            )
            was_cancelling, cancel_pressed = (
                cancel_pressed, lines.get_value(CANCEL_LINE) == Value.ACTIVE
            )

            if switch_closed != was_closed:
                printing_enabled = printing_from_switch(switch_closed)
                wanted_printing = printing_enabled
                next_attempt = 0.0
                if not printing_enabled:
                    busy_until = 0.0

            if confirm_pressed and not was_confirming:
                status = api.confirm_print()
                if status == 200:
                    LOG.info("print confirmed")
                elif status == 409:
                    LOG.info("confirm ignored, print decision already closed")
                else:
                    LOG.error("confirming the print failed (status %s)", status)

            if cancel_pressed and not was_cancelling:
                status = api.cancel_print()
                if status == 200:
                    busy_until = 0.0
                    LOG.info("print canceled, dead time cleared")
                elif status == 409:
                    LOG.info("cancel ignored, print decision already closed")
                else:
                    LOG.error("canceling the print failed (status %s)", status)

            if pressed and not was_pressed:
                if busy:
                    LOG.info("trigger ignored, %.0fs of dead time left", busy_until - now)
                    continue

                status = api.trigger()
                if status == 200:
                    if printing_enabled:
                        busy_until = time.monotonic() + args.dead_time
                        LOG.info("triggered, dead time %.0fs", args.dead_time)
                    else:
                        LOG.info("triggered (printing off, no dead time)")
                elif status == 503:
                    LOG.warning("booth is not ready to capture")
                else:
                    LOG.error("trigger failed (status %s)", status)

        lines.set_value(READY_LED_LINE, Value.INACTIVE)
        lines.set_value(BUSY_LED_LINE, Value.INACTIVE)

    LOG.info("stopped")


if __name__ == "__main__":
    main()
