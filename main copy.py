import speech_recognition as sr
import csv
from datetime import datetime
import re
import sys
import os

# File to store the entries
CSV_FILE = 'time_entries.csv'

def initialize_csv():
    """Initialize the CSV file with headers if it doesn't exist."""
    try:
        with open(CSV_FILE, 'x', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Date', 'JADR', 'Activity Type', 'Hours'])
        print(f"Created new CSV file: {CSV_FILE}")
    except FileExistsError:
        print(f"CSV file already exists: {CSV_FILE}")
    
    print("Current contents of CSV file:")
    try:
        with open(CSV_FILE, 'r') as file:
            print(file.read())
    except Exception as e:
        print(f"Error reading CSV file: {str(e)}")

def add_entry(jadr, activity_type, hours):
    """Add a new entry to the CSV file."""
    try:
        with open(CSV_FILE, 'a', newline='') as file:
            writer = csv.writer(file)
            date = datetime.now().strftime('%Y-%m-%d')
            writer.writerow([date, jadr, activity_type, hours])
        print(f"Entry added successfully: Date: {date}, JADR: {jadr}, Activity: {activity_type}, Hours: {hours}")
        print(f"Current working directory: {os.getcwd()}")
        print(f"Full path of CSV file: {os.path.abspath(CSV_FILE)}")
        
        print("Updated contents of CSV file:")
        with open(CSV_FILE, 'r') as file:
            print(file.read())
    except Exception as e:
        print(f"Error writing to CSV: {str(e)}")

def process_voice_command(command):
    """Process the voice command and extract relevant information."""
    command = command.lower()
    
    # Pattern for entries with JADR number (JADR keyword is optional)
    jadr_pattern = r"(?:add|log|record)\s+(\d+(?:\.\d+)?)\s+hours?\s+(?:to|for)?\s*(?:ja?d?r?|jadr|junior)?\s*(\d+)\s+(?:for)?\s*(.+)"
    
    # Pattern for support hours
    support_pattern = r"(?:add|log|record)\s+(\d+(?:\.\d+)?)\s+hours?\s+(?:for)?\s*support"
    
    # Pattern for generic administrative entries
    admin_pattern = r"(?:add|log|record)\s+(\d+(?:\.\d+)?)\s+hours?\s+(?:for)?\s*(.+)"

    jadr_match = re.match(jadr_pattern, command)
    support_match = re.match(support_pattern, command)
    admin_match = re.match(admin_pattern, command)

    if jadr_match:
        hours, jadr, activity_type = jadr_match.groups()
        # Check if the activity is "administrative"
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
        print("1. 'Add [hours] hours to [number] for [activity]'")
        print("2. 'Add [hours] hours to [number] for Administrative'")
        print("3. 'Add [hours] hours for support'")
        print("4. 'Add [hours] hours for [administrative activity]'")
        print(f"Received: {command}")
        return False

def listen_for_command():
    """Listen for a voice command and process it."""
    recognizer = sr.Recognizer()
    
    with sr.Microphone() as source:
        print("\nListening for command...")
        try:
            audio = recognizer.listen(source, timeout=10, phrase_time_limit=10)
            
            print("Attempting to recognize speech...")
            command = recognizer.recognize_google(audio)
            print(f"Command recognized: {command}")
            if process_voice_command(command):
                print("Command processed successfully. Exiting program.")
                sys.exit(0)
        except sr.WaitTimeoutError:
            print("No speech detected.")
        except sr.UnknownValueError:
            print("Could not understand audio.")
        except sr.RequestError as e:
            print(f"Could not request results; {e}")

def main():
    initialize_csv()
    print("Listening for a command. The program will exit after processing one command.")
    print("Supported formats:")
    print("1. 'Add [hours] hours to [number] for [activity]'")
    print("2. 'Add [hours] hours to [number] for Administrative'")
    print("3. 'Add [hours] hours for support'")
    print("4. 'Add [hours] hours for [administrative activity]'")
    listen_for_command()
    print("No command processed. Exiting program.")

if __name__ == "__main__":
    main()