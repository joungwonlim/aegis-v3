"""
AEGIS v3.0 - Event System
Event-driven architecture for immediate response
"""
from events.event_bus import event_bus, EventType, Event

__all__ = ['event_bus', 'EventType', 'Event']
