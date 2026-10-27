import asyncio
import json
import os
from typing import Dict, Set, Callable, Any
import logging

try:
    import redis
except ImportError:  # pragma: no cover - optional dependency
    redis = None


logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "false").lower() == "true"


class PubSubManager:
    """Manages real-time event publishing and subscriptions"""

    def __init__(self):
        self.subscriptions: Dict[str, Set[asyncio.Queue]] = {}
        self.redis_client = None
        self._init_redis()

    def _init_redis(self):
        """Initialize Redis connection if enabled"""
        if not REDIS_ENABLED:
            logger.info("Redis pub/sub disabled - using in-memory queues")
            return

        try:
            # Parse Redis URL
            self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            self.redis_client.ping()
            logger.info(f"✅ Connected to Redis: {REDIS_URL}")
        except Exception as e:
            logger.warning(f"⚠️ Redis connection failed: {e} - using in-memory queues")
            self.redis_client = None

    async def subscribe(self, channel: str) -> asyncio.Queue:
        """Subscribe to a channel and return a queue for messages"""
        if channel not in self.subscriptions:
            self.subscriptions[channel] = set()

        queue = asyncio.Queue()
        self.subscriptions[channel].add(queue)

        logger.debug(f"New subscription to {channel} (total: {len(self.subscriptions[channel])})")
        return queue

    async def unsubscribe(self, channel: str, queue: asyncio.Queue):
        """Unsubscribe from a channel"""
        if channel in self.subscriptions:
            self.subscriptions[channel].discard(queue)
            logger.debug(f"Unsubscribed from {channel}")

    async def publish(self, channel: str, data: Any):
        """Publish an event to a channel"""
        message = {
            "channel": channel,
            "data": data,
            "timestamp": str(__import__('datetime').datetime.now().isoformat()),
        }

        # Publish to Redis if available
        if self.redis_client:
            try:
                self.redis_client.publish(channel, json.dumps(message))
                logger.debug(f"Published to Redis channel: {channel}")
            except Exception as e:
                logger.error(f"Redis publish error: {e}")

        # Publish to local subscribers
        if channel in self.subscriptions:
            for queue in self.subscriptions[channel]:
                try:
                    await queue.put(message)
                except Exception as e:
                    logger.error(f"Error publishing to queue: {e}")


# Global pub/sub manager
_pubsub_manager = PubSubManager()


def get_pubsub_manager() -> PubSubManager:
    """Get global pub/sub manager instance"""
    return _pubsub_manager


# ============================================================================
# CHANNEL DEFINITIONS
# ============================================================================

class EventChannels:
    """Predefined event channels"""

    @staticmethod
    def new_frame(patient_id: str) -> str:
        """Channel for new sensor frames"""
        return f"new_frame:{patient_id}"

    @staticmethod
    def alert(patient_id: str) -> str:
        """Channel for patient alerts"""
        return f"alerts:{patient_id}"

    @staticmethod
    def device_status(device_id: str) -> str:
        """Channel for device status updates"""
        return f"status:{device_id}"

    @staticmethod
    def session_started(session_id: str) -> str:
        """Channel for session start events"""
        return f"session_start:{session_id}"

    @staticmethod
    def session_ended(session_id: str) -> str:
        """Channel for session end events"""
        return f"session_end:{session_id}"


# ============================================================================
# EVENT PUBLISHING HELPERS
# ============================================================================

async def publish_sensor_frame(patient_id: str, frame_data: Dict[str, Any]):
    """Publish a new sensor frame event"""
    channel = EventChannels.new_frame(patient_id)
    await get_pubsub_manager().publish(channel, frame_data)
    logger.debug(f"Published sensor frame for patient {patient_id}")


async def publish_alert(patient_id: str, alert_data: Dict[str, Any]):
    """Publish an alert event"""
    channel = EventChannels.alert(patient_id)
    await get_pubsub_manager().publish(channel, alert_data)
    logger.info(f"Published alert for patient {patient_id}")


async def publish_device_status(device_id: str, status_data: Dict[str, Any]):
    """Publish a device status update"""
    channel = EventChannels.device_status(device_id)
    await get_pubsub_manager().publish(channel, status_data)
    logger.debug(f"Published device status for {device_id}")


async def publish_session_event(session_id: str, event_type: str, data: Dict[str, Any]):
    """Publish a session lifecycle event"""
    if event_type == "start":
        channel = EventChannels.session_started(session_id)
    elif event_type == "end":
        channel = EventChannels.session_ended(session_id)
    else:
        return

    await get_pubsub_manager().publish(channel, data)
    logger.info(f"Published session event: {event_type} for {session_id}")
