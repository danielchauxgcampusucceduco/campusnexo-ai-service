"""Operational limits shared by validation, runtime behavior and API discovery."""

MAX_OCCUPANCY_BATCH_ITEMS = 250
MAX_ASSIGNMENT_COURSES = 18
MAX_ASSIGNMENT_ROOMS = 1_000
MAX_ASSIGNMENT_ATTENDANCE = 1_000
MAX_ROOM_CAPACITY = 1_000
MAX_ROOM_POWER_KW = 1_000
MAX_VISION_IMAGE_BYTES = 8 * 1024 * 1024
# The backend sends at most a day of readings of the whole campus per sensor-health request.
MAX_ANOMALY_READINGS = 20_000
# A month of one room at one stored change per minute.
MAX_FORECAST_HISTORY = 50_000
MAX_FORECAST_HOURS = 48
