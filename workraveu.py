#!/usr/bin/python3

import ConfigParser
import os.path
import math
import time
import datetime

import appindicator
import pynotify
import gtk
import gobject
import signal

from lock import lock_screen

class WorkRaveUnity:
    STATE_WORKING = 0
    STATE_BREAK = 1
    STATE_CLOSE = 4

    SECOND = 1000

    def main(self):
        self.config_init()
        self.indicators_init()
        self.reset_timer()
        gtk.main()

    #
    # Configurations and commons
    #

    def config_init(self):
        self.config = ConfigParser.RawConfigParser()
        self.config_dir = os.path.expanduser("~/.workrave-unity")
        self.file = os.path.realpath(self.config_dir + "/settings.ini")
        if (not os.path.isdir(self.config_dir)):
            os.makedirs(self.config_dir)

        if (os.path.isfile(self.file)):
            self.config.read(self.file)
        else:
            self.config.add_section("Micro-break")
            self.config.add_section("Application")
            self.config.add_section("Logging")
            self.config_default()
            self.config_save(self.file)
        self.count = int(self.config.get("Micro-break", "work-mintes")) * 60

    def config_default(self):
        self.config.set("Micro-break", "work-mintes", '45')
        self.config.set("Micro-break", "postpone-mintes", '5')
        self.config.set("Micro-break", "break-mintes", '10')
        self.config.set("Application", "version", '0.1')
        self.config.set("Logging", "log-time", 'True')
        self.config.set("Logging", "log-dir", '/log/%Y/%Y-%m-%d.log')

    def config_save(self, file=None):
        if (file is None):
            file = self.file
        with open(file, 'wb+') as configfile:
            self.config.write(configfile)

    def date_to_string(self, seconds):
        if (seconds > 60):
            return "%d min %d s." % (math.floor(seconds / 60), seconds%60)
        else:
            return "%d s." % seconds
        #TODO: mins min, hours

    def quit(self, widget=None, args=None):
        self.config_save()
        self.change_state(self.STATE_CLOSE)
        gtk.main_quit()

    def change_state(self, state):
        self.state = state
        self.log_state(state)

    def log_state(self, state):
        if (self.config.get("Logging", "log-time") == "True"):
            now = datetime.datetime.now()
            log_file = self.config_dir + now.strftime(
                                         self.config.get("Logging", "log-dir"))
            log_dir = os.path.dirname(log_file)
            if (not os.path.isdir(log_dir)):
                os.makedirs(log_dir)
            file = open(log_file, 'a')
            time = now.strftime("%Y-%m-%d %H:%M:%S")
            if (state == self.STATE_CLOSE):
                file.write(time + " Closing\n")
            elif (state == self.STATE_WORKING):
                file.write(time + " Working\n")
            else:
                file.write(time + " Break\n")
            file.close()

    #
    # Indicators and GUI
    #

    def indicators_init(self):
        pynotify.init ("workraveu")             #TODO: capbilities - pynotify.get_server_caps()
        #~ self.launcher = Unity.LauncherEntry.get_for_desktop_id(
                                            #~ "workraveu.desktop")

        current_dir = os.path.dirname(os.path.realpath(__file__))
        self.resources_dir = current_dir + "/res";
        default_icon = self.resources_dir + "/icon-16.png"
        self.indicator = appindicator.Indicator ("workraveu", default_icon,
                                      appindicator.CATEGORY_APPLICATION_STATUS)

        menu = gtk.Menu()
        self.menu_timer = gtk.MenuItem("Starting timer")
        self.menu_timer.connect_object('activate', self.force_break, None)
        self.menu_timer.show()
        menu.append(self.menu_timer)
        self.indicator.set_menu(menu)


    #
    # Working (counting to next break)
    #

    def reset_timer(self, timer=0, renewTimer=True):
        self.timer = timer
        self.break_timer = 0
        self.change_state(self.STATE_WORKING)
        if (renewTimer):
            self.timer_id = gobject.timeout_add(self.SECOND, self.timer_update)

    def timer_update(self):
        if (self.state != self.STATE_WORKING):
            return False

        if (self.timer == None):
            self.timer = 1
        else:
            self.timer += 1
        self.menu_timer.set_label("Till next break: %s" %
                                  self.date_to_string(self.count - self.timer));

        if (self.timer == self.count):
            self.force_break()
            return False

        return True

    def force_break(self, widget=None, args=None):
        print "hello"
        now = datetime.datetime.now()
        log_file = self.config_dir + now.strftime(
                self.config.get("Logging", "log-dir"))
        log_dir = os.path.dirname(log_file)
        if (not os.path.isdir(log_dir)):
            os.makedirs(log_dir)

        lock_screen(log_file, int(self.config.get("Micro-break", "break-mintes")) * 60)

        reset_timer()


if __name__ == "__main__":
    base = WorkRaveUnity()
    try:
        base.main()
    except KeyboardInterrupt:
        base.change_state(base.STATE_CLOSE)
