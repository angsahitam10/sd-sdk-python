# sd-sdk-python
This module is a Python helper module for the Sound Designer SDK

This Python module depends on a copy of the Sound Designer SDK being accessible on your computer. Make sure you have unzipped the Sound Designer SDK somewhere and then set the environment variable `SD_SDK_ROOT` to the root folder of the unzipped SDK, or to the path containing the Windows binaries (.dlls), Python module (`sd.pyd`), and `sd.config` file.

To test whether or not this module can resolve a valid Sound Designer SDK, you can run the following commands:

```python
import sd_sdk_python
print(sd_sdk_python.get_product_manager().Version)
```
