# -*- coding: utf-8 -*-
"""
High-level Python client for the MixTrain LabVIEW TCP server.

Protocol:
    - TCP host: 127.0.0.1
    - TCP port: 30002
    - ASCII commands terminated by CRLF
    - One command per TCP connection
    - ASCII reply terminated by CRLF

The LabVIEW side should implement the corresponding MT:* commands.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass


class MixTrainError(RuntimeError):
    """Raised when the MixTrain server returns an error response."""


@dataclass
class MixTrain:
    host: str = "127.0.0.1"
    port: int = 30002
    timeout: float = 3.0

    def send_command(self, command: str) -> str:
        """Send one command and return the stripped ASCII reply."""
        command = command.strip()

        if not command:
            raise ValueError("Command must not be empty.")

        payload = (command + "\r\n").encode("ascii")

        with socket.create_connection(
            (self.host, self.port),
            timeout=self.timeout,
        ) as sock:
            sock.settimeout(self.timeout)
            sock.sendall(payload)

            chunks = []
            while True:
                chunk = sock.recv(1024)
                if not chunk:
                    break

                chunks.append(chunk)

                # LabVIEW replies are CRLF terminated.
                if b"\r\n" in b"".join(chunks):
                    break

        reply = b"".join(chunks).decode("ascii", errors="replace").strip()

        if not reply:
            raise MixTrainError(f"No reply to command: {command}")

        if reply.upper().startswith(("ERR", "ERROR")):
            raise MixTrainError(reply)

        return reply

    # ------------------------------------------------------------------
    # Temperature controller
    # ------------------------------------------------------------------

    def get_temperature(self) -> float:
        """Return actual temperature in °C."""
        return float(self.send_command("MT:TEMP?"))

    def get_setpoint(self) -> float:
        """Return temperature setpoint in °C."""
        return float(self.send_command("MT:SETPOINT?"))

    def set_setpoint(self, temperature_c: float) -> str:
        """Set temperature setpoint in °C."""
        value = float(temperature_c)
        return self.send_command(f"MT:SET:SETPOINT {value:.6g}")

    def get_peltier_duty_cycle(self) -> float:
        """Return the Peltier controller output/duty-cycle value."""
        return float(self.send_command("MT:PELTIER?"))

    def get_resistive_duty_cycle(self) -> float:
        """Return the resistive-heater controller output/duty-cycle value."""
        return float(self.send_command("MT:RESISTIVE?"))

    def get_stabilization(self) -> bool:
        """Return True when temperature stabilization is enabled."""
        reply = self.send_command("MT:STABILIZATION?")

        if reply == "1":
            return True
        if reply == "0":
            return False

        raise MixTrainError(
            f"Unexpected stabilization reply: {reply!r}; expected '0' or '1'."
        )

    def set_stabilization(self, enabled: bool | int) -> str:
        """Enable/disable temperature stabilization."""
        if isinstance(enabled, bool):
            value = int(enabled)
        elif isinstance(enabled, int) and enabled in (0, 1):
            value = enabled
        else:
            raise ValueError("enabled must be True/False or integer 0/1.")

        return self.send_command(f"MT:SET:STABILIZATION {value}")

    # ------------------------------------------------------------------
    # Crystal / motor
    # ------------------------------------------------------------------

    def get_crystal_period(self) -> int:
        """Return current crystal period."""
        return int(self.send_command("MT:PERIOD?"))

    def set_crystal_period(self, period: int) -> str:
        """
        Set crystal period.

        Allowed range is 1..21. The LabVIEW side should use
        Crystal Period.Value (Signaling), so the existing motor logic runs.
        """
        if isinstance(period, bool) or not isinstance(period, int):
            raise TypeError("Crystal period must be an integer.")

        if not 1 <= period <= 21:
            raise ValueError("Crystal period must be between 1 and 21.")

        return self.send_command(f"MT:SET:PERIOD {period}")

    def is_busy(self) -> bool:
        """Return the current MixTrain busy state."""
        reply = self.send_command("MT:BUSY?")

        if reply == "1":
            return True
        if reply == "0":
            return False

        raise MixTrainError(
            f"Unexpected busy reply: {reply!r}; expected '0' or '1'."
        )

    # ------------------------------------------------------------------
    # Shutters
    # ------------------------------------------------------------------

    def get_tisa_shutter(self) -> bool:
        """Return Ti:Sa shutter state; requires MT:SHUTTER:TISA? in LabVIEW."""
        reply = self.send_command("MT:SHUTTER:TISA?")
        if reply == "1":
            return True
        if reply == "0":
            return False
        raise MixTrainError(f"Unexpected Ti:Sa shutter reply: {reply!r}")

    def get_fiber_shutter(self) -> bool:
        """Return fiber-laser shutter state; requires MT:SHUTTER:FIBER?."""
        reply = self.send_command("MT:SHUTTER:FIBER?")
        if reply == "1":
            return True
        if reply == "0":
            return False
        raise MixTrainError(f"Unexpected fiber shutter reply: {reply!r}")
