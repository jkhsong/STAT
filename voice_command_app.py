import sys
import csv
import re
from datetime import datetime
import winsound
from speech_recognition import Recognizer, Microphone, WaitTimeoutError, UnknownValueError, RequestError
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QVBoxLayout, QLabel
from PyQt5.QtCore import QThread, pyqtSignal
from pynput.keyboard import GlobalHotKeys

# File to store the entries
CSV_FILE = 'time_entries.csv'
# File containing JADR numbers and titles
JADR_REFERENCE_FILE = 'jadr_reference.csv'

# Global dictionary to store JADR references
jadr_dict = {}

class VoiceCommandThread(QThread):
    command_processed = pyqtSignal(bool)

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
                success = process_voice_command(command)
                self.command_processed.emit(success)
            except WaitTimeoutError:
                print("No speech detected.")
                self.command_processed.emit(False)
            except UnknownValueError:
                print("Could not understand audio.")
                self.command_processed.emit(False)
            except RequestError as e:
                print(f"Could not request results; {e}")
                self.command_processed.emit(False)

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.voice_thread = None
        self.setup_global_hotkey()

    def initUI(self):
        self.setWindowTitle('Voice Command App')
        self.setGeometry(300, 300, 300, 200)

        layout = QVBoxLayout()

        self.status_label = QLabel('Press "Start" or Ctrl+Shift+A to begin', self)
        layout.addWidget(self.status_label)

        self.start_button = QPushButton('Start', self)
        self.start_button.clicked.connect(self.start_listening)
        layout.addWidget(self.start_button)

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

    def on_command_processed(self, success):
        if success:
            self.status_label.setText('Command processed successfully')
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS)
        else:
            self.status_label.setText('Command processing failed')
            winsound.PlaySound("SystemHand", winsound.SND_ALIAS)
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
                    for word in title.split():
                        if word not in jadr_dict:
                            jadr_dict[word] = jadr_number
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
        print(f"Entry added successfully: Date: {date}, JADR: {jadr}, Activity: {activity_type}, Hours: {hours}")
    except Exception as e:
        print(f"Error writing to CSV: {str(e)}")

def infer_jadr(text):
    text_lower = text.lower()
    for key, value in jadr_dict.items():
        if key.lower() in text_lower or value.lower() in text_lower:
            return key if key.isdigit() else value
    return None

def process_voice_command(command):
    command = command.lower()
    
    jadr_pattern = r"(?:add|log|record)\s+(\d+(?:\.\d+)?)\s+hours?\s+(?:to|for)?\s*(.+?)\s+(?:for)?\s*(.+)"
    support_pattern = r"(?:add|log|record)\s+(\d+(?:\.\d+)?)\s+hours?\s+(?:for)?\s*support"
    admin_pattern = r"(?:add|log|record)\s+(\d+(?:\.\d+)?)\s+hours?\s+(?:for)?\s*(.+)"

    jadr_match = re.match(jadr_pattern, command)
    support_match = re.match(support_pattern, command)
    admin_match = re.match(admin_pattern, command)

    if jadr_match:
        hours, jadr_or_keyword, activity_type = jadr_match.groups()
        inferred_jadr = infer_jadr(jadr_or_keyword)
        if inferred_jadr:
            jadr = inferred_jadr
        elif jadr_or_keyword.isdigit():
            jadr = jadr_or_keyword
        else:
            print(f"Could not infer JADR number from '{jadr_or_keyword}'. Using it as is.")
            jadr = jadr_or_keyword

        if activity_type.strip().lower() == "administrative":
            add_entry(jadr, "Administrative", float(hours))
        else:
            add_entry(jadr, activity_type.strip(), float(hours))
        return True
    elif support_match:
        hours = support_match.group(1)
        add_entry("Support", "Support", float(hours))
        return True
    elif admin_match:
        hours, activity_type = admin_match.groups()
        add_entry("Admin", activity_type.strip(), float(hours))
        return True
    else:
        print("Command not recognized. Please use one of the following formats:")
        print("1. 'Add [hours] hours to [JADR number or keyword] for [activity]'")
        print("2. 'Add [hours] hours for support'")
        print("3. 'Add [hours] hours for [administrative activity]'")
        print(f"Received: {command}")
        return False

def main():
    load_jadr_references()
    initialize_csv()
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()