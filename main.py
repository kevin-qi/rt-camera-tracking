import dearpygui.dearpygui as dpg
import numpy as np
import basler
import concurrent.futures
import multiprocessing
import queue
import cv2
import time
import os
import signal

class Controller():
    def __init__(self):
        self.start_event = multiprocessing.Event()
        self.stop_event = multiprocessing.Event()

    def start(self):
        self.start_event.set()

    def end(self):
        self.stop_event.set()

    def is_stopped(self):
        return self.stop_event.is_set()



if __name__ == '__main__':
    os.environ["PYLON_CAMEMU"] = "0"


    image_rgba = np.zeros((600, 960, 4), dtype=np.float32)
    image_rgba[:, :, -1] = 1

    image_rgb = np.ascontiguousarray(image_rgba[:, :, :3])

    controller = Controller()
    out_img = image_rgb
    cam_1 = basler.BaslerCamera(40258011, out_img, controller)
    p = multiprocessing.Process(target = cam_1.grabAndWrite)
    p.start()

    def stop():
        controller.end()

    #pool = multiprocessing.Pool(3)
    #pool.apply_async([grabAndWrite(0, callback)])
    dpg.create_context()


    with dpg.texture_registry(show=True):
        dpg.add_raw_texture(width=960, height=600, default_value=image_rgb, format=dpg.mvFormat_Float_rgb, tag="texture_tag")


    with dpg.window(label="Tutorial"):
        dpg.add_image("texture_tag")
        button1 = dpg.add_button(label="Press Me!", callback = stop)

    dpg.create_viewport(title='Custom Title', width=1200, height=800)
    dpg.setup_dearpygui()




    dpg.show_metrics()
    dpg.show_viewport()
    controller.start_event.set()
    while dpg.is_dearpygui_running():
        # updating the texture in a while loop the frame rate will be limited to the camera frame rate.
        # commenting out the "ret, frame = vid.read()" line will show the full speed that operations and updating a texture can run at
        img = out_img[:]
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        dpg.set_value("texture_tag", img.astype(np.float32))

        # to compare to the base example in the open cv tutorials uncomment below
        #cv.imshow('frame', frame)
        dpg.render_dearpygui_frame()



    dpg.destroy_context()
