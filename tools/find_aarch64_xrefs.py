#!/usr/bin/env python3
"""Find simple ADRP+ADD references to strings in an AArch64 ELF image."""

from __future__ import annotations

import argparse
from collections import deque

from capstone import CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, Cs
from capstone.arm64 import ARM64_OP_IMM, ARM64_OP_REG
from elftools.elf.elffile import ELFFile


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf")
    parser.add_argument("needle", nargs="+")
    parser.add_argument("--context", type=int, default=10)
    args = parser.parse_args()

    with open(args.elf, "rb") as stream:
        image = stream.read()
        stream.seek(0)
        elf = ELFFile(stream)
        text = elf.get_section_by_name(".text")
        if text is None:
            raise SystemExit("ELF has no .text section")
        text_data = text.data()
        text_address = text["sh_addr"]

    targets: dict[int, str] = {}
    for needle in args.needle:
        encoded = needle.encode()
        start = 0
        while (offset := image.find(encoded, start)) >= 0:
            targets[offset] = needle
            start = offset + 1
    if not targets:
        raise SystemExit("no target strings found")

    disassembler = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    disassembler.detail = True
    instructions = list(disassembler.disasm(text_data, text_address))
    history: deque = deque(maxlen=args.context)
    pages: dict[int, tuple[int, int]] = {}

    for index, instruction in enumerate(instructions):
        operands = instruction.operands
        if instruction.mnemonic == "adrp" and len(operands) == 2:
            if operands[0].type == ARM64_OP_REG and operands[1].type == ARM64_OP_IMM:
                pages[operands[0].reg] = (operands[1].imm, index)
        elif instruction.mnemonic == "add" and len(operands) >= 3:
            destination, source, immediate = operands[:3]
            if (
                destination.type == ARM64_OP_REG
                and source.type == ARM64_OP_REG
                and immediate.type == ARM64_OP_IMM
                and source.reg in pages
            ):
                page, page_index = pages[source.reg]
                target = page + immediate.imm
                if target in targets and index - page_index <= 24:
                    low = max(0, index - args.context)
                    high = min(len(instructions), index + args.context + 1)
                    print(
                        f"\nreference to {targets[target]!r} at 0x{target:x}; "
                        f"code 0x{instruction.address:x}"
                    )
                    for current in instructions[low:high]:
                        marker = ">" if current.address == instruction.address else " "
                        print(
                            f"{marker} 0x{current.address:08x}: "
                            f"{current.mnemonic:8} {current.op_str}"
                        )
        history.append(instruction)


if __name__ == "__main__":
    main()
