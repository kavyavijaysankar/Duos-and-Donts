# Duos-and-Donts
This is a 2-player co-operative serious game meant to be used as a tool in couples therapy. The gameplay dynamics are designed to foster interpersonal and relational skills between players. This game is a proof-of-concept and not a deployable clinical tool.

### 🎮 [Play the Game in Your Browser](https://kavyavijaysankar.github.io/Duos-and-Donts/)
*No installation required. Can be played on any browser.*

## How to Play:
The game follows a levelled system where players progress through increasingly complex challenges that require synchronized actions and clear communication.

| Feature | Player 1 (blue) | Player 2 (green) |
|:----------|:----------:|:----------:|
| Controls  | WASD keys  | Arrow keys  |
| Objective  | Collect the key and unlock the treasure chest  | Assist Player 1 by disabling obstacles  |
| Roles  | Navigate path and avoid obstacles  | Use deactivators to clear Player 1's path  |
| Obstacles  | Red Guards  | Fake deactivators in level 3  |

### Key commands:
- 'R' key to restart the level
- 'M' key to return to the main menu
- SHIFT + [Level Number] to skip to a specific level

**Read the briefings before each level and follow the on screen instructions to play the game.**

### Level Breakdown:
- **Level 0 (Tutorial)**: A foundational level to introduce movement. Player 1 must retrieve the key and reach the chest while Player 2 moves freely with no active role.
- **Level 1 (Easy)**: Player 1 must reach the key/chest while avoiding guards' vision cones (contact results in a respawn). Player 2 must hover over deactivator switches to temporarily disable guards for Player 1.
- **Level 2 (Medium)**: Introduces faster patrolling guards and a mix of real and fake deactivator switches. Player 2 must discern and identify the correct deactivators to help Player 1.
- **Level 3 (Hard)**: The final challenge with high-stakes penalties. If Player 2 triggers a fake deactivator, Player 1 freezes and Player 2’s controls are inverted (hitting a wall causes a respawn). Player 2 must reach a special cyan antifreeze switch to recover.


## Local Execution & Deployment
The project is available both as a web-based application via [GitHub Pages](https://kavyavijaysankar.github.io/Duos-and-Donts/), and a local source-code execution. The deployment utilizes **pygbag** to compile the Python source code and assets into a web-ready format.

### Local Execution:
If you wish to run the raw Python source code on your machine:

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/kavyavijaysankar/duos-and-donts.git](https://github.com/kavyavijaysankar/duos-and-donts.git)
    cd duos-and-donts
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Execute the game:**
    ```bash
    python main.py
    ```

---
## Repository Structure
The repository is organized to maintain a clear distinction between source code, assets, and deployment builds:

* **`main.py`**: The core Python script containing game logic, state management, and rendering.
* **`assets/`**: Contains open-source fonts licenses.
* **`docs/`**: The WebAssembly (Wasm) build used for GitHub Pages deployment.
* **`requirements.txt`**: Python dependencies required for local execution.


## License and Attribution
* **Code:** This project is licensed under the MIT License.
* **Fonts:** 
    * *Open Sans* (Bold) - Open Font License.
    * *Inconsolata* (Regular) - Open Font License.

See the `assets/` folder for full license text.