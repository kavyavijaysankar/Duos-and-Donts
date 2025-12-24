# Duos-and-Donts
This is a 2-player co-operative serious game meant to be used as a tool in couples therapy. The gameplay dynamics are designed to foster interpersonal and relational skills between players. This game is a proof-of-concept and not a deployable clinical tool.

## How to Play:
The game follows a levelled system where players progress through increasingly complex challenges that require synchronized actions and clear communication.

| Feature | Player 1 (blue) | Player 2 (green) |
|:----------|:----------:|:----------:|
| Controls  | WASD keys  | Arrow keys  |
| Objective  | collect the key and unlock the treasure chest  | Assist Player 1 by disabling obstacles  |
| Roles  | Navigate path and avoid obstacles  | Use deactivators to clear Player 1's path  |
| Obstacles  | Red Guards  | Fake deactivators in level 3  |

### Key commands:
- 'R' key to restart the level
- 'M' key to return to the main menu
- SHIFT + [Level Number] to skip to a specific level

Read the briefings before each level and follow the on screen instructions to play the game.

### Level Breakdown:
- **Level 0 (Tutorial)**: A foundational level to introduce movement. Player 1 must retrieve the key and reach the chest while Player 2 moves freely with no active role.
- **Level 1 (Easy)**: Player 1 must reach the key/chest while avoiding guards' vision cones (contact results in a respawn). Player 2 must hover over deactivator switches to temporarily disable guards for Player 1.
- **Level 2 (Medium)**: Introduces faster patrolling guards and a mix of real and fake deactivator switches. Player 2 must discern and identify the correct deactivators to help Player 1.
- **Level 3 (Hard)**: The final challenge with high-stakes penalties. If Player 2 triggers a fake deactivator, Player 1 freezes and Player 2’s controls are inverted (hitting a wall causes a respawn). Player 2 must reach a special cyan antifreeze switch to recover.


## How to Run Locally:
The game is designed for high portability and is executed via a command-line interface, ensuring it is easily deployable on standard computers without needing a specific IDE.

### Prerequisites:
- Python 3.x installed on your machine.
- Pygame library installed.
The game uses the Pygame library for graphics and input handling. You can install it via pip:
```
pip install pygame
``` 

### Running the Game:
1. Open your command line interface (CLI)
2. Navigate to the directory where the game files are located
3. Run the main Python script to start:
```
Python main.py
```
Enjoy the game!