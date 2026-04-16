#!/usr/bin/env bash
# Downloads sample public GitHub repositories as zip archives for upload testing.
# Run from the project root: bash test_files/fetch_samples.sh

set -e

OUTDIR="$(dirname "$0")"

echo "Downloading sample code archives into $OUTDIR ..."

# Small Python project — good for basic function analysis
curl -L "https://github.com/psf/requests/archive/refs/heads/main.zip" \
  -o "$OUTDIR/sample_requests.zip"
echo "Downloaded sample_requests.zip"

# Tiny repo — fast upload, minimal analysis time
curl -L "https://github.com/pallets/click/archive/refs/heads/main.zip" \
  -o "$OUTDIR/sample_click.zip"
echo "Downloaded sample_click.zip"

# Another small utility library
curl -L "https://github.com/tqdm/tqdm/archive/refs/heads/master.zip" \
  -o "$OUTDIR/sample_tqdm.zip"
echo "Downloaded sample_tqdm.zip"

echo ""
echo "Done. Files in $OUTDIR:"
ls -lh "$OUTDIR"/*.zip
