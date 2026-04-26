"""
MS_Setup.pyw

A small Tkinter setup tool for Microsoft Flight Simulator 2024 configuration files.

This script is intentionally a single file. It uses only Python's built-in
standard library modules, so there is nothing to install with pip.

Important safety rule used throughout the program:
    Before this script writes an options/configuration file, it first creates a
    numbered backup next to that file. It never deletes the original config file.
"""

import configparser
import os
import shutil
import tkinter as tk
import xml.etree.ElementTree as ET

from pathlib import Path
from tkinter import messagebox
from tkinter import ttk


# The script is expected to live in the Flight Simulator 2024 configuration
# folder. Using the script's own folder makes the program work even if the user
# starts it from a shortcut whose working directory is somewhere else.
APP_DIR = Path(__file__).resolve().parent

# Names of the files this program knows how to edit.
USERCFG_FILE = APP_DIR / "UserCfg.opt"
SIMCFG_FILE = APP_DIR / "FlightSimulator2024.CFG"
DEVMODE_FILE = APP_DIR / "DevMode.xml"

# A readable text encoding is not declared by the simulator files. UTF-8 works
# for the current files and also handles ordinary ASCII-only config data.
TEXT_ENCODING = "utf-8"


class OptLine:
    """
    A single parsed line from UserCfg.opt.

    UserCfg.opt is not JSON, INI, or XML. It is a brace-based text format:

        {Graphics
            {Terrain
                LoDFactor 1.400000
            }
        }

    This class stores enough information to update known setting lines while
    keeping the original order, indentation, and unrelated lines untouched.
    """

    def __init__(self, raw_text, path_parts, key, value_text):
        # raw_text is the line exactly as it appeared in the file, without the
        # newline character. If a line is not a setting, raw_text is still kept.
        self.raw_text = raw_text

        # path_parts is a tuple such as ("Graphics", "Terrain"). It tells us
        # which brace sections the setting belongs to.
        self.path_parts = path_parts

        # key is the setting name on this line, for example "LoDFactor".
        self.key = key

        # value_text is everything after the key, for example "1.400000".
        self.value_text = value_text


class UserCfgDocument:
    """
    Line-preserving reader/writer for UserCfg.opt.

    The goal is not to understand every possible simulator option. The goal is
    to safely change known values and write the rest of the file back exactly as
    it was.
    """

    def __init__(self, file_path):
        self.file_path = Path(file_path)
        self.lines = []
        self.newline = "\n"
        self.load()

    def load(self):
        """Read and parse the file, keeping all original lines in memory."""
        if not self.file_path.exists():
            self.lines = []
            return

        raw_data = self.file_path.read_text(encoding=TEXT_ENCODING)

        # Keep the original newline style when possible.
        if "\r\n" in raw_data:
            self.newline = "\r\n"
        else:
            self.newline = "\n"

        active_path = []
        parsed_lines = []

        for raw_line in raw_data.splitlines():
            stripped = raw_line.strip()

            # Opening section line, for example "{Graphics".
            if stripped.startswith("{") and not stripped == "{":
                section_name = stripped[1:].strip()
                parsed_lines.append(OptLine(raw_line, tuple(active_path), None, None))
                active_path.append(section_name)
                continue

            # Closing section line.
            if stripped == "}":
                parsed_lines.append(OptLine(raw_line, tuple(active_path), None, None))
                if active_path:
                    active_path.pop()
                continue

            # Normal setting line. It is normally "Key Value", and the value may
            # contain spaces if it is quoted, so split only once.
            if stripped:
                parts = stripped.split(None, 1)
                key = parts[0]
                value_text = parts[1] if len(parts) > 1 else ""
                parsed_lines.append(OptLine(raw_line, tuple(active_path), key, value_text))
                continue

            # Blank lines are preserved.
            parsed_lines.append(OptLine(raw_line, tuple(active_path), None, None))

        self.lines = parsed_lines

    def get(self, path_text, key, default_value=""):
        """Return a setting value as text, or default_value when not found."""
        wanted_path = tuple(path_text.split("/")) if path_text else tuple()
        for line in self.lines:
            if line.path_parts == wanted_path and line.key == key:
                return line.value_text
        return default_value

    def set(self, path_text, key, new_value):
        """
        Change a setting line in memory.

        The exact indentation from the existing line is preserved. Missing
        settings are deliberately not added, because adding unknown simulator
        syntax in the wrong section could be more dangerous than useful.
        """
        wanted_path = tuple(path_text.split("/")) if path_text else tuple()
        new_value = str(new_value)

        for line in self.lines:
            if line.path_parts == wanted_path and line.key == key:
                indentation = line.raw_text[:len(line.raw_text) - len(line.raw_text.lstrip())]
                line.value_text = new_value
                line.raw_text = indentation + key + " " + new_value
                return True

        return False

    def save(self):
        """Write all lines back to the original file."""
        text = self.newline.join(line.raw_text for line in self.lines) + self.newline
        self.file_path.write_text(text, encoding=TEXT_ENCODING)


def numbered_backup_path(file_path):
    """
    Return the next numbered backup path for a file.

    Example:
        UserCfg.opt.backup_001
        UserCfg.opt.backup_002

    Existing backups are never overwritten.
    """
    file_path = Path(file_path)
    number = 1

    while True:
        candidate = file_path.with_name(file_path.name + ".backup_" + str(number).zfill(3))
        if not candidate.exists():
            return candidate
        number += 1


def make_backup(file_path):
    """
    Copy file_path to the next numbered backup.

    If the target file does not exist, there is nothing to back up. The function
    returns None in that case.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return None

    backup_path = numbered_backup_path(file_path)
    shutil.copy2(file_path, backup_path)
    return backup_path


def bool_text_to_int(value):
    """Convert a Tkinter BooleanVar value into the simulator's 0/1 text."""
    if value:
        return "1"
    return "0"


def int_text(value):
    """Return an integer setting as text."""
    return str(int(float(value)))


def float_text(value, digits=6):
    """Return a float setting using the simulator's usual six decimal places."""
    return ("{:." + str(digits) + "f}").format(float(value))


class ScrollableFrame(ttk.Frame):
    """
    A simple scrollable frame made from a Canvas plus a child Frame.

    Tkinter does not provide a ready-made scrollable frame widget, so this small
    class keeps the rest of the UI code cleaner.
    """

    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)

        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)

        self.inner.bind("<Configure>", self._update_scroll_region)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Configure>", self._resize_inner_frame)

        # Mouse wheel support is bound only while the pointer is over this
        # scrollable frame. That way the wheel scrolls the active tab content
        # instead of unexpectedly affecting another part of the program.
        self.canvas.bind("<Enter>", self._bind_mouse_wheel)
        self.canvas.bind("<Leave>", self._unbind_mouse_wheel)
        self.inner.bind("<Enter>", self._bind_mouse_wheel)
        self.inner.bind("<Leave>", self._unbind_mouse_wheel)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

    def _update_scroll_region(self, event):
        """Tell the canvas how large the scrollable content is."""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _resize_inner_frame(self, event):
        """Make the inner frame as wide as the canvas viewport."""
        self.canvas.itemconfigure(self.window_id, width=event.width)

    def _bind_mouse_wheel(self, event):
        """Enable mouse wheel scrolling while the pointer is over this tab."""
        self.canvas.bind_all("<MouseWheel>", self._on_mouse_wheel)
        self.canvas.bind_all("<Button-4>", self._on_mouse_wheel)
        self.canvas.bind_all("<Button-5>", self._on_mouse_wheel)

    def _unbind_mouse_wheel(self, event):
        """Disable mouse wheel scrolling after the pointer leaves this tab."""
        self.canvas.unbind_all("<MouseWheel>")
        self.canvas.unbind_all("<Button-4>")
        self.canvas.unbind_all("<Button-5>")

    def _on_mouse_wheel(self, event):
        """Scroll the canvas from Windows/macOS or Linux wheel events."""
        if event.num == 4:
            scroll_units = -1
        elif event.num == 5:
            scroll_units = 1
        else:
            scroll_units = int(-1 * (event.delta / 120))

        self.canvas.yview_scroll(scroll_units, "units")


class SettingRow:
    """
    Description of one editable setting.

    file_kind chooses the parser:
        "opt"     -> UserCfg.opt
        "ini"     -> FlightSimulator2024.CFG
        "devxml"  -> DevMode.xml
    """

    def __init__(self, group, label, file_kind, path, key, control, choices, minimum,
                 maximum, explanation, formatter):
        self.group = group
        self.label = label
        self.file_kind = file_kind
        self.path = path
        self.key = key
        self.control = control
        self.choices = choices
        self.minimum = minimum
        self.maximum = maximum
        self.explanation = explanation
        self.formatter = formatter


class SetupApp(tk.Tk):
    """The main Tkinter window and all application behavior."""

    def __init__(self):
        tk.Tk.__init__(self)

        self.title("Microsoft Flight Simulator 2024 Setup")
        self.geometry("980x720")
        self.minsize(860, 600)

        # Tkinter variables are stored by "file|path|key". That keeps saving
        # straightforward and avoids one variable name per setting.
        self.variables = {}

        # Build the data model first, then load current file values into it.
        self.settings = self._build_setting_list()
        self.usercfg = UserCfgDocument(USERCFG_FILE)
        self.simcfg = self._load_simcfg()
        self.devmode_tree = self._load_devmode_xml()

        self._build_style()
        self._build_window()
        self._load_values_into_controls()

    def _build_style(self):
        """Set a quiet, readable Tk theme."""
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Help.TLabel", foreground="#444444", wraplength=440)
        style.configure("Status.TLabel", foreground="#1f5f2a")
        style.configure("Danger.TLabel", foreground="#8a1f11")

    def _load_simcfg(self):
        """Load FlightSimulator2024.CFG using Python's INI parser."""
        parser = configparser.ConfigParser()
        parser.optionxform = str
        if SIMCFG_FILE.exists():
            parser.read(SIMCFG_FILE, encoding=TEXT_ENCODING)
        return parser

    def _load_devmode_xml(self):
        """Load DevMode.xml, or return None when it is missing or invalid."""
        if not DEVMODE_FILE.exists():
            return None

        try:
            return ET.parse(DEVMODE_FILE)
        except ET.ParseError:
            return None

    def _build_setting_list(self):
        """
        Define the clickable settings shown in the tabs.

        These are common, useful settings from the current config files. The
        program keeps unknown settings intact but does not show them as editable
        controls.
        """
        settings = []

        # Video tab.
        settings.append(SettingRow("Video", "Display Mode", "opt", "Video", "Windowed",
                                   "choice", [("Fullscreen / borderless", "0"), ("Windowed", "1")],
                                   None, None,
                                   "Controls the simulator's Windowed flag. Use it together with Borderless Fullscreen for fullscreen-style or windowed startup.",
                                   str))
        settings.append(SettingRow("Video", "Borderless Fullscreen", "opt", "Video", "FullscreenBorderless",
                                   "bool", None, None, None,
                                   "Uses a borderless fullscreen window. This is usually smooth for alt-tab use.",
                                   bool_text_to_int))
        settings.append(SettingRow("Video", "V-Sync", "opt", "Video", "VSync",
                                   "bool", None, None, None,
                                   "Synchronizes frames to the monitor refresh. It can reduce tearing but may add latency.",
                                   bool_text_to_int))
        settings.append(SettingRow("Video", "Frame Limiter", "opt", "Video", "FrameLimiter",
                                   "spin", None, 20, 120,
                                   "Caps real rendered frames before any frame generation. Lower caps can reduce heat, power use, and unnecessary frames.",
                                   int_text))
        settings.append(SettingRow("Video", "Target Frame Rate", "opt", "Video", "TargetFrameRate",
                                   "spin", None, 10, 120,
                                   "Target used by Dynamic Settings. The simulator can reduce LOD and other load to try to hold this frame rate.",
                                   int_text))
        settings.append(SettingRow("Video", "NVIDIA Reflex", "opt", "Video", "Reflex",
                                   "choice", [("Off", "OFF"), ("On", "ON"), ("On + Boost", "ON_BOOST")],
                                   None, None,
                                   "Reduces render latency on supported NVIDIA GPUs.",
                                   str))
        settings.append(SettingRow("Video", "Anti-Aliasing", "opt", "Video", "AntiAliasing",
                                   "choice", [("TAA", "TAA"), ("DLSS", "DLSS"), ("FXAA", "FXAA"), ("Off", "NONE")],
                                   None, None,
                                   "Controls edge smoothing. TAA is the common compatibility choice; DLSS uses NVIDIA upscaling.",
                                   str))
        settings.append(SettingRow("Video", "DLSS Mode", "opt", "Video", "DLSSMode",
                                   "choice", [("Auto", "AUTO"), ("Quality", "QUALITY"), ("Balanced", "BALANCED"),
                                              ("Performance", "PERFORMANCE"), ("Ultra Performance", "ULTRA_PERFORMANCE"),
                                              ("DLAA", "DLAA"), ("Off", "OFF")],
                                   None, None,
                                   "Controls DLSS super-resolution mode when DLSS anti-aliasing is used. DLAA keeps native resolution and applies DLSS anti-aliasing.",
                                   str))
        settings.append(SettingRow("Video", "Frame Generation", "opt", "Video", "FrameGeneration",
                                   "choice", [("None", "NONE"), ("DLSS Frame Generation", "DLSSG"),
                                              ("AMD FSR3 Frame Generation", "FSRFG")],
                                   None, None,
                                   "Enables generated frames on supported GPUs. It can make motion smoother but may add latency; FSR3 has had some MSFS 2024 beta issues with DevMode and multi-monitor setups.",
                                   str))
        settings.append(SettingRow("Video", "HDR10", "opt", "Video", "HDR10",
                                   "bool", None, None, None,
                                   "Enables HDR output when Windows and the display support it.",
                                   bool_text_to_int))
        settings.append(SettingRow("Video", "Primary Scaling", "opt", "Video", "PrimaryScaling",
                                   "scale", None, 0.3, 2.0,
                                   "Main render scale. 1.000000 is 100 percent; lower values reduce GPU load and higher values improve clarity at a performance cost.",
                                   float_text))
        settings.append(SettingRow("Video", "Sharpen Amount", "opt", "Video", "SharpenAmount",
                                   "scale", None, 0.0, 2.0,
                                   "Post-process sharpening. Too much can create bright edges and grain.",
                                   float_text))

        # Graphics tab.
        settings.append(SettingRow("Graphics", "Graphics Preset", "opt", "Graphics", "Preset",
                                   "choice", [("Low", "Low"), ("Medium", "Medium"), ("High", "High"),
                                              ("Ultra", "Ultra"), ("Custom", "Custom")],
                                   None, None,
                                   "Overall graphics preset label. Changing individual values usually leaves this as Custom.",
                                   str))
        settings.append(SettingRow("Graphics", "Texture Quality", "opt", "Graphics/Texture", "Quality",
                                   "texture_quality", None, 0, 3,
                                   "Texture resolution/detail and VRAM use. This setting is reversed in UserCfg.opt: 0 is Ultra, 1 is High, 2 is Medium, and 3 is Low.",
                                   int_text))
        settings.append(SettingRow("Graphics", "Anisotropic Filtering", "opt", "Graphics/Texture", "MaxAnisotropy",
                                   "choice", [("Off", "0"), ("2x", "2"), ("4x", "4"), ("8x", "8"), ("16x", "16")],
                                   None, None,
                                   "Improves runway and ground texture clarity at shallow viewing angles.",
                                   str))
        settings.append(SettingRow("Graphics", "Terrain Level of Detail", "opt", "Graphics/Terrain", "LoDFactor",
                                   "scale", None, 0.5, 4.0,
                                   "Distance/detail for terrain and terrain mesh. This can strongly affect CPU load.",
                                   float_text))
        settings.append(SettingRow("Graphics", "Objects Level of Detail", "opt", "Graphics/ObjectsLoD", "LoDFactor",
                                   "scale", None, 0.5, 4.0,
                                   "Distance/detail for buildings, objects, and airport scenery.",
                                   float_text))
        settings.append(SettingRow("Graphics", "Offscreen Terrain Pre-Caching", "opt", "Graphics/OffscreenTerrainPreCaching", "Quality",
                                   "quality", None, 0, 3,
                                   "Keeps terrain outside the current view ready. Higher can reduce pop-in during turns.",
                                   int_text))
        settings.append(SettingRow("Graphics", "Cloud Quality", "opt", "Graphics/VolumetricClouds", "Quality",
                                   "quality", None, 0, 3,
                                   "Volumetric cloud quality. This is often one of the heavier GPU settings.",
                                   int_text))
        settings.append(SettingRow("Graphics", "Shadow Map Size", "opt", "Graphics/Shadows", "Size",
                                   "choice", [("768", "768"), ("1024", "1024"), ("1536", "1536"), ("2048", "2048")],
                                   None, None,
                                   "Resolution used for main shadows. Higher looks cleaner and costs GPU memory/performance.",
                                   str))
        settings.append(SettingRow("Graphics", "Contact Shadows", "opt", "Graphics/ContactShadows", "Enabled",
                                   "bool", None, None, None,
                                   "Small nearby shadows under aircraft parts, vehicles, and scenery objects.",
                                   bool_text_to_int))
        settings.append(SettingRow("Graphics", "Screen Space Reflections", "opt", "Graphics/SSR", "Enabled",
                                   "bool", None, None, None,
                                   "Adds reflections from visible screen content. Useful for water and shiny surfaces.",
                                   bool_text_to_int))
        settings.append(SettingRow("Graphics", "Ambient Occlusion", "opt", "Graphics/SSAO", "Enabled",
                                   "bool", None, None, None,
                                   "Adds small contact shading in corners and creases.",
                                   bool_text_to_int))
        settings.append(SettingRow("Graphics", "Motion Blur", "opt", "Graphics/MotionBlur", "Enabled",
                                   "bool", None, None, None,
                                   "Blurs camera/object motion. Many sim users prefer it off for readability.",
                                   bool_text_to_int))
        settings.append(SettingRow("Graphics", "Depth of Field", "opt", "Graphics/DOF", "Enabled",
                                   "bool", None, None, None,
                                   "Camera focus blur effect. Mostly visual and often disabled for cockpit clarity.",
                                   bool_text_to_int))
        settings.append(SettingRow("Graphics", "Building Quality", "opt", "Graphics/Buildings", "Quality",
                                   "quality", None, 0, 3,
                                   "Complexity and quality of rendered buildings.",
                                   int_text))
        settings.append(SettingRow("Graphics", "Trees Quality", "opt", "Graphics/Procedural", "TreesQuality",
                                   "quality", None, 0, 3,
                                   "Quality/density of procedural trees.",
                                   int_text))
        settings.append(SettingRow("Graphics", "Glass Cockpit Refresh", "opt", "Graphics/GlassCockpitsRefreshRate", "Quality",
                                   "quality", None, 0, 2,
                                   "Refresh rate of glass cockpit displays. Higher is smoother and costs CPU/GPU time.",
                                   int_text))

        # Traffic and world tab.
        traffic_path = "Graphics/Traffic"
        settings.append(SettingRow("Traffic", "Aircraft Traffic Quantity", "opt", traffic_path, "AircraftTrafficQuantity",
                                   "traffic", None, -1, 3,
                                   "AI/live aircraft amount. Off can improve performance at busy airports.",
                                   int_text))
        settings.append(SettingRow("Traffic", "Parked Aircraft Quantity", "opt", traffic_path, "ParkedAircraftQuantity",
                                   "traffic", None, -1, 3,
                                   "Number of parked aircraft around airports.",
                                   int_text))
        settings.append(SettingRow("Traffic", "Airport Services Quantity", "opt", traffic_path, "AirportsServicesQuantity",
                                   "traffic", None, -1, 3,
                                   "Ground vehicles and service activity at airports.",
                                   int_text))
        settings.append(SettingRow("Traffic", "Road Traffic", "opt", traffic_path, "RoadQuality",
                                   "road_sea_traffic", None, -1, 3,
                                   "Road vehicle traffic amount/quality. The in-game presets commonly show Off, Medium, High, and Ultra.",
                                   int_text))
        settings.append(SettingRow("Traffic", "Sea Traffic", "opt", traffic_path, "SeaQuality",
                                   "road_sea_traffic", None, -1, 3,
                                   "Boat and ship traffic amount/quality. The in-game presets commonly show Off, Medium, High, and Ultra.",
                                   int_text))
        settings.append(SettingRow("Traffic", "Fauna Quantity", "opt", "Graphics/Fauna", "Quantity",
                                   "traffic", None, -1, 3,
                                   "Wildlife amount where supported.",
                                   int_text))
        settings.append(SettingRow("Traffic", "Seatbelts Visuals", "opt", "Graphics/Seatbelts", "Enabled",
                                   "bool", None, None, None,
                                   "Toggles the simulator's Seatbelts graphics-section option. The exact visual effect can depend on aircraft/content.",
                                   bool_text_to_int))

        # VR tab.
        settings.append(SettingRow("VR", "VR Preset", "opt", "GraphicsVR", "Preset",
                                   "choice", [("Low", "VRLow"), ("Medium", "VRMedium"), ("High", "VRHigh"),
                                              ("Ultra", "VRUltra"), ("Custom", "Custom")],
                                   None, None,
                                   "Overall VR graphics preset label.",
                                   str))
        settings.append(SettingRow("VR", "VR Terrain LOD", "opt", "GraphicsVR/Terrain", "LoDFactor",
                                   "scale", None, 0.2, 2.0,
                                   "Terrain detail in VR. Lower values are often needed for stable VR frame timing.",
                                   float_text))
        settings.append(SettingRow("VR", "VR Objects LOD", "opt", "GraphicsVR/ObjectsLoD", "LoDFactor",
                                   "scale", None, 0.2, 2.0,
                                   "Object/scenery detail distance in VR.",
                                   float_text))
        settings.append(SettingRow("VR", "VR Primary Scaling", "opt", "Video", "PrimaryScalingVR",
                                   "scale", None, 0.4, 1.5,
                                   "VR render scale. 1.000000 is 100 percent; higher improves clarity and costs performance.",
                                   float_text))
        settings.append(SettingRow("VR", "VR Cloud Quality", "opt", "GraphicsVR/VolumetricClouds", "Quality",
                                   "quality", None, 0, 3,
                                   "Cloud quality while in VR.",
                                   int_text))
        settings.append(SettingRow("VR", "VR Frame Generation", "opt", "Video", "FrameGenerationVR",
                                   "choice", [("None", "NONE"), ("DLSS Frame Generation", "DLSSG"),
                                              ("AMD FSR3 Frame Generation", "FSRFG")],
                                   None, None,
                                   "Generated frames for VR if supported by the simulator and GPU.",
                                   str))

        # Simulator UI and assistance options from FlightSimulator2024.CFG.
        settings.append(SettingRow("Simulator", "Wide View Aspect", "ini", "Display", "WideViewAspect",
                                   "bool", None, None, None,
                                   "Wider camera projection intended for very wide displays.",
                                   bool_text_to_int))
        settings.append(SettingRow("Simulator", "Info: Brakes", "ini", "Display", "InfoBrakesEnable",
                                   "bool", None, None, None,
                                   "Shows brake status text.",
                                   bool_text_to_int))
        settings.append(SettingRow("Simulator", "Info: Parking Brakes", "ini", "Display", "InfoParkingBrakesEnable",
                                   "bool", None, None, None,
                                   "Shows parking brake status text.",
                                   bool_text_to_int))
        settings.append(SettingRow("Simulator", "Info: Pause", "ini", "Display", "InfoPauseEnable",
                                   "bool", None, None, None,
                                   "Shows pause status text.",
                                   bool_text_to_int))
        settings.append(SettingRow("Simulator", "Info: Stall", "ini", "Display", "InfoStallEnable",
                                   "bool", None, None, None,
                                   "Shows stall warning text.",
                                   bool_text_to_int))
        settings.append(SettingRow("Simulator", "Info: Overspeed", "ini", "Display", "InfoOverspeedEnable",
                                   "bool", None, None, None,
                                   "Shows overspeed warning text.",
                                   bool_text_to_int))
        settings.append(SettingRow("Simulator", "Dynamic Head Movement", "ini", "DynamicHeadMovement", "MaxHeadAngle",
                                   "scale", None, 0.0, 10.0,
                                   "Maximum head tilt from acceleration. Set lower if cockpit movement bothers you.",
                                   float_text))
        settings.append(SettingRow("Simulator", "Virtual Copilot", "ini", "VirtualCopilot", "VirtualCopilotActive",
                                   "bool", None, None, None,
                                   "Stores the simulator's Virtual Copilot active flag. Assistance behavior is still controlled by the simulator's assistance options.",
                                   bool_text_to_int))
        settings.append(SettingRow("Simulator", "Map Orientation", "ini", "UserInterface", "Map_Orientation",
                                   "choice", [("North Up", "0"), ("Track Up", "1"), ("Default / Saved", "2")],
                                   None, None,
                                   "Stored map orientation value from the simulator UI. Exact labels can vary by simulator screen, so keep your current value if unsure.",
                                   str))

        # Developer mode XML options.
        settings.append(SettingRow("Developer", "DevMode Toolbar Visible", "devxml", "General", "Devmode_Toolbar_Visibility",
                                   "bool", None, None, None,
                                   "Shows or hides the developer toolbar.",
                                   bool_text_to_int))
        settings.append(SettingRow("Developer", "DevMode Bar Auto-Hide", "devxml", "General", "DevMode_Bar_Auto_Hide",
                                   "bool", None, None, None,
                                   "Auto-hides the developer toolbar.",
                                   bool_text_to_int))
        settings.append(SettingRow("Developer", "Capture DevMode Inputs", "devxml", "Options", "Capture devmode inputs",
                                   "bool", None, None, None,
                                   "Keeps keyboard/mouse inputs captured by developer mode tools when enabled.",
                                   bool_text_to_int))
        settings.append(SettingRow("Developer", "Disable Crashes", "devxml", "Options", "Disable Crashes",
                                   "bool", None, None, None,
                                   "Developer-mode option that disables crash behavior.",
                                   bool_text_to_int))
        settings.append(SettingRow("Developer", "WASM Debug Mode", "devxml", "Options", "Wasm Debug Mode",
                                   "bool", None, None, None,
                                   "Compiles WASM modules in debug mode for easier debugging and faster compile time, usually with lower runtime performance.",
                                   bool_text_to_int))

        return settings

    def _build_window(self):
        """Create the top-level layout, tabs, buttons, and status line."""
        main = ttk.Frame(self, padding=12)
        main.pack(fill="both", expand=True)

        title = ttk.Label(main, text="Microsoft Flight Simulator 2024 Setup", style="Header.TLabel")
        title.pack(anchor="w")

        folder_label = ttk.Label(main, text="Config folder: " + str(APP_DIR))
        folder_label.pack(anchor="w", pady=(2, 10))

        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill="both", expand=True)

        for group_name in ("Video", "Graphics", "Traffic", "VR", "Simulator", "Developer", "Backups"):
            if group_name == "Backups":
                self._build_backup_tab(group_name)
            else:
                self._build_settings_tab(group_name)

        button_row = ttk.Frame(main)
        button_row.pack(fill="x", pady=(10, 0))

        ttk.Button(button_row, text="Reload From Files", command=self.reload_from_files).pack(side="left")
        ttk.Button(button_row, text="Create Backups Now", command=self.create_manual_backups).pack(side="left", padx=(8, 0))
        ttk.Button(button_row, text="Save Changes", command=self.save_changes).pack(side="right")

        self.status_var = tk.StringVar(value="Ready. Nothing has been changed yet.")
        ttk.Label(main, textvariable=self.status_var, style="Status.TLabel").pack(anchor="w", pady=(8, 0))

    def _build_settings_tab(self, group_name):
        """Create one notebook tab full of clickable setting controls."""
        frame = ScrollableFrame(self.notebook)
        self.notebook.add(frame, text=group_name)

        intro = ttk.Label(frame.inner, text=self._group_intro(group_name), style="Help.TLabel")
        intro.grid(row=0, column=0, columnspan=3, sticky="ew", padx=10, pady=(10, 14))

        frame.inner.columnconfigure(1, weight=1)
        row_number = 1

        for setting in self.settings:
            if setting.group != group_name:
                continue

            label = ttk.Label(frame.inner, text=setting.label)
            label.grid(row=row_number, column=0, sticky="w", padx=10, pady=8)

            variable_key = self._variable_key(setting)
            variable = self._create_variable(setting)
            self.variables[variable_key] = variable

            control = self._create_control(frame.inner, setting, variable)
            control.grid(row=row_number, column=1, sticky="ew", padx=10, pady=8)

            help_label = ttk.Label(frame.inner, text=setting.explanation, style="Help.TLabel")
            help_label.grid(row=row_number, column=2, sticky="w", padx=10, pady=8)

            row_number += 1

    def _build_backup_tab(self, group_name):
        """Create a simple tab that explains and lists backup behavior."""
        frame = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(frame, text=group_name)

        text = (
            "Backups are always created before saving. The script writes numbered files next to the "
            "original files, for example UserCfg.opt.backup_001. Existing backups are never overwritten. "
            "This tab can also create backups manually without changing settings."
        )
        ttk.Label(frame, text=text, style="Help.TLabel", wraplength=820).pack(anchor="w", pady=(0, 12))

        ttk.Button(frame, text="Create Backups Now", command=self.create_manual_backups).pack(anchor="w")

        self.backup_list = tk.Listbox(frame, height=18)
        self.backup_list.pack(fill="both", expand=True, pady=(12, 0))

        ttk.Button(frame, text="Refresh Backup List", command=self.refresh_backup_list).pack(anchor="w", pady=(10, 0))
        self.refresh_backup_list()

    def _group_intro(self, group_name):
        """Return short explanatory text for a tab."""
        intros = {
            "Video": "Display, sync, scaling, latency, and frame-rate options from UserCfg.opt.",
            "Graphics": "Main non-VR graphics quality options. Higher values usually improve visuals and cost performance.",
            "Traffic": "World density settings. These can affect CPU load around airports and cities.",
            "VR": "VR-specific graphics and video values. VR usually needs lower settings than flat-screen flying.",
            "Simulator": "General simulator interface and assistance options from FlightSimulator2024.CFG.",
            "Developer": "Developer-mode options from DevMode.xml.",
        }
        return intros.get(group_name, "")

    def _create_variable(self, setting):
        """Choose the right Tkinter variable type for a setting."""
        if setting.control == "bool":
            return tk.BooleanVar()
        return tk.StringVar()

    def _create_control(self, parent, setting, variable):
        """Create a clickable control for one setting."""
        if setting.control == "bool":
            return ttk.Checkbutton(parent, variable=variable)

        if setting.control in ("choice", "quality", "texture_quality", "traffic", "road_sea_traffic"):
            choices = setting.choices
            if setting.control == "quality":
                choices = [("Low", "0"), ("Medium", "1"), ("High", "2"), ("Ultra", "3")]
                if setting.maximum == 2:
                    choices = [("Low", "0"), ("Medium", "1"), ("High", "2")]
            if setting.control == "texture_quality":
                choices = [("Ultra", "0"), ("High", "1"), ("Medium", "2"), ("Low", "3")]
            if setting.control == "traffic":
                choices = [("Off", "-1"), ("Low", "0"), ("Medium", "1"), ("High", "2"), ("Ultra", "3")]
            if setting.control == "road_sea_traffic":
                choices = [("Off", "-1"), ("Medium", "1"), ("High", "2"), ("Ultra", "3")]

            combo = ttk.Combobox(parent, textvariable=variable, state="readonly",
                                 values=[label + "  (" + value + ")" for label, value in choices])
            combo.choice_pairs = choices
            combo.bind("<<ComboboxSelected>>", self._on_combo_selected)
            return combo

        if setting.control == "spin":
            return ttk.Spinbox(parent, textvariable=variable, from_=setting.minimum,
                               to=setting.maximum, increment=1, width=10)

        if setting.control == "scale":
            holder = ttk.Frame(parent)
            holder.columnconfigure(0, weight=1)

            scale = ttk.Scale(holder, from_=setting.minimum, to=setting.maximum,
                              orient="horizontal", command=lambda value, var=variable: var.set(float_text(value)))
            scale.grid(row=0, column=0, sticky="ew")

            entry = ttk.Entry(holder, textvariable=variable, width=10)
            entry.grid(row=0, column=1, sticky="e", padx=(8, 0))

            variable.trace_add("write", lambda name, index, mode, sc=scale, var=variable: self._sync_scale(sc, var))
            return holder

        return ttk.Entry(parent, textvariable=variable)

    def _on_combo_selected(self, event):
        """
        Store only the actual config value when a friendly combobox row is picked.

        The combobox displays "High  (2)" but the config file should receive
        just "2".
        """
        combo = event.widget
        selected = combo.get()
        for label, value in combo.choice_pairs:
            if selected == label + "  (" + value + ")":
                combo.set(value)
                break

    def _sync_scale(self, scale, variable):
        """Keep a slider position in sync when the adjacent text value changes."""
        try:
            scale.set(float(variable.get()))
        except (tk.TclError, ValueError):
            pass

    def _variable_key(self, setting):
        """Build a stable dictionary key for one setting variable."""
        return setting.file_kind + "|" + setting.path + "|" + setting.key

    def _load_values_into_controls(self):
        """Read current file values and place them into all UI controls."""
        for setting in self.settings:
            variable = self.variables[self._variable_key(setting)]
            value = self._read_setting_value(setting)

            if setting.control == "bool":
                variable.set(str(value).strip() in ("1", "true", "True", "YES", "yes"))
            else:
                variable.set(str(value))

        self.status_var.set("Loaded current settings from disk.")

    def _read_setting_value(self, setting):
        """Read one setting from the correct backing document."""
        if setting.file_kind == "opt":
            return self.usercfg.get(setting.path, setting.key, "")

        if setting.file_kind == "ini":
            if self.simcfg.has_section(setting.path) and self.simcfg.has_option(setting.path, setting.key):
                return self.simcfg.get(setting.path, setting.key)
            return ""

        if setting.file_kind == "devxml":
            element = self._find_devmode_element(setting.path, setting.key)
            if element is not None:
                return element.get("value", "")
            return ""

        return ""

    def _find_devmode_element(self, section_name, setting_name):
        """Find a Setting or Option node in DevMode.xml."""
        if self.devmode_tree is None:
            return None

        root = self.devmode_tree.getroot()
        section = root.find(section_name)
        if section is None:
            return None

        for child in section:
            if child.get("name") == setting_name:
                return child
        return None

    def reload_from_files(self):
        """Discard unsaved UI changes and reload current values from disk."""
        self.usercfg = UserCfgDocument(USERCFG_FILE)
        self.simcfg = self._load_simcfg()
        self.devmode_tree = self._load_devmode_xml()
        self._load_values_into_controls()
        self.refresh_backup_list()

    def create_manual_backups(self):
        """Create backups of all known config files without editing them."""
        created = []
        for file_path in (USERCFG_FILE, SIMCFG_FILE, DEVMODE_FILE):
            backup_path = make_backup(file_path)
            if backup_path is not None:
                created.append(backup_path.name)

        self.refresh_backup_list()

        if created:
            self.status_var.set("Created backups: " + ", ".join(created))
            messagebox.showinfo("Backups Created", "Created:\n\n" + "\n".join(created))
        else:
            self.status_var.set("No known config files were found to back up.")
            messagebox.showwarning("No Files", "No known config files were found to back up.")

    def refresh_backup_list(self):
        """Refresh the backup list shown on the Backups tab."""
        if not hasattr(self, "backup_list"):
            return

        self.backup_list.delete(0, tk.END)

        names = []
        for file_path in (USERCFG_FILE, SIMCFG_FILE, DEVMODE_FILE):
            pattern = file_path.name + ".backup_*"
            for backup in sorted(APP_DIR.glob(pattern)):
                names.append(backup.name)

        if not names:
            self.backup_list.insert(tk.END, "No backups found yet.")
            return

        for name in sorted(names):
            self.backup_list.insert(tk.END, name)

    def save_changes(self):
        """
        Validate values, create backups, then save all changed files.

        For simplicity and safety, this saves the known files after creating
        backups. It does not try to delete, rename, or clean up any simulator
        files.
        """
        try:
            self._apply_controls_to_documents()
        except ValueError as error:
            messagebox.showerror("Invalid Value", str(error))
            self.status_var.set("Save stopped because a value is invalid.")
            return

        backup_paths = []
        for file_path in (USERCFG_FILE, SIMCFG_FILE, DEVMODE_FILE):
            if file_path.exists():
                backup_path = make_backup(file_path)
                if backup_path is not None:
                    backup_paths.append(backup_path.name)

        try:
            if USERCFG_FILE.exists():
                self.usercfg.save()

            if SIMCFG_FILE.exists():
                with SIMCFG_FILE.open("w", encoding=TEXT_ENCODING) as handle:
                    self.simcfg.write(handle, space_around_delimiters=False)

            if DEVMODE_FILE.exists() and self.devmode_tree is not None:
                self.devmode_tree.write(DEVMODE_FILE, encoding=TEXT_ENCODING,
                                        xml_declaration=False, short_empty_elements=True)

        except OSError as error:
            messagebox.showerror("Save Failed", "Could not save settings:\n\n" + str(error))
            self.status_var.set("Save failed. Backups were created before the write attempt.")
            return

        self.refresh_backup_list()
        self.status_var.set("Saved settings. Backups created: " + ", ".join(backup_paths))
        messagebox.showinfo("Saved", "Settings saved.\n\nBackups created:\n" + "\n".join(backup_paths))

    def _apply_controls_to_documents(self):
        """Move values from Tkinter variables into the three document objects."""
        for setting in self.settings:
            variable = self.variables[self._variable_key(setting)]

            if setting.control == "bool":
                value = setting.formatter(variable.get())
            else:
                value = variable.get().strip()

                # Sliders and spinboxes are validated here so a bad typed value
                # cannot be written to a simulator file.
                if setting.control in ("scale", "spin"):
                    numeric = float(value)
                    if numeric < float(setting.minimum) or numeric > float(setting.maximum):
                        raise ValueError(setting.label + " must be between " +
                                         str(setting.minimum) + " and " + str(setting.maximum) + ".")
                    value = setting.formatter(value)
                elif setting.control in ("quality", "texture_quality", "traffic", "road_sea_traffic"):
                    value = int_text(value)
                else:
                    value = setting.formatter(value)

            self._write_setting_value(setting, value)

    def _write_setting_value(self, setting, value):
        """Write one setting to the correct backing document."""
        if setting.file_kind == "opt":
            self.usercfg.set(setting.path, setting.key, value)
            return

        if setting.file_kind == "ini":
            if not self.simcfg.has_section(setting.path):
                self.simcfg.add_section(setting.path)
            self.simcfg.set(setting.path, setting.key, value)
            return

        if setting.file_kind == "devxml":
            element = self._find_devmode_element(setting.path, setting.key)
            if element is not None:
                element.set("value", value)


def main():
    """Program entry point."""
    app = SetupApp()
    app.mainloop()


if __name__ == "__main__":
    main()
