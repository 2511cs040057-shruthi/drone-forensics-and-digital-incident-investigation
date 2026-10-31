from backend.flight_log_processor import process_flight_log
from backend.flight_log_processor import save_flight_records

file_path = "sample_flight_log.txt"

flight_data = process_flight_log(file_path)

save_flight_records(2, flight_data)

print("Flight records saved successfully")
print("Records saved:", len(flight_data["records"]))