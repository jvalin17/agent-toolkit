#!/bin/bash
# Deletes archived .md files older than 30 days
# Usage: ./scripts/cleanup-archive.sh [project-root]
# Defaults to current directory if no argument provided

PROJECT_ROOT="${1:-.}"
ARCHIVE_DIR="$PROJECT_ROOT/archive"
DAYS=30

if [ ! -d "$ARCHIVE_DIR" ]; then
  echo "No archive directory found at $ARCHIVE_DIR — nothing to clean."
  exit 0
fi

COUNT=$(find "$ARCHIVE_DIR" -name "*.md" -mtime +$DAYS | wc -l | tr -d ' ')

if [ "$COUNT" -eq 0 ]; then
  echo "No archive files older than $DAYS days."
  exit 0
fi

echo "Deleting $COUNT archive file(s) older than $DAYS days..."
find "$ARCHIVE_DIR" -name "*.md" -mtime +$DAYS -delete
find "$ARCHIVE_DIR" -type d -empty -delete
echo "Done."
