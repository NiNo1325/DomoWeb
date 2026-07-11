#!/usr/bin/env python3
"""Recherche de valeurs plausibles dans un CSV issu de scan_syclope.py."""

from __future__ import annotations

import argparse
import csv
import math
import struct
from pathlib import Path

TARGETS = {
    "pH mesure": 7.17,
    "Redox mesure": 882.0,
    "pH minimum de consigne": 6.50,
    "pH maximum de consigne": 7.60,
    "bande proportionnelle pH": 0.20,
    "Redox minimum de consigne": 650.0,
    "Redox maximum de consigne": 800.0,
    "bande proportionnelle Redox": 50.0,
    "temps maximal": 120.0,
}


def signed16(value: int) -> int:
    return value - 65536 if value >= 32768 else value


def decode_variants(a: int, b: int) -> dict[str, float]:
    wa, wb = a.to_bytes(2, "big"), b.to_bytes(2, "big")
    return {
        "Float ABCD": struct.unpack(">f", wa + wb)[0],
        "Float CDAB": struct.unpack(">f", wb + wa)[0],
        "Float BADC": struct.unpack(">f", wa[::-1] + wb[::-1])[0],
        "Float DCBA": struct.unpack(">f", wb[::-1] + wa[::-1])[0],
    }


def close(value: float, target: float) -> bool:
    tolerance = max(0.03, abs(target) * 0.002)
    return math.isfinite(value) and abs(value - target) <= tolerance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--plc-start", type=int, default=41200)
    parser.add_argument("--plc-end", type=int, default=42400)
    parser.add_argument("--out", type=Path, default=Path("syclope_candidates.csv"))
    args = parser.parse_args()

    registers: dict[int, int] = {}
    with args.csv_file.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            plc = int(row["plc_address"])
            if args.plc_start <= plc <= args.plc_end:
                registers[int(row["address_zero_based"])] = int(row["unsigned_16"])

    matches: list[dict] = []
    for zero, u16 in sorted(registers.items()):
        s16 = signed16(u16)
        scalar_values = {
            "UInt16": float(u16),
            "Int16": float(s16),
            "UInt16 / 10": u16 / 10,
            "Int16 / 10": s16 / 10,
            "UInt16 / 100": u16 / 100,
            "Int16 / 100": s16 / 100,
            "UInt16 / 1000": u16 / 1000,
            "Int16 / 1000": s16 / 1000,
        }
        for interpretation, value in scalar_values.items():
            for name, target in TARGETS.items():
                if close(value, target):
                    matches.append({
                        "target": name,
                        "target_value": target,
                        "plc_address": 40001 + zero,
                        "zero_based_address": zero,
                        "interpretation": interpretation,
                        "decoded_value": value,
                        "difference": abs(value - target),
                        "register_1": u16,
                        "register_2": "",
                    })

        if zero + 1 in registers:
            second = registers[zero + 1]
            for interpretation, value in decode_variants(u16, second).items():
                for name, target in TARGETS.items():
                    if close(value, target):
                        matches.append({
                            "target": name,
                            "target_value": target,
                            "plc_address": 40001 + zero,
                            "zero_based_address": zero,
                            "interpretation": interpretation,
                            "decoded_value": value,
                            "difference": abs(value - target),
                            "register_1": u16,
                            "register_2": second,
                        })

    matches.sort(key=lambda row: (row["target"], row["difference"], row["plc_address"]))
    fields = [
        "target", "target_value", "plc_address", "zero_based_address",
        "interpretation", "decoded_value", "difference", "register_1", "register_2"
    ]
    with args.out.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(matches)

    for row in matches:
        print(
            f"{row['target']:<32} PLC {row['plc_address']} "
            f"{row['interpretation']:<14} {row['decoded_value']}"
        )
    print(f"\nRésultats : {args.out.resolve()}")


if __name__ == "__main__":
    main()
