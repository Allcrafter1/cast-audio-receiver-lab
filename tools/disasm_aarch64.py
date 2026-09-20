#!/usr/bin/env python3
"""Disassemble an address range from an AArch64 ELF image."""

from __future__ import annotations

import argparse

from capstone import CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, Cs
from elftools.elf.elffile import ELFFile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf")
    parser.add_argument("start", type=lambda value: int(value, 0))
    parser.add_argument("end", type=lambda value: int(value, 0))
    args = parser.parse_args()

    with open(args.elf, "rb") as stream:
        elf = ELFFile(stream)
        text = elf.get_section_by_name(".text")
        if text is None:
            raise SystemExit("ELF has no .text section")
        text_address = text["sh_addr"]
        offset = args.start - text_address
        data = text.data()[offset : offset + args.end - args.start]

    disassembler = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    for instruction in disassembler.disasm(data, args.start):
        print(
            f"0x{instruction.address:08x}: "
            f"{instruction.mnemonic:8} {instruction.op_str}"
        )


if __name__ == "__main__":
    main()
