from pypylon import pylon
import queue
import cv2
import time
import signal
import numpy as np
from vidgear.gears import WriteGear

def find_camera(serial_number):
    tlf = pylon.TlFactory.GetInstance()
    devices = tlf.EnumerateDevices()

    for d in devices:
        print(d.GetSerialNumber())
        if(str(d.GetSerialNumber()) == str(serial_number)):
            return tlf.CreateDevice(d)
    return None

# definition of event handler class
class FrameGrabber(pylon.ImageEventHandler):
    def __init__(self, frame_queue):
        super().__init__()
        self.grab_times = []
        self.frame_queue = frame_queue
        self.img = None

    def OnImageGrabbed(self, camera, grabResult):
        self.grab_times.append(grabResult.TimeStamp)
        self.frame_queue.put(grabResult.Array)
        self.img = grabResult.Array


class BaslerCamera():
    def __init__(self, cam_id, controller):
        self.cam_id = cam_id
        self.controller = controller

        assert not find_camera(self.cam_id) == None, f"Camera {self.cam_id} not found!"

        self.is_stopped = False
        # TODO: Allow selecting which camera

        # TODO: Camera settings
        # https://github.com/basler/pypylon/blob/master/samples/parametrizecameraloadandsaveconfig.py
        #self.cam.LineSelector = "Line3"
        #self.cam.LineMode = "Input"

        #self.cam.TriggerSelector = "FrameStart"
        #self.cam.TriggerSource = "Line3"
        #self.cam.TriggerMode = "Off"

    def setup(self):
        device = find_camera(self.cam_id)
        self.cam = pylon.InstantCamera(device)

        # TODO: Camera settings
        return self.cam

    def grabAndWrite(self, shared_out_buffer):
        img_size = (750, 1000)
        #writer = cv2.VideoWriter(f'video_{cam_id}.avi',
    #                         cv2.VideoWriter_fourcc(*'MJPG'),
        #                     50, size)
        self.setup()
        frame_queue = queue.Queue()
        grabber = FrameGrabber(frame_queue)
        self.cam.RegisterImageEventHandler(grabber,
                                  pylon.RegistrationMode_ReplaceAll,
                                  pylon.Cleanup_None)
        params = {"-input_framerate": 10}
        self.writer = WriteGear(output="Output.mp4", **params)

        # Wait for recording start event
        self.controller.start_event.wait()


        # Start grabbing
        self.cam.StartGrabbing(pylon.GrabStrategy_LatestImages, pylon.GrabLoop_ProvidedByInstantCamera)

        # Continue running until frame_queue is empty and stop signal received
        while(not self.controller.is_stopped() or frame_queue.qsize()):
            if(frame_queue.qsize() > 0):
                if(frame_queue.qsize() > 100):
                    print(frame_queue.qsize())
                img = frame_queue.get()

                #print(arr)

                with shared_out_buffer.get_lock():
                    arr = np.frombuffer(shared_out_buffer.get_obj(), dtype=np.int32).reshape(img_size[0],img_size[1])
                    np.copyto(arr, img)


                self.writer.write(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
                #arr[0] = 1

                #print(arr)
                #print("Got Frame!", flush=True)
                # TODO write image to video
                #writer.write(img)
            else:
                time.sleep(0.00001) # Prevent loop from going crazy

            # If not stopped yet, stop and close camera
            if(self.controller.is_stopped() and not self.is_stopped):
                self.stop()
                self.is_stopped = True


    def stop(self):
        print("stopping", flush=True)
        self.cam.StopGrabbing()
        self.cam.Close()
        self.writer.close()


def signal_handler(sig, frame):
    print('You pressed Ctrl+C!')

def to_numpy_array(shared_array, shape):
    '''Create a numpy array backed by a shared memory Array.'''
    arr = np.ctypeslib.as_array(shared_array)
    #print(arr.dtype)
    return arr.reshape(shape)
