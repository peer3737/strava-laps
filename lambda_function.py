import logging
import os
from datetime import datetime, timedelta
from supporting.strava import Strava
from database.db import Connection
import json
import uuid
from supporting import aws


class CorrelationIdFilter(logging.Filter):
    def __init__(self):
        super().__init__()
        # Generate a new correlation ID
        self.correlation_id = str(uuid.uuid4())

    def filter(self, record):
        # Add correlation ID to the log record
        record.correlation_id = self.correlation_id
        return True


# Logging formatter that includes the correlation ID
formatter = logging.Formatter('[%(levelname)s] [%(asctime)s] [Correlation ID: %(correlation_id)s] %(message)s')

# Set up the root logger
log = logging.getLogger()
log.setLevel("INFO")
logging.getLogger("boto3").setLevel(logging.WARNING)
logging.getLogger("botocore").setLevel(logging.WARNING)

# Remove existing handlers
for handler in log.handlers:
    log.removeHandler(handler)

# Add a new handler with the custom formatter
handler = logging.StreamHandler()
handler.setFormatter(formatter)
log.addHandler(handler)

# Add the CorrelationIdFilter to the logger
correlation_filter = CorrelationIdFilter()
log.addFilter(correlation_filter)


def lambda_handler(event, context):
    body = event.get("body")
    log.info(body)
    parsed_body = json.loads(body)
    activity_id = parsed_body.get("activity_id")
    log.info(f"Start handling laps for activity {activity_id}")
    exit()
    database_id = os.getenv('DATABASE_ID')
    database_settings = aws.dynamodb_query(table='database_settings', id=database_id)
    db_host = database_settings[0]['host']
    db_user = database_settings[0]['user']
    db_password = database_settings[0]['password']
    db_port = database_settings[0]['port']
    db = Connection(user=db_user, password=db_password, host=db_host, port=db_port, charset="utf8mb4")
    strava = Strava(db)

    lap_keys = ['name', 'split', 'distance', 'moving_time', 'elapsed_time', 'start_index',
                        'total_elevation_gain', 'average_cadence', 'average_heartrate', 'max_heartrate', 'pace_zone']

    laps = strava.activity_laps(activity_id=activity_id)
    content = []
    for lap in laps:
        lap_content = {
            "activity_id": activity_id
        }
        for lap_key in lap_keys:
            if lap_key in lap:
                lap_content[lap_key] = lap[lap_key]
            else:
                lap_content[lap_key] = None
        content.append(lap_content)

    db = Connection(user=db_user, password=db_password, host=db_host, port=db_port, charset="utf8")

    if len(content) > 0:
        db.insert(table='activity_laps', json_data=content, mode='many')
    else:
        log.info(f"No laps detected for activity with ID={activity_id}")
