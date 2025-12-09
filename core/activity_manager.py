from schemas.base_models import ActivityRecorder
from schemas.activity_schemas import Activities
from services.index_manager import FaissIndexManager
from config import RecordingConfig

import time
import threading
from typing import Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RecordingState:
    is_active: bool = False
    last_screen_time: float = 0
    last_app_time: float = 0

class ActivityManager:    
    def __init__(self, 
                screen_activity_recorder: ActivityRecorder, 
                app_activity_recorder: ActivityRecorder,
                faiss_index_manager: FaissIndexManager,
                recording_config: RecordingConfig):
        """
        Initialize ActivityManager with screen and app activity recorders.
        
        Args:
            screen_activity_recorder: Recorder for screen activities
            app_activity_recorder: Recorder for application activities
            recording_config: Configuration dictionary containing recording settings
        """
        self.screen_activity_recorder = screen_activity_recorder
        self.app_activity_recorder = app_activity_recorder
        self.recording_config = recording_config
        self.faiss_index_manager = faiss_index_manager
        self.index_lock = threading.Lock()  # Add thread lock for index access
        
        self.session_activites = Activities(activities=[])

        self.state = RecordingState()
        self.screen_thread: Optional[threading.Thread] = None
        self.app_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.last_app_activity = None  # Track the last recorded app activity
    
    
    
    def _record_screen_activity(self):
        """Background thread function for recording screen activities."""
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                if current_time - self.state.last_screen_time >= self.recording_config.screenshot_interval_seconds:
                    activity = self.screen_activity_recorder.record_activity()

                    # print(activity)

                    with self.index_lock:
                        self.faiss_index_manager.add_text(
                            text=activity.keywords, 
                            metadata={'activity': activity, 'type': type(activity)}
                        )

                    # Process or store the recorded activity as needed
                    self.state.last_screen_time = current_time
                    print(f"Added new screenshot activity")
                    
                time.sleep(0.1)  # Small sleep to prevent CPU overuse
            except Exception as e:
                import traceback
                print(f"Error in screen recording thread: {e}")
                traceback.print_exc()
                break
    
    def _record_app_activity(self):
        """Background thread function for recording application activities."""
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                if current_time - self.state.last_app_time >= self.recording_config.app_poll_interval_seconds:
                    activity = self.app_activity_recorder.record_activity()
                    
                    # Only add if this is the first activity or if app_name/window_title changed
                    should_add = False
                    with self.index_lock:
                        if self.last_app_activity is None or \
                           activity.app_name != self.last_app_activity.app_name or \
                           activity.window_title != self.last_app_activity.window_title:
                            
                            self.faiss_index_manager.add_text(
                                text=activity.keywords, 
                                metadata={'activity': activity, 'type': type(activity)}
                            )
                            self.session_activites = self.faiss_index_manager.get_activities_metadata()

                            self.app_activity_recorder.last_switch_time = time.time()

                            self.last_app_activity = activity  # Update the last activity
                            should_add = True
                    
                    if should_add:
                        print(f"Added new app activity: {activity.app_name} - {activity.window_title}")
                    
                    self.state.last_app_time = current_time
                time.sleep(0.1)  # Small sleep to prevent CPU overuse
            except Exception as e:
                print(f"Error in app recording thread: {e}")
                import traceback
                traceback.print_exc()
                break
    
    def start_recording(self):
        """Start recording screen and application activities in separate threads."""
        if self.state.is_active:
            print("Recording is already in progress")
            return
        
        self.state = RecordingState(is_active=True)
        self.stop_event.clear()
        
        # Start screen recording thread
        self.screen_thread = threading.Thread(
            target=self._record_screen_activity,
            daemon=True,
            name="ScreenRecorderThread"
        )
        
        # Start app activity recording thread
        self.app_thread = threading.Thread(
            target=self._record_app_activity,
            daemon=True,
            name="AppRecorderThread"
        )
        
        self.screen_thread.start()
        self.app_thread.start()
        
        print("Started recording screen and application activities")
    
    def stop_recording(self):
        """Stop all recording activities and clean up resources."""
        if not self.state.is_active:
            return
        
        self.state.is_active = False
        self.stop_event.set()
        
        if self.screen_thread and self.screen_thread.is_alive():
            self.screen_thread.join(timeout=2.0)
        
        if self.app_thread and self.app_thread.is_alive():
            self.app_thread.join(timeout=2.0)
        
        print("Stopped all recording activities")
    
    def load_session(self, session_path: str):
        """
        Safely switch to a different session by loading its FAISS index.
        
        Args:
            session_path: Path to the session's index file to load
            
        This method ensures thread safety when switching sessions during recording.
        """
        if not session_path.endswith(".joblib"):
            session_path += ".joblib"
            
        # Stop recording if active
        was_recording = self.state.is_active
        if was_recording:
            self.stop_recording()
            
        try:
            # Load the session's index
            self.session_activites = self.faiss_index_manager.load_index(session_path)
            print(f"Successfully switched to session: {session_path}")
        except Exception as e:
            print(f"Error changing session: {str(e)}")
            if was_recording:
                self.start_recording()  # Restart with old session if loading fails
            raise
            
        # Restart recording if it was active
        if was_recording:
            self.start_recording()

    
    def get_session_activities(self) -> Activities:
        return self.session_activites
        


            
    def create_session(self, session_path: str):
        """
        Create a new session with a fresh FAISS index.
        
        Args:
            session_path: Path where to create the new session's index file
            
        This will create a new empty index for the session.
        """
        if not session_path.endswith(".joblib"):
            session_path += ".joblib"
            
        # Stop recording if active
        was_recording = self.state.is_active
        if was_recording:
            self.stop_recording()
            
        try:
            # Create a new empty index for the session
            self.session_activites = self.faiss_index_manager.create_index(session_path)
            print(f"Successfully created new session: {session_path}")
        except Exception as e:
            print(f"Error creating session: {str(e)}")
            if was_recording:
                self.start_recording()  # Restart with old session if creation fails
            raise
            
        # Restart recording if it was active
        if was_recording:
            self.start_recording()
        
            
    def __del__(self):
        """Ensure threads are properly stopped when the object is destroyed."""
        self.stop_recording()