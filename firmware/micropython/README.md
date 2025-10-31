* Micropython firmware image here has some stuff baked in:

    - LVGL graphics
    - cryptography (for RSA / key signing) 


* `LVGL_MICROPYTHON_COMPILE_NOTES` is an unstructured, but correct, log of how the binary was built.

* At the moment, no other modules are frozen in, but if you wanted to do so, adding them to `hackaday_frozen_manifest.py` would be the thing to do, unless they require compiling, in which case, see above.

* `testing/` has any number of odd patched-together scripts, but they illustrate the way things work at the simplest / lowest level

* `system` is where the real OS is going to go.  Right now, totally WIP until we merge Ben's code in.


