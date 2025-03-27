import time
import socket
import cv2
import numpy
from datetime import datetime

from multiprocessing import Process, Manager, Lock

from picrawler import Picrawler
from robot_hat import Music, TTS
from picamera2 import Picamera2


DEFAULT_PORT = 23232
INPUT_TIMEOUT_SECS = 60
DEBUG = True
CMD_SOUNDS = True


def dbg(*args, **kwargs):
    if DEBUG:
        print(f'[{datetime.now().strftime("%H:%M:%S")}] ', end='')
        print(*args, **kwargs)


class NetCrawler():
    def __init__(self):
        # PiCrawler
        dbg(f'Booting up Crawler...')
        self.crawler = Picrawler()
        dbg(f'Booting up Music/TTS...')
        self.music = Music()
        self.tts = TTS()
        self.speed = 80
        # Networking
        self.sock = self._bind_recv_sock()
        self.vr_addr = None
        self.send_process = None
        self.terminate = False
        # Multithreading
        self.manager = Manager()
        self.send_feed = self.manager.Value(bool, False)
        # Play a sound when ready!
        dbg(f'Ready to go!')
        self.music.sound_play('./sounds/sign.wav')

    def __del__(self):
        self.manager.shutdown()
        self.sock.close()

    def _bind_recv_sock(self, ip='0.0.0.0'):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(INPUT_TIMEOUT_SECS)
        sock.bind((ip, DEFAULT_PORT))
        dbg(f'Listening on {ip}:{DEFAULT_PORT}')
        return sock

    def _send_packet(self, message: str, addr: str, encode: bool = True, sock: socket.socket = None, debug: bool = True):
        close_socket = False
        if sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            close_socket = True
        try:
            sock.sendto(message.encode() if encode else message, addr)
            if debug:
                dbg(f'Message "{message}" sent to {addr}')
            # self.dbg_slow(1, f'Message of len {len(message)} sent to {addr}')
        finally:
            if close_socket:
                sock.close()

    def _soundarg(self, args):
        return (False if len(args) > 1 and args[1] == 'nosound' else CMD_SOUNDS)

    def cmd_connect(self, addr, sound=CMD_SOUNDS):
        self.vr_addr = addr
        dbg(f'Connected to Unity at {self.vr_addr}')
        self._send_packet('connected', self.vr_addr)
        if sound:
            self.music.sound_play('./sounds/bell.wav')

    def cmd_startcam(self, sound=CMD_SOUNDS):
        if self.send_feed.value:
            dbg(f'Camera already running. Ignoring command...')
        dbg(f'Starting camera feed!')
        self.send_feed.value = True
        self.send_process = Process(target=self.run_send, args=(self.vr_addr, self.send_feed,))
        self.send_process.start()
        if sound:
            self.music.sound_play('./sounds/bell.wav')

    def cmd_stopcam(self, sound=CMD_SOUNDS):
        dbg(f'Stopping camera feed.')
        self.send_feed.value = False
        if self.send_process is not None and self.send_process.is_alive():
            self.send_process.join()
        if sound:
            self.music.sound_play('./sounds/depress.wav')

    def cmd_disconnect(self, sound=CMD_SOUNDS):
        dbg(f'Disconnecting from {self.vr_addr}')
        self._send_packet('disconnected', self.vr_addr)
        self.vr_addr = None
        self.cmd_stopcam(sound=False)
        if sound:
            self.music.sound_play('./sounds/depress2.wav')

    def send_frame(self, camera, vr_addr: str, sock=None):
        frame = camera.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        encoded, img_buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        data = img_buf.tobytes()
        self._send_packet(data, vr_addr, encode=False, sock=sock, debug=False)

    def handle_receive(self, data: str, addr: str):
        msg = data.decode()
        dbg(f'Message "{msg}" received from {addr}')
        args = msg.split()
        # If a connection exists, ignore commands from others
        if self.vr_addr and addr != self.vr_addr:
            dbg(f'Message is from another connection. Ignoring command...')
        # Handle connection and disconnection
        if args[0] == 'connect' and not self.vr_addr:
            self.cmd_connect(addr, sound=self._soundarg(args))
        elif args[0] == 'disconnect' and self.vr_addr:
            self.cmd_disconnect(sound=self._soundarg(args))
        elif msg == 'quit':
            self.cmd_disconnect(sound=True)
            self.terminate = True

        # Ignore commands if the server address is not set
        if not self.vr_addr:
            return
        # Handle camera feed commands
        if args[0] == 'startcam':
            self.cmd_startcam(sound=self._soundarg(args))
        elif args[0] == 'stopcam':
            self.cmd_stopcam(sound=self._soundarg(args))
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
        else:
            dbg('Unknown command. Ignoring...')

    def run_recv(self):
        while not self.terminate:
            try:
                data, addr = self.sock.recvfrom(1024)
                self.handle_receive(data, addr)
            except TimeoutError:
                if self.vr_addr:
                    dbg(f'TimeoutError: Didn\'t receive input for {INPUT_TIMEOUT_SECS} seconds. Disconnecting...')
                    self.cmd_disconnect()

    def run_send(self, vr_addr, send_feed):
        camera = Picamera2()
        camera.configure(camera.create_preview_configuration(main={'size': (640, 480)}))
        camera.start()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        start = time.perf_counter()
        fps = 0
        while send_feed.value:
            self.send_frame(camera, vr_addr, sock)
            if time.perf_counter() - start > 10:
                dbg(f'Sent {fps} frames ({round(fps/10)} fps) to {vr_addr}')
                fps = 0
                start = time.perf_counter()
            fps += 1
        dbg(f'Closing thread - Sent {fps} frames ({round(fps/10)} fps) to {vr_addr}')
        camera.stop()

    def run(self):
        self.run_recv()


def main():
    crawler = NetCrawler()
    crawler.run()


if __name__ == '__main__':
    main()
