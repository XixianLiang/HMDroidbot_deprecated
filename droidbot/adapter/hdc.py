# This is the interface for hdc
import subprocess
import logging
import re
from .adapter import Adapter
import time
import os
import pathlib
try:
    from shlex import quote # Python 3
except ImportError:
    from pipes import quote # Python 2

class HDCException(Exception):
    """
    Exception in HDC connection
    """
    pass


class HDC(Adapter):
    """
    interface of HDC
    """
    HDC_EXEC = "hdc.exe"
    # TODO don't know what's this
    UP = 0
    DOWN = 1
    DOWN_AND_UP = 2
    MODEL_PROPERTY = "ro.product.model"
    VERSION_SDK_PROPERTY = 'ro.build.version.sdk'
    VERSION_RELEASE_PROPERTY = 'ro.build.version.release'
    RO_SECURE_PROPERTY = 'ro.secure'
    RO_DEBUGGABLE_PROPERTY = 'ro.debuggable'

    def __init__(self, device=None):
        """
        initiate a HDC connection from serial no
        the serial no should be in output of `hdc devices`
        :param device: instance of Device
        :return:
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        if device is None:
            from droidbot.device import Device
            device = Device()
        self.device = device

        self.cmd_prefix = [self.HDC_EXEC, "-t", device.serial]

    
    def set_up(self):
        # make the temp path in output dir to store the dumped layout result
        temp_path = os.getcwd() + "/" + self.device.output_dir + "/temp"
        if os.path.exists(temp_path):
            import shutil
            shutil.rmtree(temp_path)
        os.mkdir(temp_path)

    def tear_down(self):
        pass
        # temp_path = os.getcwd() + "/" + self.device.output_dir + "/temp"
        # if os.path.exists(temp_path):
        #     import shutil
        #     shutil.rmtree(temp_path)


    def run_cmd(self, extra_args):
        """
        run a hdc command and return the output
        :return: output of hdc command
        @param extra_args: arguments to run in hdc
        """
        if isinstance(extra_args, str):
            extra_args = extra_args.split()
        if not isinstance(extra_args, list):
            msg = "invalid arguments: %s\nshould be list or str, %s given" % (extra_args, type(extra_args))
            self.logger.warning(msg)
            raise HDCException(msg)

        args = ["hdc.exe"]
        # args = [] + self.cmd_prefix    TODO 写到有设备号的时候用这一行
        args += extra_args

        self.logger.debug('command:')
        self.logger.debug(args)
        r = subprocess.check_output(args).strip()
        if not isinstance(r, str):
            r = r.decode()
        self.logger.debug('return:')
        self.logger.debug(r)
        return r


    def shell(self, extra_args):
        """
        run an `hdc shell` command
        @param extra_args:
        @return: output of hdc shell command
        """
        if isinstance(extra_args, str):
            extra_args = extra_args.split()
        if not isinstance(extra_args, list):
            msg = "invalid arguments: %s\nshould be list or str, %s given" % (extra_args, type(extra_args))
            self.logger.warning(msg)
            raise HDCException(msg)

        shell_extra_args = ['shell'] + [ quote(arg) for arg in extra_args ]
        return self.run_cmd(shell_extra_args)

    def check_connectivity(self):
        """
        check if hdc is connected
        :return: True for connected
        """
        #TODO not support this method
        r = self.run_cmd("list targets")
        return not r.startswith("[Empty]")

    def connect(self):
        """
        connect hdc
        """
        self.logger.debug("connected")

    def disconnect(self):
        """
        disconnect hdc
        """
        print("[CONNECTION] %s is disconnected" % self.__class__.__name__)

    def get_property(self, property_name):
        """
        get the value of property
        @param property_name:
        @return:
        """
        return self.shell(["getprop", property_name])

    def get_model_number(self):
        """
        Get device model number. e.g. SM-G935F
        """
        return self.get_property(HDC.MODEL_PROPERTY)

    def get_sdk_version(self):
        """
        Get version of SDK, e.g. 18, 20
        """
        return int(self.get_property(HDC.VERSION_SDK_PROPERTY))

    def get_release_version(self):
        """
        Get release version, e.g. 4.3, 6.0
        """
        return self.get_property(HDC.VERSION_RELEASE_PROPERTY)

    def get_ro_secure(self):
        """
        get ro.secure value
        @return: 0/1
        """
        return int(self.get_property(HDC.RO_SECURE_PROPERTY))

    def get_ro_debuggable(self):
        """
        get ro.debuggable value
        @return: 0/1
        """
        return int(self.get_property(HDC.RO_DEBUGGABLE_PROPERTY))

    # The following methods are originally from androidviewclient project.
    # https://github.com/dtmilano/AndroidViewClient.
    def get_display_info(self):
        """
        Gets C{mDefaultViewport} and then C{deviceWidth} and C{deviceHeight} values from dumpsys.
        This is a method to obtain display dimensions and density
        """
        display_info = {}
        logical_display_re = re.compile(".*DisplayViewport{valid=true, .*orientation=(?P<orientation>\d+),"
                                        " .*deviceWidth=(?P<width>\d+), deviceHeight=(?P<height>\d+).*")
        dumpsys_display_result = self.shell("dumpsys display")
        if dumpsys_display_result is not None:
            for line in dumpsys_display_result.splitlines():
                m = logical_display_re.search(line, 0)
                if m:
                    for prop in ['width', 'height', 'orientation']:
                        display_info[prop] = int(m.group(prop))

        if 'width' not in display_info or 'height' not in display_info:
            physical_display_re = re.compile('Physical size: (?P<width>\d+)x(?P<height>\d+)')
            m = physical_display_re.search(self.shell('wm size'))
            if m:
                for prop in ['width', 'height']:
                    display_info[prop] = int(m.group(prop))

        if 'width' not in display_info or 'height' not in display_info:
            # This could also be mSystem or mOverscanScreen
            display_re = re.compile('\s*mUnrestrictedScreen=\((?P<x>\d+),(?P<y>\d+)\) (?P<width>\d+)x(?P<height>\d+)')
            # This is known to work on older versions (i.e. API 10) where mrestrictedScreen is not available
            display_width_height_re = re.compile('\s*DisplayWidth=(?P<width>\d+) *DisplayHeight=(?P<height>\d+)')
            for line in self.shell('dumpsys window').splitlines():
                m = display_re.search(line, 0)
                if not m:
                    m = display_width_height_re.search(line, 0)
                if m:
                    for prop in ['width', 'height']:
                        display_info[prop] = int(m.group(prop))

        if 'orientation' not in display_info:
            surface_orientation_re = re.compile("SurfaceOrientation:\s+(\d+)")
            output = self.shell("dumpsys input")
            m = surface_orientation_re.search(output)
            if m:
                display_info['orientation'] = int(m.group(1))

        density = None
        float_re = re.compile(r"[-+]?\d*\.\d+|\d+")
        d = self.get_property('ro.sf.lcd_density')
        if float_re.match(d):
            density = float(d)
        else:
            d = self.get_property('qemu.sf.lcd_density')
            if float_re.match(d):
                density = float(d)
            else:
                physical_density_re = re.compile('Physical density: (?P<density>[\d.]+)', re.MULTILINE)
                m = physical_density_re.search(self.shell('wm density'))
                if m:
                    density = float(m.group('density'))
        if density is not None:
            display_info['density'] = density

        display_info_keys = {'width', 'height', 'orientation', 'density'}
        if not display_info_keys.issuperset(display_info):
            self.logger.warning("getDisplayInfo failed to get: %s" % display_info_keys)

        return display_info

    def get_enabled_accessibility_services(self):
        """
        Get enabled accessibility services
        :return: the enabled service names, each service name is in <package_name>/<service_name> format
        """
        r = self.shell("settings get secure enabled_accessibility_services")
        r = re.sub(r'(?m)^WARNING:.*\n?', '', r)
        return r.strip().split(":") if r.strip() != '' else []

    def disable_accessibility_service(self, service_name):
        """
        Disable an accessibility service
        :param service_name: the service to disable, in <package_name>/<service_name> format
        """
        service_names = self.get_enabled_accessibility_services()
        if service_name in service_names:
            service_names.remove(service_name)
            self.shell("settings put secure enabled_accessibility_services %s" % ":".join(service_names))

    def enable_accessibility_service(self, service_name):
        """
        Enable an accessibility service
        :param service_name: the service to enable, in <package_name>/<service_name> format
        """
        service_names = self.get_enabled_accessibility_services()
        if service_name not in service_names:
            service_names.append(service_name)
            self.shell("settings put secure enabled_accessibility_services %s" % ":".join(service_names))
        self.shell("settings put secure accessibility_enabled 1")

    def enable_accessibility_service_db(self, service_name):
        """
        Enable an accessibility service
        :param service_name: the service to enable, in <package_name>/<service_name> format
        """
        subprocess.check_call(
            "adb shell \""
            "sqlite3 -batch /data/data/com.android.providers.settings/databases/settings.db \\\""
            "DELETE FROM secure WHERE name='enabled_accessibility_services' OR name='accessibility_enabled' "
            "OR name='touch_exploration_granted_accessibility_services' OR name='touch_exploration_enabled';"
            "INSERT INTO secure (name, value) VALUES "
            "('enabled_accessibility_services','" + service_name + "'), "
            "('accessibility_enabled','1'), "
            "('touch_exploration_granted_accessibility_services','" + service_name + "'), "
            "('touch_exploration_enabled','1')\\\";\"", shell=True)
        self.shell("stop")
        time.sleep(1)
        self.shell("start")

    def get_installed_apps(self):
        """
        Get the package names and apk paths of installed apps on the device
        :return: a dict, each key is a package name of an app and each value is the file path to the apk
        """
        app_lines = self.shell("bm dump -a").splitlines()
        installed_bundle = []
        for app_line in app_lines:
            installed_bundle.append(app_line.strip())
        return installed_bundle

    def get_display_density(self):
        display_info = self.get_display_info()
        if 'density' in display_info:
            return display_info['density']
        else:
            return -1.0

    def __transform_point_by_orientation(self, xy, orientation_orig, orientation_dest):
        (x, y) = xy
        if orientation_orig != orientation_dest:
            if orientation_dest == 1:
                _x = x
                x = self.get_display_info()['width'] - y
                y = _x
            elif orientation_dest == 3:
                _x = x
                x = y
                y = self.get_display_info()['height'] - _x
        return x, y

    def get_orientation(self):
        display_info = self.get_display_info()
        if 'orientation' in display_info:
            return display_info['orientation']
        else:
            return -1

    def unlock(self):
        """
        Unlock the screen of the device
        """
        self.shell("uitest uiInput keyEvent Home")
        self.shell("uitest uiInput keyEvent Back")

    def press(self, key_code):
        """
        Press a key
        """
        self.shell("uitest uiInput keyEvent %s" % key_code)

    def touch(self, x, y, orientation=-1, event_type=DOWN_AND_UP):
        if orientation == -1:
            orientation = self.get_orientation()
        self.shell("uitest uiInput click %d %d" %
                   self.__transform_point_by_orientation((x, y), orientation, self.get_orientation()))

    def long_touch(self, x, y, duration=2000, orientation=-1):
        """
        Long touches at (x, y)
        """
        if orientation == -1:
            orientation = self.get_orientation()
        self.shell("uitest uiInput longClick %d %d" %
                   self.__transform_point_by_orientation((x, y), orientation, self.get_orientation()))

    def drag(self, start_xy, end_xy, duration, orientation=-1):
        """
        Sends drag event n PX (actually it's using C{input swipe} command.
        @param start_xy: starting point in pixel
        @param end_xy: ending point in pixel
        @param duration: duration of the event in ms
        @param orientation: the orientation (-1: undefined)
        """
        (x0, y0) = start_xy
        (x1, y1) = end_xy
        if orientation == -1:
            orientation = self.get_orientation()
        (x0, y0) = self.__transform_point_by_orientation((x0, y0), orientation, self.get_orientation())
        (x1, y1) = self.__transform_point_by_orientation((x1, y1), orientation, self.get_orientation())

        self.shell("uitest uiInput swipe %d %d %d %d %d" % (x0, y0, x1, y1, duration))
        
    def type(self, text):
        # TODO 华为的 inputText 不太一样
        # hdc shell uitest uiInput inputText 100 100 hello
        if isinstance(text, str):
            escaped = text.replace("%s", "\\%s")
            encoded = escaped.replace(" ", "%s")
        else:
            encoded = str(text)
        # TODO find out which characters can be dangerous, and handle non-English characters
        self.shell("input text %s" % encoded)

    """
    TODO 从这行开始是我加的东西
    """
    @staticmethod
    def __safe_dict_get(view_dict, key, default=None):
        value = view_dict[key] if key in view_dict else None
        return value if value is not None else default
    
    @staticmethod
    def get_relative_path(absolute_path:str) -> str:
        """
        return the relative path in win style
        """
        workspace = pathlib.Path(os.getcwd())
        relative_path = pathlib.PureWindowsPath(pathlib.Path(absolute_path).relative_to(workspace))
        return relative_path
    
    def dump_view(self)->str:
        """
        Using uitest to dumpLayout, and return the remote path of the layout file
        :Return: remote path
        """
        r = self.shell("uitest dumpLayout")
        remote_path = r.split(":")[-1]
        return remote_path

    # def dump_views(self):
    #     """
    #     dump layout and recv the layout from the device
    #     """
    #     r = self.shell("uitest dumpLayout")
    #     remote_path = r.split(":")[-1]
    #     file_name = os.path.basename(remote_path)
    #     temp_path = os.path.join(self.device.output_dir, "temp")
    #     local_path = os.path.join(os.getcwd(), temp_path, file_name)

    #     p = "file recv {} {}".format(remote_path, HDC.get_relative_path(local_path))

    #     r2 = self.run_cmd("file recv {} {}".format(remote_path, HDC.get_relative_path(local_path)))
    #     assert not r2.startswith("[Fail]"), "Error with receiving dump layout"

    #     with open(local_path, "r") as f:
    #         import json
    #         raw_views = json.load(f)
    #     # print(r)
    #     return raw_views


    def get_views(self, views_path):
        """
        bfs the view tree and turn it into the android style
        views list
        ### :param: view path
        """
        from collections import deque
        self.views = []


        with open(views_path, "r") as f:
            import json
            self.views_raw = json.load(f)

        # process the root node
        self.views_raw["attributes"]["parent"] = -1

        # add it into a queue to bfs
        queue = deque([self.views_raw])
        temp_id = 0

        while queue:
            node:dict = queue.popleft()

            # process the node and add some attribute which Droidbot can
            # recongnize while traversing
            node["attributes"]["temp_id"] = temp_id
            node["attributes"]["child_count"] = len(node["children"])
            node["attributes"]["children"] = list()

            # process the view, turn it into android style and add to view list
            self.views.append(self.get_adb_view(node["attributes"]))

            # bfs the tree
            for child in node["children"]:
                child["attributes"]["parent"] = temp_id
                if "bundleName" in node["attributes"]:
                    child["attributes"]["bundleName"] = HDC.__safe_dict_get(node["attributes"], "bundleName")
                queue.append(child)
            
            temp_id += 1
        
        # get the 'children' attributes
        self.get_view_children()

        return self.views
        
    def get_view_children(self):
        """
        get the 'children' attributes by the 'parent'
        """
        for view in self.views:
            temp_id = HDC.__safe_dict_get(view, "parent")
            if temp_id > -1:
                self.views[temp_id]["children"].append(view["temp_id"])
                assert self.views[temp_id]["temp_id"] == temp_id
    
    def get_adb_view(self, raw_view:dict):
        """
        process the view and turn it into the android style
        """
        view = dict()
        for key, value in raw_view.items():
            # adapt the attributes into adb form
            if key in ["visible", "checkable", "enabled", "clickable", \
                       "scrollable", "selected", "focused", "checked"]:
                view[key] = True if value in ["True", "true"] else False
                continue
            if key == "longClickable":
                view["long_clickable"] = bool(value)
                continue
            if key == "bounds":
                view[key] = self.get_bounds(value)
                view["size"] = self.get_size(value)
                continue
            if key == "bundleName":
                view["package"] = value
                continue
            if key == "description":
                view["content_description"] = value
                continue
            if key == "type":
                view["class"] = value
                continue
            view[key] = value
    
        return view
    
    def get_bounds(self, raw_bounds:str):
        # capturing the coordinate of the bounds and return 2-dimensional list
        # e.g.  "[10,20][30,40]" -->  [[10, 20], [30, 40]]
        import re
        size_pattern = r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]"
        match = re.search(size_pattern, raw_bounds)
        if match:
            return [[int(match.group(1)), int(match.group(2))], \
                    [int(match.group(3)), int(match.group(4))]]
    
    def get_size(self, raw_bounds:str):
        bounds = self.get_bounds(raw_bounds)
        return f"{bounds[1][0]-bounds[0][0]}*{bounds[1][1]-bounds[0][1]}"