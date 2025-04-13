import json
from django.core.management.base import BaseCommand, CommandError
from log_service.events import (
    get_all_events, 
    register_event_type, 
    register_event,
    get_registry_file_path
)

class Command(BaseCommand):
    """
    Management command to list and manage event types and events.
    """
    help = "List, add, and manage event types and events in the logging system"

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='command', help='Command to run')
        
        # List command
        list_parser = subparsers.add_parser('list', help='List all event types and events')
        list_parser.add_argument(
            '--event-type', 
            help='Filter events by event type',
            required=False
        )
        
        # Add event type command
        add_type_parser = subparsers.add_parser('add-type', help='Add a new event type')
        add_type_parser.add_argument('event_type', help='Name of the event type to add')
        add_type_parser.add_argument('description', help='Description of the event type')
        
        # Add event command
        add_event_parser = subparsers.add_parser('add-event', help='Add a new event to an event type')
        add_event_parser.add_argument('event_type', help='Event type to add the event to')
        add_event_parser.add_argument('event_name', help='Name of the event to add')

    def handle(self, *args, **options):
        command = options.get('command')
        
        if command == 'list':
            self._list_events(options.get('event_type'))
        elif command == 'add-type':
            self._add_event_type(options.get('event_type'), options.get('description'))
        elif command == 'add-event':
            self._add_event(options.get('event_type'), options.get('event_name'))
        else:
            self.stdout.write(self.style.WARNING("Please specify a command: list, add-type, or add-event"))
            self.print_help('manage.py', 'manage_events')
    
    def _list_events(self, event_type_filter=None):
        """List all event types and their registered events."""
        events = get_all_events()
        
        registry_path = get_registry_file_path()
        self.stdout.write(f"Event registry stored at: {registry_path}")
        self.stdout.write("=" * 80)
        
        if event_type_filter:
            if event_type_filter not in events:
                self.stdout.write(self.style.ERROR(f"Event type '{event_type_filter}' not found."))
                return
            events = {event_type_filter: events[event_type_filter]}
        
        for event_type, data in events.items():
            self.stdout.write(self.style.SUCCESS(f"Event Type: {event_type}"))
            self.stdout.write(f"Description: {data['description']}")
            self.stdout.write("Registered Events:")
            
            if data['registered_events']:
                for event in sorted(data['registered_events']):
                    self.stdout.write(f"  - {event}")
            else:
                self.stdout.write("  No events registered yet")
            
            self.stdout.write("-" * 80)
    
    def _add_event_type(self, event_type, description):
        """Add a new event type."""
        register_event_type(event_type, description)
        self.stdout.write(self.style.SUCCESS(
            f"Successfully added event type '{event_type}' with description: {description}"
        ))
    
    def _add_event(self, event_type, event_name):
        """Add a new event to an event type."""
        register_event(event_type, event_name)
        self.stdout.write(self.style.SUCCESS(
            f"Successfully added event '{event_name}' to event type '{event_type}'"
        )) 