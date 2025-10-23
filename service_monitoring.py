import requests
import time
import smtplib
import logging
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from prometheus_client import start_http_server, Gauge, Counter, Histogram

# Configuration
ENDPOINTS = [
    {
        "name": "Main API",
        "url": "https://api.example.com/health",
        "check_interval": 60  # Optional: override default interval
    },
    {
        "name": "Auth Service",
        "url": "https://auth.example.com/health",
    },
    {
        "name": "Payment API",
        "url": "https://payments.example.com/health",
    }
]

DEFAULT_CHECK_INTERVAL = 60  # seconds
NOTIFICATION_INTERVAL = 3600  # 1 hour in seconds
PROMETHEUS_PORT = 8000  # Port for Prometheus metrics endpoint

# Email configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "your-email@gmail.com"
SENDER_PASSWORD = "your-app-password"
RECIPIENT_EMAIL = "alert-recipient@example.com"

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(endpoint)s] - %(message)s',
    handlers=[
        logging.FileHandler('api_health_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Prometheus metrics
api_health_status = Gauge('api_health_status', 'API health status (1=up, 0=down)', ['endpoint_name', 'endpoint_url'])
api_response_time = Histogram('api_response_time_seconds', 'API response time in seconds', ['endpoint_name', 'endpoint_url'])
api_check_total = Counter('api_check_total', 'Total number of API health checks', ['endpoint_name', 'endpoint_url', 'status'])
api_notification_total = Counter('api_notification_total', 'Total notifications sent', ['endpoint_name', 'endpoint_url', 'type'])
api_last_check_timestamp = Gauge('api_last_check_timestamp', 'Timestamp of last health check', ['endpoint_name', 'endpoint_url'])
api_http_status_code = Gauge('api_http_status_code', 'Last HTTP status code received', ['endpoint_name', 'endpoint_url'])

# State tracking per endpoint
endpoint_states = {}

class EndpointMonitor:
    """Monitor a single endpoint"""
    
    def __init__(self, endpoint_config):
        self.name = endpoint_config['name']
        self.url = endpoint_config['url']
        self.check_interval = endpoint_config.get('check_interval', DEFAULT_CHECK_INTERVAL)
        self.last_notification_time = None
        self.is_down = False
        
    def send_email_notification(self, subject, body):
        """Send email notification"""
        try:
            msg = MIMEMultipart()
            msg['From'] = SENDER_EMAIL
            msg['To'] = RECIPIENT_EMAIL
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            text = msg.as_string()
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, text)
            server.quit()
            
            self._log("Email notification sent successfully")
            api_notification_total.labels(endpoint_name=self.name, endpoint_url=self.url, type='email').inc()
            return True
        except Exception as e:
            self._log(f"Failed to send email: {str(e)}", level='error')
            api_notification_total.labels(endpoint_name=self.name, endpoint_url=self.url, type='email_failed').inc()
            return False
    
    def check_health(self):
        """Check endpoint health"""
        start_time = time.time()
        try:
            response = requests.get(self.url, timeout=10)
            response_time = time.time() - start_time
            
            # Record response time
            api_response_time.labels(endpoint_name=self.name, endpoint_url=self.url).observe(response_time)
            
            # Consider 2xx status codes as success
            if 200 <= response.status_code < 300:
                api_check_total.labels(endpoint_name=self.name, endpoint_url=self.url, status='success').inc()
                api_http_status_code.labels(endpoint_name=self.name, endpoint_url=self.url).set(response.status_code)
                return True, response.status_code, None
            else:
                api_check_total.labels(endpoint_name=self.name, endpoint_url=self.url, status='failure').inc()
                api_http_status_code.labels(endpoint_name=self.name, endpoint_url=self.url).set(response.status_code)
                return False, response.status_code, f"HTTP {response.status_code}"
        except requests.exceptions.Timeout:
            response_time = time.time() - start_time
            api_response_time.labels(endpoint_name=self.name, endpoint_url=self.url).observe(response_time)
            api_check_total.labels(endpoint_name=self.name, endpoint_url=self.url, status='timeout').inc()
            return False, None, "Request timeout"
        except requests.exceptions.ConnectionError:
            api_check_total.labels(endpoint_name=self.name, endpoint_url=self.url, status='connection_error').inc()
            return False, None, "Connection error - API is down"
        except Exception as e:
            api_check_total.labels(endpoint_name=self.name, endpoint_url=self.url, status='error').inc()
            return False, None, f"Error: {str(e)}"
    
    def should_send_notification(self):
        """Determine if we should send a notification based on timing"""
        if self.last_notification_time is None:
            return True
        
        time_since_last = datetime.now() - self.last_notification_time
        return time_since_last >= timedelta(seconds=NOTIFICATION_INTERVAL)
    
    def _log(self, message, level='info'):
        """Log with endpoint context"""
        extra = {'endpoint': self.name}
        if level == 'info':
            logger.info(message, extra=extra)
        elif level == 'error':
            logger.error(message, extra=extra)
        elif level == 'warning':
            logger.warning(message, extra=extra)
        elif level == 'debug':
            logger.debug(message, extra=extra)
    
    def monitor(self):
        """Main monitoring loop for this endpoint"""
        self._log(f"Starting monitoring for: {self.url}")
        self._log(f"Check interval: {self.check_interval} seconds")
        
        while True:
            try:
                is_healthy, status_code, error_msg = self.check_health()
                
                # Update last check timestamp
                api_last_check_timestamp.labels(endpoint_name=self.name, endpoint_url=self.url).set(time.time())
                
                if is_healthy:
                    self._log(f"Healthy (Status: {status_code})")
                    api_health_status.labels(endpoint_name=self.name, endpoint_url=self.url).set(1)
                    
                    # If API recovered, send recovery notification
                    if self.is_down:
                        subject = f"API Recovery: {self.name}"
                        body = f"The API '{self.name}' has recovered and is now healthy.\n\n"
                        body += f"URL: {self.url}\n"
                        body += f"Status Code: {status_code}\n"
                        body += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        self.send_email_notification(subject, body)
                        self.last_notification_time = None
                        self._log("Recovered - recovery notification sent")
                        api_notification_total.labels(endpoint_name=self.name, endpoint_url=self.url, type='recovery').inc()
                        
                    self.is_down = False
                    
                else:
                    error_info = error_msg if error_msg else f"Status {status_code}"
                    self._log(f"Check failed: {error_info}", level='error')
                    api_health_status.labels(endpoint_name=self.name, endpoint_url=self.url).set(0)
                    
                    # Send notification if it's the first failure or enough time has passed
                    if self.should_send_notification():
                        subject = f"API Alert: {self.name} is DOWN"
                        body = f"The API health check has failed for '{self.name}'.\n\n"
                        body += f"URL: {self.url}\n"
                        body += f"Error: {error_info}\n"
                        body += f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        
                        if self.last_notification_time:
                            body += f"\nThis is a recurring alert. Previous alert sent at: {self.last_notification_time.strftime('%Y-%m-%d %H:%M:%S')}"
                            self._log("Sending hourly recurring failure notification", level='warning')
                            notification_type = 'failure_recurring'
                        else:
                            self._log("Sending initial failure notification", level='warning')
                            notification_type = 'failure_initial'
                        
                        if self.send_email_notification(subject, body):
                            self.last_notification_time = datetime.now()
                            api_notification_total.labels(endpoint_name=self.name, endpoint_url=self.url, type=notification_type).inc()
                    else:
                        self._log("Skipping notification - not yet time for hourly update", level='debug')
                    
                    self.is_down = True
                
                time.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self._log("Monitoring stopped by user")
                break
            except Exception as e:
                self._log(f"Unexpected error in monitoring loop: {str(e)}", level='error')
                time.sleep(self.check_interval)

def start_monitoring():
    """Start monitoring all endpoints"""
    # Start Prometheus metrics server
    start_http_server(PROMETHEUS_PORT)
    logger.info(f"Prometheus metrics server started on port {PROMETHEUS_PORT}", extra={'endpoint': 'SYSTEM'})
    logger.info(f"Metrics available at http://localhost:{PROMETHEUS_PORT}/metrics", extra={'endpoint': 'SYSTEM'})
    logger.info(f"Monitoring {len(ENDPOINTS)} endpoints", extra={'endpoint': 'SYSTEM'})
    logger.info("-" * 60, extra={'endpoint': 'SYSTEM'})
    
    # Create and start a thread for each endpoint
    threads = []
    for endpoint_config in ENDPOINTS:
        monitor = EndpointMonitor(endpoint_config)
        thread = threading.Thread(target=monitor.monitor, daemon=True)
        thread.start()
        threads.append(thread)
    
    # Keep the main thread alive
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        logger.info("Monitoring stopped by user", extra={'endpoint': 'SYSTEM'})

if __name__ == "__main__":
    start_monitoring()
