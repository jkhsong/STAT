# import sys
# import csv
# import re
# from datetime import datetime
# from speech_recognition import Recognizer, Microphone, WaitTimeoutError, UnknownValueError, RequestError
# from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QScrollArea
# from PyQt5.QtCore import QThread, pyqtSignal, Qt
# from PyQt5.QtGui import QPixmap
# from pynput.keyboard import GlobalHotKeys
# from fuzzywuzzy import fuzz, process
# from pygame import mixer

import sys
import csv
import re
from datetime import datetime
import speech_recognition as sr
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel, QScrollArea
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QPixmap
from pynput.keyboard import GlobalHotKeys
from fuzzywuzzy import fuzz, process
from pygame import mixer

# File to store the entries
CSV_FILE = 'time_entries.csv'
# File containing JADR numbers and titles
JADR_REFERENCE_FILE = 'jadr_reference.csv'

# Global dictionary to store JADR references
jadr_dict = {}

class VoiceCommandThread(QThread):
    command_processed = pyqtSignal(bool, str)

    def run(self):
        self.listen_for_command()

    def listen_for_command(self):
        recognizer = Recognizer()
        with Microphone() as source:
            print("\nListening for command...")
            try:
                audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
                print("Attempting to recognize speech...")
                command = recognizer.recognize_google(audio)
                print(f"Command recognized: {command}")
                success, message = process_voice_command(command)
                self.command_processed.emit(success, message)
            except WaitTimeoutError:
                print("No speech detected.")
                self.command_processed.emit(False, "No speech detected.")
            except UnknownValueError:
                print("Could not understand audio.")
                self.command_processed.emit(False, "Could not understand audio.")
            except RequestError as e:
                print(f"Could not request results; {e}")
                self.command_processed.emit(False, f"Could not request results; {e}")

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.voice_thread = None
        self.setup_global_hotkey()
        mixer.init()
        mixer.music.load("got_it.wav")

    def initUI(self):
        self.setWindowTitle('Voice Command App')
        self.setFixedSize(600, 400)

        layout = QVBoxLayout()

        # Add centered splash image
        splash_label = QLabel(self)
        pixmap = QPixmap("splash.jpg")
        splash_label.setPixmap(pixmap)
        splash_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(splash_label)

        self.status_label = QLabel('Press "Start" or Ctrl+Shift+A to begin', self)
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.start_button = QPushButton('Start', self)
        self.start_button.clicked.connect(self.start_listening)
        layout.addWidget(self.start_button)

        # Create a scroll area for the result
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.result_label = QLabel()
        self.result_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.result_label.setWordWrap(True)
        scroll_area.setWidget(self.result_label)
        layout.addWidget(scroll_area)

        self.setLayout(layout)

    def setup_global_hotkey(self):
        self.listener = GlobalHotKeys({
            '<ctrl>+<shift>+a': self.start_listening
        })
        self.listener.start()

    def start_listening(self):
        if not self.voice_thread or not self.voice_thread.isRunning():
            self.status_label.setText('Listening for command...')
            self.voice_thread = VoiceCommandThread()
            self.voice_thread.command_processed.connect(self.on_command_processed)
            self.voice_thread.start()

    def on_command_processed(self, success, message):
        self.status_label.setText('Press "Start" or Ctrl+Shift+A to begin')
        self.result_label.setText(message)
        if success:
            mixer.music.play()
        self.voice_thread = None

def load_jadr_references():
    global jadr_dict
    try:
        with open(JADR_REFERENCE_FILE, 'r') as file:
            reader = csv.reader(file)
            for row in reader:
                if len(row) >= 2:
                    jadr_number = row[0].strip()
                    title = row[1].strip().lower()
                    jadr_dict[jadr_number] = title
        print(f"Loaded {len(jadr_dict)} JADR references.")
    except Exception as e:
        print(f"Error loading JADR references: {str(e)}")

def initialize_csv():
    try:
        with open(CSV_FILE, 'x', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Date', 'JADR', 'Activity Type', 'Hours'])
        print(f"Created new CSV file: {CSV_FILE}")
    except FileExistsError:
        print(f"CSV file already exists: {CSV_FILE}")

def add_entry(jadr, activity_type, hours):
    try:
        with open(CSV_FILE, 'a', newline='') as file:
            writer = csv.writer(file)
            date = datetime.now().strftime('%Y-%m-%d')
            writer.writerow([date, jadr, activity_type, hours])
        return f"Entry added successfully:\nDate: {date}\nJADR: {jadr}\nActivity: {activity_type}\nHours: {hours}"
    except Exception as e:
        return f"Error writing to CSV: {str(e)}"

def infer_jadr(text):
    text_lower = text.lower()
    best_match = process.extractOne(text_lower, jadr_dict.values(), scorer=fuzz.partial_ratio)
    
    if best_match and best_match[1] >= 70:  # 70% similarity threshold
        matched_title = best_match[0]
        for jadr, title in jadr_dict.items():
            if title == matched_title:
                return jadr, matched_title
    
    return None, None

def process_voice_command(command):
    command = command.lower()
    
    # Pattern for entries with hours and activity type
    hours_activity_pattern = r"(?:add|log|record)\s+(\d+(?:\.\d+)?)\s+hours?\s+(?:to|for)?\s*(.+)"
    
    hours_activity_match = re.match(hours_activity_pattern, command)

    if hours_activity_match:
        hours, activity = hours_activity_match.groups()
        hours = float(hours)
        activity = activity.strip()

        # Check for special cases: meeting, Administrative, Support
        if activity.lower() in ['meeting', 'administrative', 'support']:
            jadr = ""
            activity_type = activity.capitalize()
            if activity_type == "Meeting":
                activity_type = "Administrative"
        else:
            # Try to infer JADR
            words = activity.split()
            for i in range(len(words)):
                potential_jadr = " ".join(words[:i+1])
                inferred_jadr, matched_title = infer_jadr(potential_jadr)
                if inferred_jadr:
                    jadr = inferred_jadr
                    activity_type = " ".join(words[i+1:])
                    break
            else:  # If no JADR is inferred
                if words[0].isdigit():
                    jadr = words[0]
                    activity_type = " ".join(words[1:])
                else:
                    jadr = ""
                    activity_type = activity

        # Remove 'for' from the beginning of the activity type if present
        activity_type = re.sub(r'^for\s+', '', activity_type, flags=re.IGNORECASE)

        result_message = add_entry(jadr, activity_type, hours)
        return True, result_message
    else:
        message = "Command not recognized. Please use one of the following formats:\n"
        message += "1. 'Add [hours] hours to [JADR number or keyword] for [activity]'\n"
        message += "2. 'Add [hours] hours to Meeting/Administrative/Support'\n"
        message += f"Received: {command}"
        return False, message

def main():
    load_jadr_references()
    initialize_csv()
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()