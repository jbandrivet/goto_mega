import ctypes
import os
import sys

# Charger libudev en mode global d'abord
try:
    ctypes.CDLL('libudev.so.1', mode=ctypes.RTLD_GLOBAL)
except Exception:
    pass

caa_lib = None
for path in ['/home/jean-baptiste/ASIStudio/lib/libCAA.so', '/usr/lib/libCAA.so', '/usr/local/lib/libCAA.so']:
    if os.path.exists(path):
        try:
            caa_lib = ctypes.CDLL(path)
            break
        except Exception as e:
            print("Erreur chargement", path, ":", e)
            pass

if caa_lib is None:
    raise ImportError("Impossible de trouver libCAA.so. Assurez-vous que le SDK ZWO CAA est installé.")

# Définition des types
CAA_ERROR_CODE = ctypes.c_int

# ... (rest is same)
caa_lib.CAAGetNum.restype = ctypes.c_int
caa_lib.CAAOpen.argtypes = [ctypes.c_int]
caa_lib.CAAOpen.restype = CAA_ERROR_CODE
caa_lib.CAAClose.argtypes = [ctypes.c_int]
caa_lib.CAAClose.restype = CAA_ERROR_CODE
caa_lib.CAAMoveTo.argtypes = [ctypes.c_int, ctypes.c_float]
caa_lib.CAAMoveTo.restype = CAA_ERROR_CODE
caa_lib.CAAStop.argtypes = [ctypes.c_int]
caa_lib.CAAStop.restype = CAA_ERROR_CODE
caa_lib.CAAIsMoving.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int)]
caa_lib.CAAIsMoving.restype = CAA_ERROR_CODE
caa_lib.CAAGetDegree.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_float)]
caa_lib.CAAGetDegree.restype = CAA_ERROR_CODE

class CAA:
    def __init__(self, caa_id=0):
        self.caa_id = caa_id
        
    @staticmethod
    def get_num():
        return caa_lib.CAAGetNum()
        
    def open(self):
        err = caa_lib.CAAOpen(self.caa_id)
        if err != 0: raise RuntimeError(f"CAAOpen failed with code {err}")
        
    def close(self):
        caa_lib.CAAClose(self.caa_id)
        
    def move_to(self, degree):
        err = caa_lib.CAAMoveTo(self.caa_id, float(degree))
        if err != 0: raise RuntimeError(f"CAAMoveTo failed with code {err}")
        
    def stop(self):
        err = caa_lib.CAAStop(self.caa_id)
        if err != 0: raise RuntimeError(f"CAAStop failed with code {err}")
        
    def is_moving(self):
        moving = ctypes.c_int(0)
        hc = ctypes.c_int(0)
        err = caa_lib.CAAIsMoving(self.caa_id, ctypes.byref(moving), ctypes.byref(hc))
        if err != 0: raise RuntimeError(f"CAAIsMoving failed with code {err}")
        return bool(moving.value)
        
    def get_degree(self):
        deg = ctypes.c_float(0.0)
        err = caa_lib.CAAGetDegree(self.caa_id, ctypes.byref(deg))
        if err != 0: raise RuntimeError(f"CAAGetDegree failed with code {err}")
        return deg.value
