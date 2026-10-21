"""Focuseur ZWO EAF par le SDK de ZWO (libEAFFocuser.so), sur le modèle de zwocaa.py.

Le SDK numérote les appareils par index (0, 1…) mais les pilote par un identifiant
obtenu avec EAFGetID. EAFMove envoie à une position absolue, en pas.
"""
import ctypes
import os

_lib = None
_PATHS = ("/usr/lib/x86_64-linux-gnu/libEAFFocuser.so", "/usr/lib/libEAFFocuser.so",
          "/usr/local/lib/libEAFFocuser.so", os.path.expanduser("~/ASIStudio/lib/libEAFFocuser.so"))


def _load():
    global _lib
    if _lib is not None:
        return _lib
    try:
        ctypes.CDLL("libudev.so.1", mode=ctypes.RTLD_GLOBAL)
    except OSError:
        pass
    path = next((p for p in _PATHS if os.path.exists(p)), None)
    if path is None:
        raise ImportError("libEAFFocuser.so introuvable : installez le SDK ZWO EAF")
    lib = ctypes.CDLL(path)
    pint = ctypes.POINTER(ctypes.c_int)
    lib.EAFGetNum.restype = ctypes.c_int
    for name, args in (("EAFGetID", [ctypes.c_int, pint]), ("EAFOpen", [ctypes.c_int]),
                       ("EAFClose", [ctypes.c_int]), ("EAFMove", [ctypes.c_int, ctypes.c_int]),
                       ("EAFStop", [ctypes.c_int]), ("EAFGetPosition", [ctypes.c_int, pint]),
                       ("EAFGetMaxStep", [ctypes.c_int, pint]),
                       ("EAFIsMoving", [ctypes.c_int, ctypes.POINTER(ctypes.c_bool), ctypes.POINTER(ctypes.c_bool)]),
                       ("EAFGetTemp", [ctypes.c_int, ctypes.POINTER(ctypes.c_float)])):
        f = getattr(lib, name)
        f.argtypes = args
        f.restype = ctypes.c_int
    _lib = lib
    return lib


class EAF:
    def __init__(self, index=0):
        self.lib = _load()
        self.index = index
        self.id = -1

    @staticmethod
    def count():
        return _load().EAFGetNum()

    def _check(self, err, what):
        if err != 0:
            raise RuntimeError(f"{what} : erreur EAF {err}")

    def open(self):
        if self.lib.EAFGetNum() <= self.index:
            raise RuntimeError("Aucun focuseur ZWO EAF détecté")
        i = ctypes.c_int()
        self._check(self.lib.EAFGetID(self.index, ctypes.byref(i)), "EAFGetID")
        self.id = i.value
        self._check(self.lib.EAFOpen(self.id), "EAFOpen")

    def close(self):
        if self.id >= 0:
            self.lib.EAFClose(self.id)
            self.id = -1

    def position(self):
        v = ctypes.c_int()
        self._check(self.lib.EAFGetPosition(self.id, ctypes.byref(v)), "EAFGetPosition")
        return v.value

    def max_step(self):
        v = ctypes.c_int()
        self._check(self.lib.EAFGetMaxStep(self.id, ctypes.byref(v)), "EAFGetMaxStep")
        return v.value

    def move_to(self, step):
        self._check(self.lib.EAFMove(self.id, int(step)), "EAFMove")

    def stop(self):
        self._check(self.lib.EAFStop(self.id), "EAFStop")

    def is_moving(self):
        moving, hand = ctypes.c_bool(), ctypes.c_bool()
        self._check(self.lib.EAFIsMoving(self.id, ctypes.byref(moving), ctypes.byref(hand)), "EAFIsMoving")
        return moving.value

    def temperature(self):
        """Température en °C, ou None (sans sonde, le SDK renvoie -273)."""
        t = ctypes.c_float()
        if self.lib.EAFGetTemp(self.id, ctypes.byref(t)) != 0 or t.value < -270:
            return None
        return t.value
