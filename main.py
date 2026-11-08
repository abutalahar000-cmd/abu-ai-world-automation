import os
from datetime import datetime, timezone

def main():
    print("Abu AI World Automation Started!")
    print("Time:", datetime.now(timezone.utc).isoformat())

    youtube_ready = bool(os.getenv("YOUTUBE_CLIENT_ID"))
    print("YouTube credentials configured:", youtube_ready)

    print("System check completed.")
    print("Publishing is disabled until setup is verified.")

if __name__ == "__main__":
    main()
