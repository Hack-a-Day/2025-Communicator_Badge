# User Application Manager

AppManager is a replacement AppMenu that automatically discovers new apps.

Simply copy the application .py module into the /apps directory on the device
and reset.

## Application Module Metadata

AppManager uses one required metadata constant and one optional constant to
discover app modules and add them to its menu system.

  * ```APP_NAME``` is required, and must be contain the name of the app as a
    string. App name will be used to name the app's entry in the AppManager
    menu. App names should be short to fit in the menu, but descriptive and
    unique.
  * ```APP_CLASS``` is optional, and can contain the application class as a
    callable. By default AppManager will look for a class named ```App``` in
    the app module, but this constant will override the application class to
    an arbitrary class object or any callback taking ```badge``` as its only
    argument.

For example, adding the following lines to ```userA.py``` will make it
automically discoverable as a user app:

```
APP_NAME = "UserA"
APP_CLASS = App
```

Note: in this case ```APP_CLASS``` would not be required.

## Installation

Copy ```app_manager.py``` to ```firmware/badge/apps``` to install the
application.

Optionally copy ```main.py``` from this directory to ```firmware/badge``` to
replace the default hard-coded User AppMenu with AppManager in the main menu.