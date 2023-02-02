import time
import numpy as np

from .exampleinst import ExampleInst

class ExampleInst2(ExampleInst):
    def get_data(self):
        times = np.linspace(0, 10, 100)
        values = np.sin(times + 0.1 * time.time())

        return {
            "time": list(times),
            "val": list(values)
        }

    def _save_data(self, hdf5_path: str, array, dgw):
        path = f"{hdf5_path}/{self._name}/{time.ctime()}"
        dgw.append(path, array, plotConfig = "dset_mult")
