"""
Rate limiting utility for MCP tools
"""
from datetime import datetime
import threading
from collections import deque
import time

class RateLimiter:
    def __init__(self, max_requests: int, time_window_seconds: int):
        """
        Initialize a rate limiter.
        
        Args:
            max_requests: Maximum number of requests allowed in the time window
            time_window_seconds: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window_seconds = time_window_seconds
        self.requests = deque()
        self.lock = threading.Lock()

    def can_make_request(self) -> bool:
        """Check if a request can be made within the rate limit."""
        now = datetime.now()
        with self.lock:
            # Remove old requests
            while self.requests and (now - self.requests[0]).total_seconds() > self.time_window_seconds:
                self.requests.popleft()
            
            # Check if we can make a new request
            if len(self.requests) < self.max_requests:
                self.requests.append(now)
                return True
            return False

    def wait_for_slot(self):
        """Block until a request slot is available."""
        while not self.can_make_request():
            time.sleep(1)  # Wait 1 second before checking again 