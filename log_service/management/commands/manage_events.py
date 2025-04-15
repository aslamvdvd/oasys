import json
from django.core.management.base import BaseCommand, CommandError

# Use Enum and helpers
from log_service.events import (
    LogEventType,
    get_all_events,
    register_event, # Use the unified register_event
    get_registry_file_path
)

class Command(BaseCommand):
    """
    Management command to list and manage event types and registered events.
    Uses LogEventType Enum for adding events.
    """
    help = "List, add, and manage event types and registered events in the logging system."

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='command', help='Sub-command to run', required=True)
        
        # List command
        list_parser = subparsers.add_parser('list', help='List all or specific event types and their registered events')
        list_parser.add_argument(
            '--type', 
            choices=[e.value for e in LogEventType], # Use Enum values for choices
            help='Filter events by a specific event type (e.g., user_activity)',
            required=False,
            dest='event_type_filter' # Store in options under this name
        )
        
        # Add event command (Removing add-type as types are defined by Enum now)
        add_event_parser = subparsers.add_parser('register-event', help='Register a specific event name under an existing event type')
        add_event_parser.add_argument(
            'event_type', 
            choices=[e.value for e in LogEventType],
            help='The event type category (e.g., user_activity)'
        )
        add_event_parser.add_argument('event_name', help='The specific event name string to register (e.g., \'password_reset_request\')')

    def handle(self, *args, **options):
        command = options.get('command')
        
        if command == 'list':
            self._list_events(options.get('event_type_filter'))
        elif command == 'register-event':
            self._register_event_cmd(options.get('event_type'), options.get('event_name'))
    
    def _list_events(self, event_type_filter_str=None):
        """Lists event types and registered events, potentially filtered."""
        try:
            all_event_data = get_all_events() # Already uses Enums internally
        except Exception as e:
            raise CommandError(f"Failed to load event registry: {e}")
            
        registry_path = get_registry_file_path()
        self.stdout.write(f"Event registry stored at: {registry_path}")
        self.stdout.write("=" * 80)
        
        events_to_list = all_event_data
        if event_type_filter_str:
            if event_type_filter_str not in all_event_data:
                self.stdout.write(self.style.ERROR(f"Event type '{event_type_filter_str}' not found in registry."))
                valid_types = ", ".join(all_event_data.keys())
                self.stdout.write(f"Valid types are: {valid_types}")
                return
            events_to_list = {event_type_filter_str: all_event_data[event_type_filter_str]}
        
        if not events_to_list:
             self.stdout.write(self.style.WARNING("No event types found or registry is empty."))
             return
             
        for event_type_str, data in sorted(events_to_list.items()):
            self.stdout.write(self.style.SUCCESS(f"Event Type: {event_type_str}"))
            self.stdout.write(f"  Description: {data.get('description', 'N/A')}")
            registered = sorted(data.get('registered_events', []))
            self.stdout.write(f"  Registered Events ({len(registered)}):")
            if registered:
                for event in registered:
                    self.stdout.write(f"    - {event}")
            else:
                self.stdout.write(f"    (No specific events registered for this type yet)")
            self.stdout.write("---") # Separator
    
    # Removed _add_event_type method
    
    def _register_event_cmd(self, event_type_str, event_name):
        """Handles the register-event sub-command."""
        if not event_name:
             raise CommandError("Event name cannot be empty.")
             
        try:
            event_type_enum = LogEventType(event_type_str)
            register_event(event_type_enum, event_name) # Use the unified function
            self.stdout.write(self.style.SUCCESS(
                f"Successfully registered event '{event_name}' under type '{event_type_str}'."
            ))
        except ValueError:
             # Should not happen due to choices in add_arguments, but good practice
             raise CommandError(f"Invalid event type specified: {event_type_str}")
        except Exception as e:
             raise CommandError(f"Failed to register event: {e}") 