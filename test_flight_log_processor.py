from backend.flight_log_processor import process_flight_log

file_path = "sample_flight_log.txt"

result = process_flight_log(file_path)

print("Flight Log Processing Result:")
print(result)