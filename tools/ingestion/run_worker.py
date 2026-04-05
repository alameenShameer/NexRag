import argparse
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ingestion import get_ingestion_service


def main():
    parser = argparse.ArgumentParser(description="Run the NexRag official-source ingestion worker.")
    parser.add_argument("--force", action="store_true", help="Refetch and rebuild even if sources appear unchanged.")
    parser.add_argument("--interval-minutes", type=int, default=0, help="Run continuously on the given interval.")
    args = parser.parse_args()

    service = get_ingestion_service()

    if args.interval_minutes <= 0:
        result = service.run_once(force=args.force)
        print(result)
        return

    print(f"Starting NexRag ingestion worker loop (interval={args.interval_minutes} minutes, force={args.force})")
    while True:
        result = service.run_once(force=args.force)
        print(result)
        time.sleep(max(args.interval_minutes, 1) * 60)


if __name__ == "__main__":
    main()
