"""Read Windows connection status without probing websites or reading credentials."""
import ctypes
from ctypes import wintypes
import os
from core.diagnostics import failure

def wifi_status() -> str:
    if os.name != 'nt':
        return 'N/A'
    class Interface(ctypes.Structure):
        _fields_ = [('guid', ctypes.c_ubyte * 16), ('description', ctypes.c_wchar * 256), ('state', wintypes.DWORD)]
    wlan = ctypes.WinDLL('wlanapi')
    wlan.WlanOpenHandle.argtypes = [wintypes.DWORD, ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.HANDLE)]
    wlan.WlanEnumInterfaces.argtypes = [wintypes.HANDLE, ctypes.c_void_p, ctypes.POINTER(ctypes.c_void_p)]
    wlan.WlanFreeMemory.argtypes = [ctypes.c_void_p]
    wlan.WlanCloseHandle.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    handle, version, pointer = wintypes.HANDLE(), wintypes.DWORD(), ctypes.c_void_p()
    if wlan.WlanOpenHandle(2, None, ctypes.byref(version), ctypes.byref(handle)):
        return 'N/A'
    try:
        if wlan.WlanEnumInterfaces(handle, None, ctypes.byref(pointer)) or not pointer.value:
            return 'N/A'
        count = ctypes.cast(pointer, ctypes.POINTER(wintypes.DWORD))[0]
        if not count:
            return 'N/A'
        interfaces = ctypes.cast(pointer.value + 8, ctypes.POINTER(Interface))
        return 'Connected' if any(interfaces[i].state == 1 for i in range(min(count, 64))) else 'Disconnected'
    finally:
        if pointer.value:
            wlan.WlanFreeMemory(pointer)
        wlan.WlanCloseHandle(handle, None)

def connection_status() -> dict:
    result = {'internet': 'N/A', 'wifi': 'N/A'}
    try:
        import pythoncom
        import win32com.client
        pythoncom.CoInitialize()
        try:
            manager = win32com.client.Dispatch('{DCB00C01-570F-4A9B-8D69-199FDBA5723B}')
            result['internet'] = 'ONLINE' if manager.IsConnectedToInternet else 'OFFLINE'
        finally:
            pythoncom.CoUninitialize()
    except Exception as exc:
        failure('network-status', exc)
    try:
        result['wifi'] = wifi_status()
    except Exception as exc:
        failure('wifi-status', exc)
    return result

def byte_rates(previous, current, elapsed: float) -> tuple[float | None, float | None]:
    if previous is None or current is None or elapsed <= 0:
        return None, None
    return (max(0, current.bytes_recv - previous.bytes_recv) / elapsed,
            max(0, current.bytes_sent - previous.bytes_sent) / elapsed)
