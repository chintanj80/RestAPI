import requests
import time
import logging
import smtplib
from email.message import EmailMessage
from prometheus_client import Gauge, start_http_server
from datetime import datetime, timedelta

# --- Configuration ---

# List of APIs to monitor
API_CONFIG = [
    {"name": "API Service A", "url": "http://localhost:8080/health", "expected_status": 200},
    {"name": "API Service B", "url": "https://api.github.com/health", "expected_status": 200},
    {"name": "Failing API C", "url": "http://nonexistent-api-url-12345.com/health", "expected_status": 200},
]

# Email Configuration
SMTP_SERVER = "smtp.example.com"  # e.g., 'smtp.gmail.com'
SMTP_PORT = 587                    # e.g., 587 for TLS
SMTP_USERNAME = "your_email@example.com"
SMTP_PASSWORD = "your_email_password" # Use an App Password for services like Gmail
ALERT_RECIPIENTS = ["devops-team@example.com"]
SENDER_EMAIL = SMTP_USERNAME
HOURLY_ALERT_INTERVAL = timedelta(hours=1)
CHECK_INTERVAL_SECONDS = 60
PROMETHEUS_PORT = 8000

# --- Setup ---

# 1. Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 2. Prometheus Metrics Setup
# Gauge for the overall status (1=UP, 0=DOWN)
API_STATUS = Gauge(
    'api_health_status',
    'Health status of monitored APIs (1=UP, 0=DOWN)',
    ['api_name', 'url']
)

# 3. State Management
# Dictionary to store the current operational state and the last alert time
api_states = {
    api['name']: {
        'is_down': False,
        'last_alert_time': None
    }
    for api in API_CONFIG
}

# --- Core Functions ---

def send_email_alert(api_name, status, details):
    """Sends an email notification."""
    try:
        msg = EmailMessage()
        
        if status == "FAILURE":
            subject = f"🚨 ALERT: {api_name} is DOWN!"
            body = f"""
            The health check for {api_name} has FAILED.
            
            Details:
            URL: {details.get('url')}
            Error: {details.get('error')}
            Status Code: {details.get('status_code', 'N/A')}
            
            Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
        elif status == "RECOVERY":
            subject = f"✅ RECOVERY: {api_name} is UP!"
            body = f"""
            The health check for {api_name} has RECOVERED.
            
            Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            """
        else:
            return # Should not happen

        msg['Subject'] = subject
        msg['From'] = SENDER_EMAIL
        msg['To'] = ", ".join(ALERT_RECIPIENTS)
        msg.set_content(body)

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(msg)
        
        logger.warning(f"EMAIL SENT: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email for {api_name}: {e}")
        return False

def check_api_health(api):
    """Performs the HTTP check and updates state and metrics."""
    api_name = api['name']
    url = api['url']
    expected_status = api['expected_status']
    state = api_states[api_name]
    
    logger.info(f"Checking {api_name} at {url}")

    try:
        response = requests.get(url, timeout=10)
        status_code = response.status_code
        
        # Check for success
        if status_code == expected_status:
            logger.info(f"SUCCESS: {api_name} is UP ({status_code}).")
            API_STATUS.labels(api_name, url).set(1) # Prometheus UP
            
            # Recovery logic: If it was previously down, send a recovery alert
            if state['is_down']:
                logger.info(f"RECOVERY detected for {api_name}. Sending recovery alert.")
                send_email_alert(api_name, "RECOVERY", {})
                state['is_down'] = False
                state['last_alert_time'] = None
        else:
            # Check for failure (bad status code)
            logger.error(f"FAILURE: {api_name} returned unexpected status code {status_code}.")
            API_STATUS.labels(api_name, url).set(0) # Prometheus DOWN
            handle_failure(api_name, url, f"Bad status code: {status_code}", status_code)

    except requests.exceptions.RequestException as e:
        # Check for failure (connection error, timeout, etc.)
        logger.error(f"FAILURE: {api_name} is DOWN (Connection Error: {e}).")
        API_STATUS.labels(api_name, url).set(0) # Prometheus DOWN
        handle_failure(api_name, url, f"Connection/Timeout Error: {e}", "N/A")

def handle_failure(api_name, url, error_message, status_code):
    """Manages the failure state and alert throttling."""
    state = api_states[api_name]
    current_time = datetime.now()
    
    # 1. Log and Update State
    if not state['is_down']:
        # This is the FIRST time it has failed
        logger.warning(f"First failure for {api_name}. Sending immediate alert.")
        state['is_down'] = True
        
        details = {
            'url': url,
            'error': error_message,
            'status_code': status_code
        }
        if send_email_alert(api_name, "FAILURE", details):
            state['last_alert_time'] = current_time
    else:
        # It's an ongoing failure. Check for hourly re-alert.
        time_since_last_alert = current_time - state['last_alert_time']
        
        if time_since_last_alert >= HOURLY_ALERT_INTERVAL:
            logger.warning(f"API {api_name} is still down. Re-alerting (Interval: {time_since_last_alert}).")
            details = {
                'url': url,
                'error': error_message,
                'status_code': status_code
            }
            if send_email_alert(api_name, "FAILURE", details):
                state['last_alert_time'] = current_time
        else:
            # Throttled - do nothing but log the failure
            logger.warning(f"API {api_name} is still DOWN. Alert throttled.")

def main():
    """Main execution loop."""
    logger.info(f"Starting API Health Checker.")
    logger.info(f"Prometheus metrics exposed on port {PROMETHEUS_PORT}/metrics")
    
    # Start Prometheus metrics server
    start_http_server(PROMETHEUS_PORT)

    try:
        while True:
            for api in API_CONFIG:
                check_api_health(api)
            
            logger.info(f"Finished check cycle. Sleeping for {CHECK_INTERVAL_SECONDS} seconds...")
            time.sleep(CHECK_INTERVAL_SECONDS)
            
    except KeyboardInterrupt:
        logger.info("Service stopped by user.")
    except Exception as e:
        logger.critical(f"An unhandled error occurred: {e}")

if __name__ == "__main__":
    # NOTE: Remember to configure your SMTP settings before running!
    # For testing, you can comment out the send_email_alert logic.
    main()
