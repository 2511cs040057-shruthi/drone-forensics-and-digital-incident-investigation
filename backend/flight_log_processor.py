import csv
import os
from datetime import datetime


def process_flight_log(file_path):
    """
    Read and validate a drone flight log.

    Expected file format:

        Drone: TestDrone
        Flight ID: TEST-001
        Timestamp,Latitude,Longitude,Altitude,Speed
        2026-10-09 10:00:00,17.3850,78.4867,50,10

    Returns the drone details and extracted flight records.
    """

    flight_data = {
        "drone": "",
        "flight_id": "",
        "records": []
    }

    if not os.path.isfile(file_path):
        raise FileNotFoundError("Flight-log file was not found.")

    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        lines = file.readlines()

    header_found = False

    for line_number, line in enumerate(lines, start=1):
        line = line.strip()

        if not line:
            continue

        if line.startswith("Drone:"):
            flight_data["drone"] = line.split(":", 1)[1].strip()
            continue

        if line.startswith("Flight ID:"):
            flight_data["flight_id"] = line.split(":", 1)[1].strip()
            continue

        if line.lower().startswith(
            "timestamp,latitude,longitude,altitude,speed"
        ):
            header_found = True
            break

    if not header_found:
        raise ValueError(
            "Flight-log header not found. Expected columns: "
            "Timestamp,Latitude,Longitude,Altitude,Speed"
        )

    header_index = next(
        index
        for index, line in enumerate(lines)
        if line.strip().lower().startswith(
            "timestamp,latitude,longitude,altitude,speed"
        )
    )

    data_lines = lines[header_index:]

    reader = csv.DictReader(data_lines)

    expected_columns = {
        "timestamp",
        "latitude",
        "longitude",
        "altitude",
        "speed"
    }

    if reader.fieldnames is None:
        raise ValueError("Flight-log column names could not be read.")

    normalized_headers = {
        name.strip().lower()
        for name in reader.fieldnames
        if name is not None
    }

    if not expected_columns.issubset(normalized_headers):
        raise ValueError(
            "Flight log must contain Timestamp, Latitude, Longitude, "
            "Altitude, and Speed columns."
        )

    for row_number, row in enumerate(reader, start=header_index + 2):
        try:
            normalized_row = {
                key.strip().lower(): (
                    value.strip() if value is not None else ""
                )
                for key, value in row.items()
                if key is not None
            }

            if not any(normalized_row.values()):
                continue

            timestamp = normalized_row.get("timestamp", "")
            latitude = float(normalized_row["latitude"])
            longitude = float(normalized_row["longitude"])

            altitude_text = normalized_row.get("altitude", "")
            speed_text = normalized_row.get("speed", "")

            altitude = (
                float(altitude_text)
                if altitude_text
                else None
            )

            speed = (
                float(speed_text)
                if speed_text
                else None
            )

            if not timestamp:
                raise ValueError("Timestamp is missing.")

            # Validate the timestamp while preserving its original value.
            datetime.fromisoformat(timestamp)

            if not -90 <= latitude <= 90:
                raise ValueError("Latitude is outside the valid range.")

            if not -180 <= longitude <= 180:
                raise ValueError("Longitude is outside the valid range.")

            if altitude is not None and altitude < 0:
                raise ValueError("Altitude cannot be negative.")

            if speed is not None and speed < 0:
                raise ValueError("Speed cannot be negative.")

            record = {
                "timestamp": timestamp,
                "latitude": latitude,
                "longitude": longitude,
                "altitude": altitude,
                "speed": speed
            }

            flight_data["records"].append(record)

        except (ValueError, TypeError, KeyError) as error:
            raise ValueError(
                f"Invalid flight-log data on line {row_number}: {error}"
            ) from error

    if not flight_data["records"]:
        raise ValueError("No valid flight records were found.")

    # Confirm that records are in chronological order.
    flight_data["records"].sort(
        key=lambda record: datetime.fromisoformat(record["timestamp"])
    )

    return flight_data