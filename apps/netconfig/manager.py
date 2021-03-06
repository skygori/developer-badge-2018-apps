import machine
import network
import time

import ugfx

import util

from home.launcher import ButtonGroup, Button, Display


class ConfigManager(Display):

    def __init__(self, parent=None):
        self.parent = parent
        super().__init__()

    def reload(self):
        if self.parent:
            self.parent.reload()
        else:
            self.destroy()
            self.main()

    def kb_handler(self, keycode):
        if keycode == 13: # GKEY_ENTER
            text = self.kb_input.text()
            self.kb.destroy()
            self.kb_input.destroy()
            self.kb_callback(text)

    def get_input(self, label, callback):
        ugfx.input_attach(ugfx.BTN_B, util.reboot)
        w = self.create_window()
        edit_size = 40
        ugfx.Textbox(5, 0, w.width() - 12, edit_size, text=label, parent=w).enabled(False)
        self.kb_input = ugfx.Textbox(5, 7 + edit_size, w.width() - 12, edit_size, parent=w)
        self.kb = ugfx.Keyboard(5, edit_size * 2 + 12, w.width() - 12, w.height() - edit_size * 2 - 20, parent=w)
        self.kb_callback = callback
        self.kb.set_keyboard_callback(self.kb_handler)

    def get_status(self, interface):
        for stat in dir(network):
            if stat.startswith('STAT_'):
                if getattr(network, stat) == interface.status():
                    return stat.replace('STAT_', '')

    def teardown(self, pressed=True):
        if pressed and self.window and self.window.enabled() != 0:
            self.window.hide()
            self.window.destroy()
            ugfx.poll()


class WifiConfig(ConfigManager):

    def __init__(self, parent=None):
        self.sta_if = network.WLAN(network.STA_IF)
        self.ap_if = network.WLAN(network.AP_IF)
        self.saved_config = None
        super().__init__(parent)

    def scan(self):
        if not self.sta_if.active():
            self.sta_if.active(True)
        self.create_status_box()
        self.set_status('Scanning..')
        self.scan_configs = self.sta_if.scan()
        self.close_status_box()

    def connect_network(self, ssid, pw=None, timeout=15):
        self.create_window()
        self.window.text(10, 10, 'Connecting to {}'.format(ssid), ugfx.BLACK)
        if not self.sta_if.active():
            self.sta_if.active(True)
        else:
            self.sta_if.active(False)
            time.sleep(0.3)
            self.sta_if.active(True)
        self.create_status_box()
        self.sta_if.connect(ssid, pw)
        tried = 0
        while self.get_status(self.sta_if) != 'GOT_IP' and tried < timeout:
            self.set_status(self.get_status(self.sta_if))
            time.sleep(0.2)
            tried += 0.2
        if self.get_status(self.sta_if) == 'GOT_IP':
            self.set_status('Connected!')
            config = util.Config('network')
            config['sta_if'] = {
                'ssid': ssid,
                'password': pw,
            }
            config.save()
            time.sleep(1)
            self.set_status('Network configuration saved.')
            time.sleep(1)
            util.reboot()
        else:
            self.set_status('Connection failed.')

    def network_selected(self, pressed):
        if not pressed:
            return

        scan_config = self.scan_configs[self.scan_list.selected_index()]
        self.saved_config = scan_config
        ugfx.input_attach(ugfx.BTN_A, None)
        self.scan_list.destroy()
        if scan_config[4] == 0:
            self.connect_network(scan_config[0].decode('utf-8'))
        else:
            self.get_password()

    def list_network(self):
        w = self.create_window()
        self.scan()

        self.scan_list = ugfx.List(10, 10, w.width() - 20, w.height() - 20, parent = w)
        self.scan_list.visible(False)
        for scan_config in self.scan_configs:
            ap_name = '{} {}'.format(
                '@' if scan_config[4] else ' ',
                scan_config[0].decode('utf-8')
            )
            self.scan_list.add_item(ap_name)
            print(scan_config)
        self.scan_list.visible(True)

        ugfx.input_attach(ugfx.BTN_A, self.network_selected)
        ugfx.input_attach(ugfx.BTN_B, util.reboot)

    def pw_callback(self, pw):
        self.connect_network(self.saved_config[0].decode('utf-8'), pw)

    def get_password(self):
        self.get_input('Input password', self.pw_callback)


class WebreplConfig(ConfigManager):

    CONFIG = '/webrepl_cfg.py'

    def pw_callback(self, passwd):
        with open(self.CONFIG, "w") as f:
            f.write("PASS = %r\n" % passwd)
        self.create_window()
        self.create_status_box()
        self.set_status('Webrepl password saved.')
        time.sleep(1)
        util.reboot()

    def main(self):
        ugfx.input_attach(ugfx.BTN_A, None)
        self.get_input('New password (4-9 chars)', self.pw_callback)


class Status(Display):

    menus = ['WiFi', 'Webrepl']

    def title(self):
        self.window.text(60, 20, 'Network config', ugfx.HTML2COLOR(0x01d7dd))

    def main(self):
        self.create_window()
        self.title()
        self.btngroup = ButtonGroup(self.window, 80, 110, 140, 40, 10)
        self.widgets.append(self.btngroup)
        sta_if = network.WLAN(network.STA_IF)
        ugfx.Label(40, 60, 240, 30, text=sta_if.ifconfig()[0], parent=self.window)

        for menu in self.menus:
            self.btngroup.add(menu, getattr(self, menu))
        self.btngroup.end()

    def WiFi(self, data=None):
        self.destroy()
        m = WifiConfig(self)
        m.list_network()

    def Webrepl(self, data=None):
        self.destroy()
        w = WebreplConfig(self)
        w.main()
