from datetime import datetime
import os

def start():
    print(f"starting now:{datetime.now()}")
    print(f"environmental variable: {os.getenv('course')}")
    try:
        with open('/opt/dev/persisted.txt') as f:
            latest_exam_date: str = f.read()
            print(f"""reading from to file persisted.txt the latest test taken date in
                                UTC with current timestamp""")
            return latest_exam_date.strip()
    except (OSError, IOError, Exception) as e:
        print(f"failed do read the file persisted.txt due to {e}")

    try:
        with open('/opt/dev/persisted.txt', 'w+') as f:
            print(f"""writing to file persisted.txt the next query date/latest test taken date in
                                UTC """)
            f.write('success writing to the file')
    except (OSError, IOError, Exception) as e:
        print(f"""failed do write file failed due to {e}""")




if __name__ == '__main__':
    start()