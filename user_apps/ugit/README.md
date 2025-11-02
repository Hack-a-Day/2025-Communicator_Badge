# uGit - OTA updates directly from the repo!

Place ugit.py at the root of the device

Open the REPL (crtl+C or crtl+D) and run:

```python
import ugit
ugit.pull_all()
```

This will pull all udpated files from the repo's firmware/badge/ onto the device, and restart when complete.