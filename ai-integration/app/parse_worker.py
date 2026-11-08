"""Short-lived parser process. Raw input is never written to disk or logs."""

import json
import logging
import sys


def main():
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CPU, (4, 4))
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
    except ImportError:
        pass  # Windows still has the parent-enforced wall-clock timeout and input size limit.
    logging.disable(logging.CRITICAL)
    from app.privacy import document_pages

    try:
        pages = document_pages(sys.stdin.buffer.read(2 * 1024 * 1024 + 1), sys.argv[1])
        sys.stdout.write(json.dumps({"pages": pages}))
    except Exception:
        sys.stdout.write(json.dumps({"error": "Unreadable or oversized document"}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
