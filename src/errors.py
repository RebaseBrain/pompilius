from constants import DBUS_NAME

class CloudError:
    REQWEST = f"{DBUS_NAME}.Error.Reqwest"
    PARSE = f"{DBUS_NAME}.Error.Parse"
    RCLONE = f"{DBUS_NAME}.Error.Rclone"
    CONVERT = f"{DBUS_NAME}.Error.Convert"
    IO = f"{DBUS_NAME}.Error.IO"
