import time
import socket
import cv2
import numpy

from multiprocessing import Process, Manager, Lock

from picrawler import Picrawler
from robot_hat import Music, TTS
from picamera2 import Picamera2


DEFAULT_PORT = 23232


class NetCrawler():
    def __init__(self):
        # PiCrawler stuff
        self.crawler = Picrawler()
        self.music = Music()
        self.tts = TTS()
        self.speed = 80
        # Networking stuff
        self.sock = self._bind_recv_sock()
        self.vr_addr = None
        self.send_process = None
        # Play a sound when ready!
        print(f'Ready to go!')
        self.music.sound_play('./sounds/sign.wav')

    def __del__(self):
        self.sock.close()
        # self.music.sound_play('./sounds/depress.wav')

    def _bind_recv_sock(self, ip='0.0.0.0'):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((ip, DEFAULT_PORT))
        print(f'Listening on {ip}:{DEFAULT_PORT}')
        return sock

    def _send_packet(self, message: str, addr: str, encode: bool = True):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            if encode:
                sock.sendto(message.encode(), addr)
            else:
                sock.sendto(message, addr)
            # print(f'Message of len {len(message)} sent to {addr}')
        finally:
            sock.close()

    def cmd_connect(self, addr):
        self.vr_addr = addr
        print(f'Connected to Unity at {self.vr_addr}')
        self._send_packet('connected', self.vr_addr)
        self.music.sound_play('./sounds/bell.wav')

    def cmd_startcam(self):
        print(f'Starting camera feed!')
        self.send_process = Process(target=self.run_send, args=(self.vr_addr, self.send_feed,))
        self.send_feed.value = True
        self.send_process.start()
        self.music.sound_play('./sounds/bell.wav')

    def cmd_stopcam(self):
        print(f'Stopping camera feed.')
        self.send_feed.value = False
        self.send_process.join()
        self.music.sound_play('./sounds/depress.wav')

    def cmd_disconnect(self, addr):
        print(f'Disconnecting from {self.vr_addr}')
        self._send_packet('disconnected', self.vr_addr)
        self.vr_addr = None
        self.music.sound_play('./sounds/depress2.wav')

    def send_frame(self, camera, vr_addr: str):
        frame = camera.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        encoded, img_buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        data = img_buf.tobytes()
        self._send_packet(data, vr_addr, encode=False)

    def handle_receive(self, data: str, addr: str):
        msg = data.decode()
        print(f'Received message: {msg} from {addr}')
        args = msg.split()
        # If a connection is already present, ignore commands from others
        if self.vr_addr and addr != self.vr_addr:
            print(f'Ignoring command...')
        # Handle connection and disconnection
        if msg == 'connect' and not self.vr_addr:
            self.cmd_connect(addr)
        elif msg == 'disconnect' and self.vr_addr:
            self.cmd_disconnect(addr)
        # Ignore commands if the server address is not set
        if not self.vr_addr:
            return
        # Handle camera feed commands
        if msg == 'startcam':
            self.cmd_startcam()
        elif msg == 'stopcam':
            self.cmd_stopcam()
        # Handle movement commands
        elif msg == 'move forward':
            self.crawler.do_action('forward', 1, self.speed)
        elif msg == 'move backward':
            self.crawler.do_action('backward', 1, self.speed)
        elif msg == 'move left':
            self.crawler.do_action('turn left', 1, self.speed)
        elif msg == 'move right':
            self.crawler.do_action('turn right', 1, self.speed)
        # Handle settings
        elif args[0] == 'speed':
            self.speed = int(args[1])
        elif args[0] == 'step':
            # (r)ight, (l)eft, (f)ront, (b)ack
            positions = [int(n) for n in args[1:]]
            rfx, rfy, rfz, lfx, lfy, lfz, rbx, rby, rbz, lbx, lby, lbz = positions
            new_step = [[rfx, rfy, rfz], [lfx, lfy, lfz], [rbx, rby, rbz], [lbx, lby, lbz]]
            self.crawler.do_step(new_step, self.speed)

    def run_recv(self):
        while True:
            data, addr = self.sock.recvfrom(1024)
            self.handle_receive(data, addr)

    def run_send(self, vr_addr, send_feed):
        camera = Picamera2()
        camera.configure(camera.create_preview_configuration(main={'size': (640, 480)}))
        camera.start()
        while send_feed.value:
            self.send_frame(camera, vr_addr)
    
    def run(self):
        with Manager() as manager:
            # lock = manager.Lock()
            self.send_feed = manager.Value(bool, False)
            # Run the processes
            self.run_recv()


def main():
    crawler = NetCrawler()
    # crawler.run_recv()
    crawler.run()


if __name__ == '__main__':
    main()
