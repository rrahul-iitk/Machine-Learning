import requests
import base64
import time
import os
import numpy as np
import cv2
from threading import Thread
from pdf2image import convert_from_path

ip = os.environ.get("IP")
cell_ocr = f"http://{ip}/predictions/cell_det"
table_det = f"http://{ip}/predictions/table_det"
all_det = f"http://{ip}/predictions/all_det"

def convertPdf2Png(pdf_path, image_dir_path, dpi=500):
    pages = convert_from_path(pdf_path, dpi=dpi)
    image_paths = []
    for cnt, page in enumerate(pages):
        page_path = os.path.join(image_dir_path, f"{cnt}.png")
        os.makedirs(image_dir_path, exist_ok=True)
        page.save(page_path, 'png')
        image_paths.append(page_path)
    return image_paths


def request_json(image_path):
    decompressed_image_bytes = open(image_path, "rb").read()
    response_raw = requests.put(all_det, data=decompressed_image_bytes)
    response_json = response_raw.json()
    return response_json


class Worker(Thread):

    def __init__(self, threadID, wait_time, image_path, test_time=60, debug=True, experiment="swarm"):
        Thread.__init__(self)
        self.threadID = threadID
        self.experiment = experiment
        self.result = None
        self.image_path = image_path
        self.cnt = 0
        self.wait_time = wait_time
        self.test_time = test_time
        self.logs = []
        self.debug = debug

    def run(self):
        error_log = []
        st = time.time()
        lst = st
        print(f"starting {self.threadID}")
       
        bst = time.time()
        try:
            blocks = request_json(self.image_path)
            assert len(blocks) == 273, "error from server side" + str(len(blocks))
            error_log.append({
                "thread_id": self.threadID,
                "experiment#": self.experiment,
                "status": True,
                "response_time": time.time() - bst,
                "msg": "success",
                "blocks": len(blocks)
            })
        except Exception as e:
            error_log.append({
                "thread_id": self.threadID,
                "experiment#": self.experiment,
                "status": False,
                "response_time": time.time() - bst,
                "msg": "fail",
                "exception": str(e.args)
            })
        #time.sleep(self.wait_time)
        lst = bst
        if self.debug:
            print(error_log[-1])
        self.logs = error_log
        return error_log


if __name__ == "__main__":
    print(request_json(''))