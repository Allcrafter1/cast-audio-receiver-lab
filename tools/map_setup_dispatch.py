#!/usr/bin/env python3
"""Map /setup path comparisons to their branch targets in an AArch64 ELF."""

from __future__ import annotations

import argparse

from capstone import CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN, Cs
from capstone.arm64 import ARM64_OP_IMM, ARM64_OP_REG
from elftools.elf.elffile import ELFFile


def c_string(image: bytes, address: int) -> str | None:
    if address < 0 or address >= len(image):
        return None
    end = image.find(b"\0", address, min(len(image), address + 256))
    if end < 0:
        return None
    try:
        return image[address:end].decode("ascii")
    except UnicodeDecodeError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("elf")
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

    decoder = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
    decoder.detail = True
    instructions = list(decoder.disasm(text_data, text_address))
    pages: dict[int, tuple[int, int]] = {}
    candidates: list[tuple[int, str]] = []

    for index, instruction in enumerate(instructions):
        operands = instruction.operands
        if instruction.mnemonic == "adrp" and len(operands) == 2:
            if operands[0].type == ARM64_OP_REG and operands[1].type == ARM64_OP_IMM:
                pages[operands[0].reg] = (operands[1].imm, index)
            continue
        if instruction.mnemonic != "add" or len(operands) < 3:
            continue
        destination, source, immediate = operands[:3]
        if (
            destination.type != ARM64_OP_REG
            or source.type != ARM64_OP_REG
            or immediate.type != ARM64_OP_IMM
            or source.reg not in pages
        ):
            continue
        page, page_index = pages[source.reg]
        if index - page_index > 24:
            continue
        value = c_string(image, page + immediate.imm)
        if value is not None and value.startswith("/setup/"):
            candidates.append((index, value))

    for index, path in candidates:
        branch = next(
            (
                current
                for current in instructions[index + 1 : index + 8]
                if current.mnemonic in {"cbz", "cbnz"}
                and current.operands[-1].type == ARM64_OP_IMM
            ),
            None,
        )
        if branch is not None:
            print(
                f"{path:<48} compare=0x{instructions[index].address:x} "
                f"handler=0x{branch.operands[-1].imm:x}"
            )


if __name__ == "__main__":
    main()
