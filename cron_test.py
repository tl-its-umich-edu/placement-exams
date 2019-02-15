from datetime import datetime
import os

def start():
    print(f"starting now:{datetime.now()}")
    print(f"environmental variable: {os.getenv('course')}")


if __name__ == '__main__':
    start()