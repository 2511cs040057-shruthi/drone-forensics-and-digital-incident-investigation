from pymavlink import mavutil
from pathlib import Path
from datetime import datetime, timezone
from contextlib import ExitStack
from collections import Counter
import hashlib
import csv
import json
import math

# 1. PATH OF YOUR EXPORTED PIXHAWK BIN FILE
BIN_FILE = Path(
    r"C:\Users\rango\OneDrive\Desktop\sample log data\00000146.BIN"
)

# 3. SHA-256 HASH CALCULATION
def sha256_file(path):
    hash_obj = hashlib.sha256()

    with open(path, "rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            hash_obj.update(chunk)

    return hash_obj.hexdigest()


# 4. MAKE VALUES SAFE FOR JSON AND CSV
def clean_value(value):
    if isinstance(value, bytes):
        return value.hex()

    if isinstance(value, (list, tuple)):
        return [clean_value(v) for v in value]

    if isinstance(value, dict):
        return {str(k): clean_value(v) for k, v in value.items()}

    if isinstance(value, float) and not math.isfinite(value):
        return str(value)

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    return str(value)


# 5. EXTRACT FLIGHT LOGS
def extract_logs(bin_file=BIN_FILE, output_dir=None):

    bin_file = Path(bin_file)
    run_time = datetime.now(timezone.utc)
    if output_dir is None:
        output_dir = (
            bin_file.parent / "output" /
            f"{bin_file.stem}_{run_time.strftime('%Y%m%d_%H%M%S_%f')}"
        )
    output_dir = Path(output_dir)

    if not bin_file.is_file():
        print("ERROR: BIN file not found!")
        print(bin_file)
        raise FileNotFoundError(bin_file)

    output_dir.mkdir(parents=True, exist_ok=True)

    print("Starting Drone Forensic Extraction...")
    print("Source:", bin_file)

    original_hash = sha256_file(bin_file)
    print("Original SHA-256:", original_hash)

    # Read ArduPilot DataFlash BIN file
    log = mavutil.mavlink_connection(str(bin_file))

    counts = Counter()
    csv_writers = {}

    with ExitStack() as stack:
        # Close the DataFlash reader before temporary upload files are removed.
        stack.callback(log.close)

        txt_file = stack.enter_context(
            open(output_dir / "all_flight_logs.txt",
                 "w", encoding="utf-8")
        )

        json_file = stack.enter_context(
            open(output_dir / "all_flight_logs.jsonl",
                 "w", encoding="utf-8")
        )

        while True:
            msg = log.recv_match()

            if msg is None:
                break

            msg_type = msg.get_type()

            record = {
                key: clean_value(value)
                for key, value in msg.to_dict().items()
            }

            counts[msg_type] += 1

            # Save readable TXT data
            fields = ", ".join(
                f"{key}={value}"
                for key, value in record.items()
                if key != "mavpackettype"
            )

            txt_file.write(f"{msg_type}: {fields}\n")

            # Save JSON Lines data for Flask
            json_file.write(
                json.dumps(record, ensure_ascii=False) + "\n"
            )

            # Automatically create one CSV for each log type
            if msg_type not in csv_writers:

                csv_path = output_dir / f"{msg_type}.csv"

                csv_file = stack.enter_context(
                    open(csv_path, "w",
                         newline="", encoding="utf-8-sig")
                )

                writer = csv.DictWriter(
                    csv_file,
                    fieldnames=list(record.keys()),
                    extrasaction="ignore"
                )

                writer.writeheader()
                csv_writers[msg_type] = writer

            csv_writers[msg_type].writerow(record)

    # 6. CREATE FORENSIC SUMMARY
    derived_hashes = {
        path.name: sha256_file(path)
        for path in output_dir.iterdir()
        if path.is_file()
    }

    summary = {
        "source_file": bin_file.name,
        "source_sha256": original_hash,
        "extraction_utc": run_time.isoformat(),
        "total_records": sum(counts.values()),
        "records_by_type": dict(sorted(counts.items())),
        "derived_file_sha256": derived_hashes
    }

    with open(output_dir / "forensic_summary.json",
              "w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    # 7. DISPLAY RESULTS
    print("\nEXTRACTION COMPLETED")
    print("-------------------------")

    for name, count in sorted(counts.items()):
        print(f"{name}: {count} records")

    print("-------------------------")
    print("Total records:", sum(counts.values()))
    print("Output folder:", output_dir)
    print("Original BIN file was not modified.")
    return {
        "summary": summary,
        "output_dir": output_dir,
    }


if __name__ == "__main__":
    extract_logs()
