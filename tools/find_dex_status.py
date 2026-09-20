#!/usr/bin/env python3
"""Read-only lookup of an integer status code in an APK's DEX instructions.

Requires androguard. Reports method locations and matching instructions only;
does not modify APKs or dump application data.
"""
import argparse
import json
import zipfile

from androguard.core.dex import DEX
from loguru import logger


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("apk")
    parser.add_argument("--code", type=int, default=2289)
    args = parser.parse_args()
    logger.disable("androguard")
    matches = []
    dex_count = 0
    with zipfile.ZipFile(args.apk) as archive:
        for name in archive.namelist():
            if not name.endswith(".dex"):
                continue
            dex_count += 1
            dex = DEX(archive.read(name))
            for cls in dex.get_classes():
                for method in cls.get_methods():
                    for instruction in method.get_instructions():
                        if not instruction.get_name().startswith("const"):
                            continue
                        literals = getattr(instruction, "get_literals", lambda: [])()
                        if args.code in literals:
                            matches.append({"dex": name, "class": cls.get_name(),
                                            "method": method.get_name(),
                                            "descriptor": method.get_descriptor(),
                                            "instruction": instruction.get_output()})
    print(json.dumps({"code": args.code, "dex_files": dex_count, "matches": matches}, indent=2))


if __name__ == "__main__":
    main()
