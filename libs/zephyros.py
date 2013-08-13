#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import sys
import time
import json
import uuid
import Queue
import signal
import select
import socket
import threading

class StoppableThread(threading.Thread):

    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()


class Listener(StoppableThread):

    def __init__(self, host='127.0.0.1', port=1235):
        super(Listener, self).__init__()
        self.daemon = True
        self._host = host
        self._port = port

    def run(self):
        self._open_tcp_socket()

        while not self.stopped():
            readable, _, _ = select.select([self.socket], [], [], 0.01)

            if readable:
                try:
                    self._read_msg()
                except RuntimeError:
                    break

            if not send_queue.empty():
                try:
                    self._write_msg()
                except RuntimeError:
                    break

        self._close_tcp_socket()

    def _read_msg(self):
        header = ''
        while not header.endswith('\n'):
            chunk = self.socket.recv(1)
            if chunk == '':
                raise RuntimeError("socket connection broken")
            header += chunk

        data = ''
        length = int(header)
        while len(data) < length:
            chunk = self.socket.recv(1)
            if chunk == '':
                raise RuntimeError("socket connection broken")
            data += chunk

        obj = json.loads(data)
        recv_queue.put(obj)

    def _write_msg(self):
        data = json.dumps(send_queue.get())
        msg = str(len(data)) + '\n' + data
        msg_len = len(msg)

        totalsent = 0
        while totalsent < msg_len:
            sent = self.socket.send(msg[totalsent:])
            if sent == 0:
                raise RuntimeError("socket connection broken")
            totalsent = totalsent + sent

    def _open_tcp_socket(self):
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self._host, self._port))
        except:
            print "Can't connect. Is Zephyros running?"
            sys.exit(1) # TODO: This won't work, or does it?

    def _close_tcp_socket(self):
        self.socket.close()


class Dispatcher(StoppableThread):

    def __init__(self):
       super(Dispatcher, self).__init__()
       self.registered_msg_ids = {}

    def run(self):
        while not self.stopped():
            try:
                message = recv_queue.get(False)
            except Queue.Empty:
                time.sleep(0.01)
            else:
                self.dispatch_message(message)

        # Kill'em all!!! }:->
        workers = self.registered_msg_ids.itervalues()
        for worker in workers:
            worker.stop()
            worker.join()

    def register_msgid(self, msg_id, thread):
        self.registered_msg_ids[msg_id] = thread

    def unregister_msgid(self, msg_id):
        thread = self.registered_msg_ids.pop(msg_id)
        # TODO: Is this crazy?
        if thread.is_alive():
            thread.stop()
            thread.join()

    def dispatch_message(self, message):
        msg_id = message[0]
        # TODO: Handel missing msg_id's
        thread = self.registered_msg_ids[msg_id]
        thread.put_message(message)

class Worker(StoppableThread):

    def __init__(self, message, infinite=True, callback=None):
        super(Worker, self).__init__()
        self.message = message
        self.infinite = infinite
        self.callback = callback
        self.queue = Queue.Queue()

    def run(self):
        while not self.stopped():
            try:
                message = self.queue.get(False)
            except Queue.Empty:
                time.sleep(0.01)
            else:
                self.handle_message(message)

    def send_message(self):
        # compute a message id
        msg_id = str(uuid.uuid4())

        # add id to the message
        self.message.insert(0, msg_id)

        # Tell the dispatcher we want messages for msg_id
        dispatcher.register_msgid(msg_id, self)

        # Send message via the sending_queue
        send_queue.put(self.message)

        if self.callback:
            _ = self.queue.get()
            self.start()
            return None

        responce = self.queue.get()
        dispatcher.unregister_msgid(msg_id)
        return responce[1]

    def handle_message(self, message):
        if not self.infinite:
            self.stop()
        self.callback(message)

    def put_message(self, message):
        self.queue.put(message)


class Proxy(object):

    def __init__(self, id):
        self.id = id

    def _send_sync(self, *args):
        return self._send_message([self.id] + list(args))

    def _send_message(self, msg, infinite=True, callback=None):
        worker = Worker(msg, infinite=infinite, callback=callback)
        return worker.send_message()


class Rect(object):

    def to_dict(r):
        return {'x': r.x, 'y': r.y, 'w': r.w, 'h': r.h}

    def __init__(self, x=0, y=0, w=0, h=0):
        self.x = x
        self.y = y
        self.w = w
        self.h = h

    def inset(self, x, y):
        self.x += x
        self.y += y
        self.w -= (x * 2)
        self.h -= (y * 2)


class Point(object):

    def to_dict(r):
        return {'x': r.x, 'y': r.y}

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y


class Size(object):

    def __init__(self, w=0, h=0):
        self.w = w
        self.h = h

    def to_dict(r):
        return {'w': r.w, 'h': r.h}


class Window(Proxy):

    def title(self):
        return self._send_sync('title')

    def frame(self):
        return Rect(**self._send_sync('frame'))

    def top_left(self):
        return Point(**self._send_sync('top_left'))

    def size(self):
        return Size(**self._send_sync('size'))

    def set_frame(self, f):
        self._send_sync('set_frame', f.to_dict())

    def set_top_left(self, tl):
        return self._send_sync('set_top_left', tl.to_dict())

    def set_size(self, s):
        return self._send_sync('set_size', s.to_dict())

    def maximize(self):
        return self._send_sync('maximize')

    def minimize(self):
        return self._send_sync('minimize')

    def un_minimize(self):
        return self._send_sync('un_minimize')

    def app(self):
        return App(self._send_sync('app'))

    def screen(self):
        return Screen(self._send_sync('screen'))

    def focus_window(self):
        return self._send_sync('focus_window')

    def focus_window_left(self):
        return self._send_sync('focus_window_left')

    def focus_window_right(self):
        return self._send_sync('focus_window_right')

    def focus_window_up(self):
        return self._send_sync('focus_window_up')

    def focus_window_down(self):
        return self._send_sync('focus_window_down')

    def windows_to_north(self):
        return self._send_sync('windows_to_north')

    def windows_to_south(self):
        return self._send_sync('windows_to_south')

    def windows_to_east(self):
        return self._send_sync('windows_to_east')

    def windows_to_west(self):
        return self._send_sync('windows_to_west')

    def normal_window(self):
        return self._send_sync('normal_window?')

    def minimized(self):
        return self._send_sync('minimized?')

    def other_windows_on_same_screen(self):
        return [Window(x) for x in
                self._send_sync('other_windows_on_same_screen')]

    def other_windows_on_all_screens(self):
        return [Window(x) for x in
                self._send_sync('other_windows_on_all_screens')]


class Screen(Proxy):

    def frame_including_dock_and_menu(self):
        return Rect(**self._send_sync("frame_including_dock_and_menu"))

    def frame_without_dock_or_menu(self):
        return Rect(**self._send_sync("frame_without_dock_or_menu"))

    def previous_screen(self):
        return Screen(self._send_sync("previous_screen"))

    def next_screen(self):
        return Screen(self._send_sync("next_screen"))


class App(Proxy):

    def visible_windows(self):
        return [Window(x) for x in  self._send_sync("visible_windows")]

    def all_windows(self):
        return [Window(x) for x in  self._send_sync("all_windows")]

    def title(self):
        return self._send_sync("title")

    def hidden(self):
        return self._send_sync("hidden?")

    def show(self):
        return self._send_sync("show")

    def hide(self):
        return self._send_sync("hide")

    def kill(self):
        return self._send_sync("kill")

    def kill9(self):
        return self._send_sync("kill9")


class Api(Proxy):

    def alert(self, msg, duration=None):
        self._send_sync('alert', msg, duration)

    def log(self, msg):
        self._send_sync('log', msg)

    def unbind(self, key, mods):
        self._send_sync('unbind', key, mods)

    def update_settings(self, new_settings):
        self._send_sync('update_settings', new_settings)

    def relaunch_config(self):
        self._send_sync('relaunch_config')

    def clipboard_contents(self):
        return self._send_sync('clipboard_contents')

    def focused_window(self):
        return Window(self._send_sync('focused_window'))

    def visible_windows(self):
        return [Window(x) for x in  self._send_sync('visible_windows')]

    def all_windows(self):
        return [Window(x) for x in  self._send_sync('all_windows')]

    def main_screen(self):
        return Screen(self._send_sync('main_screen'))

    def all_screens(self):
        return [Screen(x) for x in  self._send_sync('all_screens')]

    def running_apps(self):
        return [App(x) for x in  self._send_sync('running_apps')]

    def bind(self, key, mods, fn):
        def tmp_fn(obj):
            fn()
        self._send_message([0, 'bind', key, mods], callback=tmp_fn)

    def choose_from(self, lst, title, lines, chars, fn):
        self._send_message([0, 'choose_from', lst, title, lines, chars],
                callback=fn, infinite=False)

    def listen(self, event, fn):
        def tmp_fn(obj):
            if   event == "window_created":     fn(Window(obj))
            elif event == "window_minimized":   fn(Window(obj))
            elif event == "window_unminimized": fn(Window(obj))
            elif event == "window_moved":       fn(Window(obj))
            elif event == "window_resized":     fn(Window(obj))
            elif event == "app_launched":       fn(App(obj))
            elif event == "app_died":           fn(App(obj))
            elif event == "app_hidden":         fn(App(obj))
            elif event == "app_shown":          fn(App(obj))
            elif event == "screens_changed":    fn()
        self._send_message([0, 'listen', event], callback=tmp_fn)


# The decorator function
def zephyros(configuration):

    def signal_handler(signal, frame):
        #logging.debug('SIGTERM caught!')
        listener.stop()
        listener.join()
        dispatcher.stop()
        dispatcher.join()
        sys.exit(0)

    configuration()
    signal.signal(signal.SIGTERM, signal_handler)
    signal.pause()

#import logging
#import itertools
#logging.basicConfig(filename='example.log',level=logging.DEBUG)

recv_queue = Queue.Queue(10)
send_queue = Queue.Queue(10)

listener = Listener()
listener.start()

dispatcher = Dispatcher()
dispatcher.start()

api = Api(None)

