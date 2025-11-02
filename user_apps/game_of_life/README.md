# Game of Life

This app runs a simulation of Conway's Game of Life,

You can customize the initial pattern and the resolution of the grid.

## Controls

### Main Menu

- **F1 (Start):** Begins the Game of Life simulation with the currently selected mode and resolution.
- **F2 (Mode):** Opens a menu to select the initial state of the grid.
- **F3 (Res):** Opens a menu to change the cell size, which alters the grid resolution.
- **F5 (Home):** Exits the app and returns to the main badge menu.

### Mode / Resolution Selection

- **F1 (Select) / Enter:** Confirms the highlighted selection.
- **F2 (Up) / Up Arrow:** Navigates up the list.
- **F3 (Down) / Down Arrow:** Navigates down the list.
- **F5 (Back):** Returns to the main menu without saving changes.

### During Simulation

- **Press any function key (F1-F5):** Stops the simulation and returns to the app's main menu.

## Features

- **Initial Modes:** Start with various patterns:
  - **Random:** A randomly populated grid.
  - **Empty:** A blank grid.
  - **Full:** A completely filled grid.
  - **Glider:** A classic "glider" pattern.
  - **LWSS:** A "Light-Weight Spaceship" pattern.
- **Adjustable Resolution:** Choose from multiple cell sizes to change the simulation's grid dimensions.
- **Camera Trigger:** The `SAO_GPIO1` pin toggles on each new frame, allowing you to trigger an external camera to create timelapses of the simulation.

## Installation Instructions

Copy `game_of_life.py` to your `firmware/badge/apps` folder and modify `firmware/badge/main.py` to add "Game of Life" to your User Apps menu.
