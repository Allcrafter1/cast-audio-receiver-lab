#!/usr/bin/env bash
# Developer-only Linux x86_64 provenance build. Does not install into runtime.
# Inputs: complete pinned recursive airplay-cli checkout, NEW output directory.
set -euo pipefail
if [[ $# != 2 ]]; then
  echo "usage: bash tools/build_airplay_source_candidate.sh CHECKOUT NEW_DIRECTORY" >&2
  exit 2
fi
cast_source=$(cd "$1" && pwd -P)
cast_output=$(realpath -m "$2")
cast_tools=$(cd "$(dirname "$0")" && pwd -P)
if [[ -e "$cast_output" ]]; then
  echo "Refusing to overlay an existing build directory" >&2
  exit 2
fi
if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
  echo "Only Linux x86_64 has been validated for this recipe" >&2
  exit 2
fi
python3 "$cast_tools/check_airplay_source_evidence.py" "$cast_source"

# Export immutable Git objects, never an edited worktree or generated objects.
export_source() {
  local component=$1 revision=$2 destination=$3
  git -C "$cast_source/$component" cat-file -e "$revision^{commit}"
  mkdir -p "$destination"
  git -C "$cast_source/$component" archive "$revision" | tar -x -C "$destination"
}
mkdir -p "$cast_output"
export_source . 431c5c582eef9307c4e39c50a0ea65e970bc1128 "$cast_output/airplay"
export_source libraop 81c2182649da8645ac2a58b78e9f370c79a4165b "$cast_output/airplay/libraop"
export_source libraop/crosstools 41544c653760a205cbf6cebfdeda4a9394cc6455 "$cast_output/airplay/libraop/crosstools"
export_source libraop/dmap-parser 2f8ee61e2427a177beea919d72dde8931084fe51 "$cast_output/airplay/libraop/dmap-parser"
export_source libraop/libcodecs 3234c96680fbe9f45047936a14df10edca822e5e "$cast_output/airplay/libraop/libcodecs"
export_source libraop/libcodecs/alac 30e526563714325ff384968e116060c4ed606f06 "$cast_output/airplay/libraop/libcodecs/alac"
export_source libraop/libmdns d7f58bf2791c3c25fd729d739a9267ce9db5b696 "$cast_output/airplay/libraop/libmdns"
export_source libraop/libmdns/mdnssd 16402f3293b8bf09b8274ba7188202953d8e4f40 "$cast_output/airplay/libraop/libmdns/mdnssd"
export_source libraop/libopenssl/openssl c1eeb9406b6142148f267594197d853403d10208 "$cast_output/openssl"

cd "$cast_output/openssl"
./Configure linux-x86_64 no-shared
make -j"${CAST_BUILD_JOBS:-4}" build_libs
cd "$cast_output/airplay/libraop/libcodecs/alac/codec"
make -j"${CAST_BUILD_JOBS:-4}" AR=ar
cd "$cast_output/airplay/libraop/libmdns/mdnssd"
make lib HOST=linux PLATFORM=x86_64 CC=gcc AR=ar -j"${CAST_BUILD_JOBS:-4}"
cd "$cast_output/airplay"

# The linker uses only ALAC, mdnssd and libcrypto from these archives. Rebuild
# those from source; do not reuse upstream's precompiled archive contents.
mkdir -p libraop/libopenssl/targets/linux/x86_64/include
cp -a "$cast_output/openssl/include/openssl" libraop/libopenssl/targets/linux/x86_64/include/
cp "$cast_output/openssl/libcrypto.a" libraop/libopenssl/targets/linux/x86_64/libopenssl.a
cp libraop/libcodecs/alac/codec/obj/libalac.a libraop/libcodecs/targets/linux/x86_64/libcodecs.a
cp libraop/libmdns/mdnssd/lib/linux/x86_64/libmdnssd.a libraop/libmdns/targets/linux/x86_64/libmdns.a
make -j"${CAST_BUILD_JOBS:-4}" STATIC=1 HOST=linux PLATFORM=x86_64 CC=gcc CXX=g++ VERSION=0.5.4-source-candidate
make test STATIC=1 HOST=linux PLATFORM=x86_64 CC=gcc CXX=g++ VERSION=0.5.4-source-candidate
bin/cliairplay-linux-x86_64 --check
sha256sum bin/cliairplay-linux-x86_64
