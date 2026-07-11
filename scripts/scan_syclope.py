#!/usr/bin/env python3
"""Cartographie en lecture seule des Holding Registers du CHY0444."""

from __future__ import annotations

import argparse
import csv
import math
import os
import struct
import time
from datetime import datetime
from pathlib import Path

from pymodbus import FramerType
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException

DEFAULT_HOST = os.getenv("SYCLOPE_HOST", "192.168.1.200")
DEFAULT_PORT = int(os.getenv("SYCLOPE_PORT", "4196"))
DEFAULT_DEVICE_ID = int(os.getenv("SYCLOPE_DEVICE_ID", "1"))


def read_holding(
    client: ModbusTcpClient,
    address: int,
    count: int,
    device_id: int,
):
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


def signed16(value: int) -> int:
    return value - 65536 if value >= 32768 else value


def decode_float_variants(a: int, b: int) -> dict[str, float | None]:
    wa = a.to_bytes(2, "big")
    wb = b.to_bytes(2, "big")
    payloads = {
        "ABCD": wa + wb,
        "CDAB": wb + wa,
        "BADC": wa[::-1] + wb[::-1],
        "DCBA": wb[::-1] + wa[::-1],
    }
    result: dict[str, float | None] = {}
    for name, raw in payloads.items():
        value = struct.unpack(">f", raw)[0]
        result[name] = value if math.isfinite(value) else None
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scanne en lecture seule les Holding Registers du CHY0444."
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--device-id", type=int, default=DEFAULT_DEVICE_ID)
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--end", type=int, default=5000)
    parser.add_argument("--block", type=int, default=100)
    parser.add_argument("--pause", type=float, default=0.20)
    parser.add_argument("--out", type=Path, default=Path("syclope_scans"))
    args = parser.parse_args()

    if not (1 <= args.block <= 125):
        raise SystemExit("--block doit être compris entre 1 et 125.")
    if args.start < 0 or args.end < args.start or args.end > 65535:
        raise SystemExit("Plage d'adresses invalide.")
    if not (1 <= args.device_id <= 247):
        raise SystemExit("--device-id doit être compris entre 1 et 247.")

    args.out.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = args.out / f"syclope_raw_{stamp}.csv"
    float_path = args.out / f"syclope_float_candidates_{stamp}.csv"
    zone_path = args.out / f"syclope_zones_{stamp}.csv"

    client = ModbusTcpClient(
        host=args.host,
        port=args.port,
        framer=FramerType.RTU,
        timeout=4,
        retries=0,
    )
    if not client.connect():
        raise SystemExit(f"Connexion impossible vers {args.host}:{args.port}")

    raw_rows: list[dict] = []
    float_rows: list[dict] = []
    zones: list[dict] = []

    try:
        for address in range(args.start, args.end + 1, args.block):
            count = min(args.block, args.end - address + 1)
            try:
                response = read_holding(client, address, count, args.device_id)
            except ModbusException as exc:
                print(f"{address:05d}-{address+count-1:05d}: {exc}")
                time.sleep(args.pause)
                continue

            if response.isError():
                print(f"{address:05d}-{address+count-1:05d}: erreur Modbus")
                time.sleep(args.pause)
                continue

            registers = list(response.registers)
            non_zero = sum(v != 0 for v in registers)
            print(
                f"{address:05d}-{address+len(registers)-1:05d}: "
                f"OK, {non_zero} valeur(s) non nulle(s)"
            )
            zones.append({
                "start_address": address,
                "end_address": address + len(registers) - 1,
                "register_count": len(registers),
                "non_zero_count": non_zero,
            })

            for offset, value in enumerate(registers):
                zero = address + offset
                raw_rows.append({
                    "address_zero_based": zero,
                    "plc_address": 40001 + zero,
                    "unsigned_16": value,
                    "signed_16": signed16(value),
                    "hex": f"0x{value:04X}",
                })

            for offset in range(len(registers) - 1):
                first, second = registers[offset], registers[offset + 1]
                for order, value in decode_float_variants(first, second).items():
                    if value is None:
                        continue
                    if -1000 <= value <= 10000 and abs(value) > 1e-8:
                        float_rows.append({
                            "start_address_zero_based": address + offset,
                            "plc_address": 40001 + address + offset,
                            "register_1": first,
                            "register_2": second,
                            "order": order,
                            "float_value": value,
                        })

            time.sleep(args.pause)
    finally:
        client.close()

    def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    write_csv(raw_path, raw_rows, [
        "address_zero_based", "plc_address", "unsigned_16", "signed_16", "hex"
    ])
    write_csv(float_path, float_rows, [
        "start_address_zero_based", "plc_address", "register_1",
        "register_2", "order", "float_value"
    ])
    write_csv(zone_path, zones, [
        "start_address", "end_address", "register_count", "non_zero_count"
    ])

    print("\nScan terminé :")
    print(raw_path)
    print(float_path)
    print(zone_path)


if __name__ == "__main__":
    main()
