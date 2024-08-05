import json
import os
import queue
import threading
import atexit

from interface.queque import QueueInterface

class LocalQueue(QueueInterface):
    def __init__(self, max_size=0, persistence_file='local_queue.json'):
        self.queue = queue.Queue(maxsize=max_size)
        self.lock = threading.Lock()
        self.persistence_file = persistence_file
        self._load_from_file()
        atexit.register(self._save_to_file)  # 注册退出时保存函数

    def enqueue(self, item):
        with self.lock:
            self.queue.put(item)

    def dequeue(self):
        with self.lock:
            if not self.queue.empty():
                return self.queue.get()
            return None

    def size(self):
        return self.queue.qsize()

    def is_empty(self):
        return self.queue.empty()

    def _save_to_file(self):
        with self.lock:
            with open(self.persistence_file, 'w') as f:
                json.dump(list(self.queue.queue), f)

    def _load_from_file(self):
        if os.path.exists(self.persistence_file):
            with open(self.persistence_file, 'r') as f:
                items = json.load(f)
                for item in items:
                    self.queue.put(item)