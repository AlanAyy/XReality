from enum import Enum
from datetime import datetime
import time
import socket

import cv2
import numpy

from multiprocessing import Process, Manager, Lock

from picrawler import Picrawler
from robot_hat import Music, TTS
from picamera2 import Picamera2


class DebugType(Enum):
    BOOT = 0
    NETWORK = 1
    STREAM = 2
    CAMERA = 3
    CRAWLER = 4
    SOUND = 5


# Configs
DEFAULT_PORT = 23232
INPUT_TIMEOUT_SECS = 120
DEBUG = True
DEBUG_FLAGS = {
    DebugType.BOOT: True,
    DebugType.NETWORK: True,
    DebugType.STREAM: False,
    DebugType.CAMERA: True,
    DebugType.CRAWLER: True,
    DebugType.SOUND: True
}
CMD_SOUNDS = True


def dbg(*args, debug_type: DebugType = None, **kwargs):
    if not DEBUG:
        return
    if debug_type is None or DEBUG_FLAGS.get(debug_type):
        print(f'[{datetime.now().strftime("%H:%M:%S")}] ', end='')
        print(f'{debug_type.name} \t> ' if debug_type is not None else '????? \t> ', end='')
        print(*args, **kwargs)

def dbg_boot(*args, **kwargs):
    dbg(*args, debug_type=DebugType.BOOT, **kwargs)

def dbg_net(*args, **kwargs):
    dbg(*args, debug_type=DebugType.NETWORK, **kwargs)

def dbg_stream(*args, **kwargs):
    dbg(*args, debug_type=DebugType.STREAM, **kwargs)

def dbg_cam(*args, **kwargs):
    dbg(*args, debug_type=DebugType.CAMERA, **kwargs)

def dbg_crawl(*args, **kwargs):
    dbg(*args, debug_type=DebugType.CRAWLER, **kwargs)

def dbg_sound(*args, **kwargs):
    dbg(*args, debug_type=DebugType.SOUND, **kwargs)


class NetCrawler():
    def __init__(self):
        # PiCrawler
        dbg_boot(f'Booting up Crawler...')
        self.crawler = Picrawler()
        dbg_boot(f'Booting up Music/TTS...')
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
        dbg_boot(f'Ready to go!')
        self.play_sound('./sounds/sign.wav')

    def __del__(self):
        self.manager.shutdown()
        self.sock.close()

    def _bind_recv_sock(self, ip='0.0.0.0'):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(INPUT_TIMEOUT_SECS)
        sock.bind((ip, DEFAULT_PORT))
        dbg_net(f'Listening on {ip}:{DEFAULT_PORT}')
        return sock

    def _send_packet(self, message: str, addr: str, encode: bool = True, sock: socket.socket = None, is_stream: bool = False):
        close_socket = False
        if sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            close_socket = True
        try:
            sock.sendto(message.encode() if encode else message, addr)
            if is_stream:
                dbg_stream(f'Sent message len({len(message)}) to {addr}')
            else:
                dbg_net(f'Sent message "{message}" to {addr}')
        except TypeError as e:
            dbg(f'TypeError - Could not send send message.')
            dbg(f'Stack trace: {e}')
        finally:
            if close_socket:
                sock.close()

    def _soundarg(self, args):
        return (False if len(args) > 1 and args[1] == 'nosound' else CMD_SOUNDS)

    def play_sound(self, sound_file: str):
        dbg_sound(f'Playing sound: "{sound_file}"')
        self.music.sound_play(sound_file)

    def crawl_action(self, action: str, times: int = 1, speed: int = None):
        dbg_crawl(f'Performing action (x{times}): "{action}" at {speed}% speed')
        self.crawler.do_action(action, times, speed)

    def cmd_connect(self, addr, sound=CMD_SOUNDS):
        self.vr_addr = addr
        dbg_net(f'Connected to Unity at {self.vr_addr}')
        self._send_packet('connected', self.vr_addr)
        if sound:
            self.play_sound('./sounds/bell.wav')

    def cmd_startcam(self, sound=CMD_SOUNDS):
        if self.send_feed.value:
            dbg_net(f'Camera already running. Ignoring command...')
        dbg_cam(f'Starting camera feed!')
        self.send_feed.value = True
        self.send_process = Process(target=self.run_send, args=(self.vr_addr, self.send_feed,))
        self.send_process.start()
        if sound:
            self.play_sound('./sounds/bell.wav')

    def cmd_stopcam(self, sound=CMD_SOUNDS):
        dbg_cam(f'Stopping camera feed.')
        self.send_feed.value = False
        if self.send_process is not None and self.send_process.is_alive():
            self.send_process.join()
        if sound:
            self.play_sound('./sounds/depress.wav')

    def cmd_disconnect(self, sound=CMD_SOUNDS):
        dbg_net(f'Disconnecting from {self.vr_addr}')
        self._send_packet('disconnected', self.vr_addr)
        self.vr_addr = None
        self.cmd_stopcam(sound=False)
        if sound:
            self.play_sound('./sounds/depress2.wav')

    def send_frame(self, camera, vr_addr: str, sock=None):
        frame = camera.capture_array()
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        encoded, img_buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        data = img_buf.tobytes()
        self._send_packet(data, vr_addr, encode=False, sock=sock, is_stream=True)

    def handle_receive(self, data: str, addr: str):
        msg = data.decode()
        dbg_net(f'Received "{msg}" from {addr}{"" if self.vr_addr else " (Not connected)"}')
        args = msg.split()
        # If a connection exists, ignore commands from others
        if self.vr_addr and addr != self.vr_addr:
            dbg_net(f'Message is from another connection. Ignoring command...')
        # Handle connection
        if args[0] == 'connect' and not self.vr_addr:
            self.cmd_connect(addr, sound=self._soundarg(args))

        # Ignore commands if the server address is not set
        if not self.vr_addr:
            return
        # Handle disconnection and quitting
        elif args[0] == 'disconnect':
            self.cmd_disconnect(sound=self._soundarg(args))
        elif msg == 'quit':
            self.cmd_disconnect(sound=True)
            self.terminate = True

        # Handle camera feed commands
        if args[0] == 'startcam':
            self.cmd_startcam(sound=self._soundarg(args))
        elif args[0] == 'stopcam':
            self.cmd_stopcam(sound=self._soundarg(args))
        # Handle movement commands
        elif msg == 'move forward':
            self.crawl_action('forward', 1, self.speed)
        elif msg == 'move backward':
            self.crawl_action('backward', 1, self.speed)
        elif msg == 'move left':
            self.crawl_action('turn left', 1, self.speed)
        elif msg == 'move right':
            self.crawl_action('turn right', 1, self.speed)
        # Handle settings
        elif args[0] == 'speed':
            self.speed = int(args[1])
        elif args[0] == 'step':
            # (r)ight, (l)eft, (f)ront, (b)ack
            positions = [int(n) for n in args[1:]]
            rfx, rfy, rfz, lfx, lfy, lfz, rbx, rby, rbz, lbx, lby, lbz = positions
            new_step = [[rfx, rfy, rfz], [lfx, lfy, lfz], [rbx, rby, rbz], [lbx, lby, lbz]]
            dbg_crawl(f'Setting new step: {new_step}')
            self.crawler.do_step(new_step, self.speed)
        else:
            dbg(f'Unknown command {msg}. Ignoring...')

    def run_recv(self):
        while not self.terminate:
            try:
                data, addr = self.sock.recvfrom(1024)
                self.handle_receive(data, addr)
            except TimeoutError:
                if self.vr_addr:
                    dbg_net(f'TimeoutError: Didn\'t receive input for {INPUT_TIMEOUT_SECS} seconds. Disconnecting...')
                    self.cmd_disconnect()
            except KeyboardInterrupt:
                dbg(f'KeyboardInterrupt - Shutting down...')
                self.cmd_disconnect()
                self.terminate = True

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
                dbg_net(f'Sent {fps} frames ({round(fps/10)} fps) to {vr_addr}')
                fps = 0
                start = time.perf_counter()
            fps += 1
        dbg_net(f'Closing thread - Sent {fps} frames ({round(fps/10)} fps) to {vr_addr}')
        camera.stop()

    def run(self):
        self.run_recv()


def main():
    crawler = NetCrawler()
    crawler.run()


if __name__ == '__main__':
    main()
