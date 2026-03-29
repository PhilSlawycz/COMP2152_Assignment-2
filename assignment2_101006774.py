"""
Author: <Philip Slawycz>
Assignment: #2
Description: Port Scanner — A tool that scans a target machine for open network ports
"""


import socket
import threading
import sqlite3
import os
import platform
import datetime




print(platform.python_version())
print(os.name)

common_ports = {
    21: "FTP",
    22: "SSH",
    23: "Telnet",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    3306: "MySQL",
    3389: "RDP",
    8080: "HTTP-Alt"
}

class NetworkTool:
    def __init__(self, target):
        self.target = target
        self.open_ports = []

    @property
    def target(self):
        return self.__target

    @target.setter
    def target(self, target):
        if not target.strip():
            raise ValueError("Cannot be empty")
        self.__target = target

    def __del__(self):
        print("NetworkTool instance destroyed")



# Q3: What is the benefit of using @property and @target.setter?
# @property hides __target through name mangling so it can't be
# easily accessed directly. @target.setter forces every assignment
# through validation. This catches bad data immediately rather than
# letting it cause errors later in the program


# Q1: How does PortScanner reuse code from NetworkTool?
# PortScanner inherits from NetworkTool and automatically gets
# the target property, setter validation, and destructor without rewriting them.
# Then super().__init__(target) runs NetworkTool's constructor, setting up __target
# and open_ports. This means any changes made to NetworkTool automatically apply to
# PortScanner without touching its code
#

# - scan_port(self, port):
# Q4: What would happen without try-except here?
# # Without the try-except in scan_port, if there were to be a socket error,
# # the thread would crash.  That port's result would not be recoded into scan_results.
# # then without finally closing the socket would never be closed, causing a resource leak.
#
#     - try-except with socket operations
#     - Create socket, set timeout, connect_ex
#     - Determine Open/Closed status
#     - Look up service name from common_ports (use "Unknown" if not found)
#     - Acquire lock, append (port, status, service_name) tuple, release lock
#     - Close socket in finally block
#     - Catch socket.error, print error message
#
# - get_open_ports(self):
#     - Use list comprehension to return only "Open" results
#
# Q2: Why do we use threading instead of scanning one port at a time?
# We use threading as sequential scanning takes up to one second per port,
# which at over one thousand ports would take that many seconds. While threading
# allows all ports to scan simultaneously, bringing down the time to around one second.
# This however, causes an issue in which thread can overwrite each-others results,
# which is why threading.Lock() is needed to write only one at a time.
#
# - scan_range(self, start_port, end_port):
#     - Create threads list
#     - Create Thread for each port targeting scan_port
#     - Start all threads (one loop)
#     - Join all threads (separate loop)
class PortScanner(NetworkTool):
    def __init__(self, target):
        super().__init__(target)
        self.scan_results = []
        self.lock = threading.Lock()
    def __del__(self):
        print("PortScanner instance destroyed")
        super().__del__()
    def scan_port(self, port):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((self.target, port))
            status = "Open" if result == 0 else "Closed"
            service_name = common_ports.get(port, "Unknown")
            with self.lock:
                self.scan_results.append((port, status, service_name))
        except socket.error as e:
            print(f"Socket error on port {port}: {e}")
        finally:
            sock.close()
    def get_open_ports(self):
        return [(port, service) for port, status, service in self.scan_results if status == "Open"]

    def scan_range(self, start_port, end_port):
        threads = []
        for port in range (start_port, end_port + 1):
            t = threading.Thread(target=self.scan_port, args=(port,))
            threads.append(t)
        for t in threads:
            t.start()
        for t in threads:
            t.join()


def save_results(target, results):
    """Create the scans table if it doesn't exist."""
    try:
        conn = sqlite3.connect("scan_history.db")
        cursor = conn.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT,
            port INTEGER,
            status TEXT,
            service TEXT,
            scan_date DATE
            )""")
        for port, status, service in results:
            cursor.execute(""" INSERT INTO scans (target,  port, status, service, scan_date)
            VALUES (?, ?, ?, ?, ?)
            """, (target, port, status, service, datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except sqlite3.Error as e:
        print(f"Database error: {e} ")
    finally:
        conn.close()


def load_past_scans():
    try:
        conn = sqlite3.connect("scan_history.db")
        cursor = conn.cursor()
        cursor.execute(" SELECT * FROM scans")
        rows = cursor.fetchall()
        for row in rows:
            print(f"Target: {row[1]}, Port: {row[2]}, Status: {row[3]}, Service: {row[4]}, Date: {row[5]}")

    except sqlite3.Error:
        print("No past scans found.")
    finally:
        conn.close()
# ============================================================
# MAIN PROGRAM
# ============================================================
if __name__ == "__main__":


    try:
        target = input("Input the target IP: ").strip()
        if not target:
            target ="127.0.0.1"
        starting_port = int(input("Enter a port from (1-1024): ").strip())
        ending_port = int(input("Enter another port from (1-1024): "). strip())
        if not (1 <=starting_port <= 1024) or not (1 <=ending_port <= 1024):
            print("Port must be between 1 and 1024.")
        elif ending_port < starting_port:
            print("End port number has to be greater than the starting port number.")
        else:
            scanner = PortScanner(target)
            print(f"Scanning {target} from port {starting_port} to {ending_port}...")
            scanner.scan_range(starting_port, ending_port)
            open_ports = scanner.get_open_ports()
            for port, service in open_ports:
                print(f"Port {port}: {service}")
            print(f"Total open ports found: {len(open_ports)}")
            save_results(scanner.target, scanner.scan_results)
            scan_history = input("Would you like to see past scan history? (yes/no):").strip().lower()
            if scan_history == "yes":
                load_past_scans()
    except ValueError:
        print("Invalid input. Please enter a valid integer.")
    except Exception as e:
        print(f"Unexpected error: {e}")



# Q5: New Feature Proposal
# One feature that I would suggest is adding the ability to export scan
# results from the program as a CSV file. It would be added as a method
# in PortScanner and called after save_results in the main block. It would
# use a list comprehension to filter only open ports before writing them
# to the file.
# Diagram: See diagram_101006774.png in the repository root
