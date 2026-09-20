#!/usr/bin/env bash
# Build an extracted source candidate offline; never installs a runtime binary.
set -euo pipefail
cast_output=$(cd "${1:?usage: bash build_exported_airplay.sh EXTRACTED_DIRECTORY}" && pwd -P)
if [[ $(uname -s) != Linux || $(uname -m) != x86_64 ]]; then
  echo "Only Linux x86_64 has been validated" >&2
  exit 2
fi
cd "$cast_output/openssl"
./Configure linux-x86_64 no-shared
make -j"${CAST_BUILD_JOBS:-4}" build_libs
cd "$cast_output/airplay/libraop/libcodecs/alac/codec"
make -j"${CAST_BUILD_JOBS:-4}" AR=ar
cd "$cast_output/airplay/libraop/libmdns/mdnssd"
make lib HOST=linux PLATFORM=x86_64 CC=gcc AR=ar -j"${CAST_BUILD_JOBS:-4}"
cd "$cast_output/airplay"
mkdir -p libraop/libopenssl/targets/linux/x86_64/include \
  libraop/libcodecs/targets/linux/x86_64 libraop/libmdns/targets/linux/x86_64
cp -a "$cast_output/openssl/include/openssl" libraop/libopenssl/targets/linux/x86_64/include/
cp "$cast_output/openssl/libcrypto.a" libraop/libopenssl/targets/linux/x86_64/libopenssl.a
cp libraop/libcodecs/alac/codec/obj/libalac.a libraop/libcodecs/targets/linux/x86_64/libcodecs.a
cp libraop/libmdns/mdnssd/lib/linux/x86_64/libmdnssd.a libraop/libmdns/targets/linux/x86_64/libmdns.a
make -j"${CAST_BUILD_JOBS:-4}" STATIC=1 HOST=linux PLATFORM=x86_64 CC=gcc CXX=g++ VERSION=0.5.4-source-candidate
make test STATIC=1 HOST=linux PLATFORM=x86_64 CC=gcc CXX=g++ VERSION=0.5.4-source-candidate
bin/cliairplay-linux-x86_64 --check
sha256sum bin/cliairplay-linux-x86_64
