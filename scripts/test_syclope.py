#!/usr/bin/env python3
"""Test minimal du Syclope HydroTouch CHY0444 via Waveshare RTU-over-TCP."""

from __future__ import annotations

import argparse
import os
import struct

from pymodbus import FramerType
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

DEFAULT_HOST = os.getenv("SYCLOPE_HOST", "192.168.1.200")
DEFAULT_PORT = int(os.getenv("SYCLOPE_PORT", "4196"))
DEFAULT_DEVICE_ID = int(os.getenv("SYCLOPE_DEVICE_ID", "1"))

PH_ADDRESS = 1202       # PLC 41203
REDOX_ADDRESS = 1302    # PLC 41303


def read_holding(
    client: ModbusTcpClient,
    address: int,
    count: int,
    device_id: int,
):
    """Compatibilité avec plusieurs versions récentes de PyModbus."""
    try:
        return client.read_holding_registers(
            address=address,
            count=count,
            device_id=device_id,
        )
    except TypeError:
        return client.read_holding_registers(
            address=address,
            count=count,
            slave=device_id,
        )


def decode_cdab(registers: list[int]) -> float:
    """Décode un float32 dont les mots 16 bits sont inversés (ABCD -> CDAB)."""
    if len(registers) != 2:
        raise ValueError("Deux registres sont nécessaires pour un float32.")
    first, second = registers
    raw = second.to_bytes(2, "big") + first.to_bytes(2, "big")
    return struct.unpack(">f", raw)[0]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Lit les mesures pH et Redox du CHY0444 en lecture seule."
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help="Adresse IP du Waveshare (défaut: %(default)s)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="Port TCP de données série (défaut: %(default)s)",
    )
    parser.add_argument(
        "--device-id",
        type=int,
        default=DEFAULT_DEVICE_ID,
        help="Adresse esclave Modbus (défaut: %(default)s)",
    )
    args = parser.parse_args()

    client = ModbusTcpClient(
        host=args.host,
        port=args.port,
        framer=FramerType.RTU,
        timeout=5,
        retries=0,
    )

    if not client.connect():
        raise SystemExit(f"Connexion TCP impossible vers {args.host}:{args.port}")

    try:
        ph_response = read_holding(client, PH_ADDRESS, 2, args.device_id)
        redox_response = read_holding(client, REDOX_ADDRESS, 2, args.device_id)

        for label, response in (("pH", ph_response), ("Redox", redox_response)):
            if response.isError():
                raise RuntimeError(f"Réponse Modbus en erreur pour {label}: {response}")

        ph = decode_cdab(list(ph_response.registers))
        redox = decode_cdab(list(redox_response.registers))

        print(f"pH: {ph:.4f}")
        print(f"Redox: {redox:.2f} mV")

    except ModbusException as exc:
        raise SystemExit(f"Erreur Modbus: {exc}") from exc
    finally:
        client.close()


if __name__ == "__main__":
    main()
