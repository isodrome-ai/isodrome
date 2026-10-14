#!/usr/bin/env bash
# Copies the public API definition from isodrome-server and regenerates the Python client.
#
#   scripts/sync_proto.sh            # copy from $ISODROME_SERVER (default ../isodrome-server), regenerate
#   scripts/sync_proto.sh --check    # fail if the copy or the generated code is out of date
#
# Needs grpcio-tools (pip install -e '.[dev]').
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
server="${ISODROME_SERVER:-$root/../isodrome-server}"
proto="isodrome/v1/isodrome.proto"
check=false
[[ "${1:-}" == "--check" ]] && check=true

if [[ ! -f "$server/proto/$proto" ]]; then
  echo "error: $server/proto/$proto not found; set ISODROME_SERVER to an isodrome-server checkout" >&2
  exit 1
fi

out="$(mktemp -d)"
trap 'rm -rf "$out"' EXIT
mkdir -p "$out/proto/isodrome/v1" "$out/src"
cp "$server/proto/$proto" "$out/proto/$proto"
python -m grpc_tools.protoc -I"$out/proto" \
  --python_out="$out/src" --pyi_out="$out/src" --grpc_python_out="$out/src" \
  "$out/proto/$proto"

generated=(isodrome_pb2.py isodrome_pb2.pyi isodrome_pb2_grpc.py)
if $check; then
  status=0
  diff -u "$root/proto/$proto" "$out/proto/$proto" || { echo "proto/$proto differs from the server's" >&2; status=1; }
  for f in "${generated[@]}"; do
    diff -q "$root/src/isodrome/v1/$f" "$out/src/isodrome/v1/$f" >/dev/null \
      || { echo "src/isodrome/v1/$f is out of date" >&2; status=1; }
  done
  [[ $status == 0 ]] && echo "proto and generated client are up to date" \
    || echo "run scripts/sync_proto.sh to update" >&2
  exit $status
fi

mkdir -p "$root/proto/isodrome/v1"
cp "$out/proto/$proto" "$root/proto/$proto"
for f in "${generated[@]}"; do cp "$out/src/isodrome/v1/$f" "$root/src/isodrome/v1/$f"; done
echo "synced $proto from $server ($(git -C "$server" rev-parse --short HEAD 2>/dev/null || echo unknown))"
