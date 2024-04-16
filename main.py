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
import ultralytics
import ctypes
import torch

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

def to_numpy_array(shared_array, shape):
    '''Create a numpy array backed by a shared memory Array.'''
    arr = np.ctypeslib.as_array(shared_array)
    return arr.reshape(shape)

if __name__ == '__main__':
    model = ultralytics.YOLO('models/bat_detection_yolov8n_v6/best.onnx')
    #model = ultralytics.YOLO('models/bat_detection_v16/weights/best.onnx')
    #model = ultralytics.YOLO('models/pruned_230827/weights/best_pruned.pt')
    #model = torch.hub.load(".", 'custom', path="/home/batlab/rt-camera-tracking/models/pruned_230827/weights/best_pruned.pt", source='local', force_reload=True)
    os.environ["PYLON_CAMEMU"] = "0"

    img_size = (600, 960)
    image_rgba = np.zeros((img_size[0], img_size[1], 4), dtype=np.float32)
    image_rgba[:, :, -1] = 1

    image_rgb = np.ascontiguousarray(image_rgba[:, :, :3])

    controller = Controller()

    shared_buffer = multiprocessing.Array(ctypes.c_uint, img_size[0]*img_size[1])

    cam_1 = basler.BaslerCamera(24260153, controller)
    p = multiprocessing.Process(target = cam_1.grabAndWrite, args=(shared_buffer,))
    p.start()

    def stop():
        controller.end()

    #pool = multiprocessing.Pool(3)
    #pool.apply_async([grabAndWrite(0, callback)])
    dpg.create_context()


    with dpg.texture_registry(show=True):
        dpg.add_raw_texture(width=img_size[1], height=img_size[0], default_value=image_rgb, format=dpg.mvFormat_Float_rgb, tag="texture_tag")


    with dpg.window(label="Tutorial"):
        dpg.add_image("texture_tag")
        button1 = dpg.add_button(label="Press Me!", callback = stop)

    dpg.create_viewport(title='Custom Title', width=1200, height=800)
    dpg.setup_dearpygui()


    dpg.show_metrics()
    dpg.show_viewport()
    controller.start_event.set()

    i = 0
    coverage_mask = np.zeros(image_rgb.shape).astype(np.uint8)
    while dpg.is_dearpygui_running():
        # updating the texture in a while loop the frame rate will be limited to the camera frame rate.
        # commenting out the "ret, frame = vid.read()" line will show the full speed that operations and updating a texture can run at
        #img = to_numpy_array(shared_buffer, img_size)

        #print(img)
        arr = np.frombuffer(shared_buffer.get_obj(), dtype=np.int32).reshape(img_size[0], img_size[1])
        #print('received', arr.shape, arr.dtype, arr)

        img = cv2.cvtColor(arr.astype(np.uint8), cv2.COLOR_BGR2RGB)
        if(i%15 == 0):
            res = model(img)
            if(len(res) > 0):
                det = res[0].boxes.xyxy.numpy()

                if(len(det) > 0):
                    conf = res[0].boxes.conf.numpy()[0]
                    if(conf > 0.8):
                        x1,y1,x2,y2 = det[0].astype(np.int32)
                        xc = (x1+x2)/2
                        yc = (y1+y2)/2

                        x1 = int(xc-3)
                        x2 = int(xc+3)
                        y1 = int(yc-3)
                        y2 = int(yc+3)
                        #print(x1,y1,x2,y2)
                        cv2.rectangle(coverage_mask, (x1,y1), (x2,y2), (255,255,0), 1)


        i += 1
        img = cv2.addWeighted(img,0.7,coverage_mask,0.3,0)
        img = img.astype(np.float32) / 255.
        dpg.set_value("texture_tag", img)

        # to compare to the base example in the open cv tutorials uncomment below
        #cv.imshow('frame', frame)
        dpg.render_dearpygui_frame()



    dpg.destroy_context()
