import pygame
import sys
import math

# --- CONFIGURATION ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# COLORS
C_BG = (15, 15, 20)          # Deep Dark Blue
C_WALL = (100, 110, 130)     # Steel Walls
C_P1 = (60, 150, 250)        # Player 1 (Blue)
C_P2 = (100, 220, 100)       # Player 2 (Green)
C_GUARD = (220, 40, 40)      # Active Hazard (Body)
C_GUARD_OFF = (60, 60, 60)   # Disabled Hazard
C_VISION = (255, 0, 0, 100)  # Transparent Red Cone (Visible Danger Zone)
C_GOAL = (255, 215, 0)       # Treasure Gold
C_DEACTIVATOR = (200, 100, 200) # Purple Switches
C_FAKE_DEACTIVATOR = (80, 50, 80) # Dark Purple/Grey Fake Switches
C_PRESSURE_PLATE = (255, 165, 0) # Orange Plate
C_TEXT = (255, 255, 255)
C_HUD_BG = (30, 30, 40)
C_DYNAMIC_WALL = (165, 42, 42) # Brown-Red for Walls P2 must open

# --- ENGINE SETUP ---
pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Duos & Don'ts: Protocol Sync")
clock = pygame.time.Clock()
font_title = pygame.font.SysFont("Arial", 50, bold=True)
font_ui = pygame.font.SysFont("Consolas", 24)
font_small = pygame.font.SysFont("Consolas", 16)

# --- CLASSES ---

class Player:
    def __init__(self, x, y, color, controls):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.color = color
        self.controls = controls
        self.speed = 5
        self.start_pos = (x, y)

    def update(self, keys, walls, dynamic_walls_state):
        dx, dy = 0, 0
        if keys[self.controls['up']]: dy = -self.speed
        if keys[self.controls['down']]: dy = self.speed
        if keys[self.controls['left']]: dx = -self.speed
        if keys[self.controls['right']]: dx = self.speed

        # Move X
        self.rect.x += dx
        
        # Check collision with static walls and currently closed dynamic walls
        current_walls = walls + [dw for dw in dynamic_walls_state.values() if not dw['is_open'] and dw['player'] == self]
        if self.rect.collidelist(current_walls) != -1:
            self.rect.x -= dx
            
        # Move Y
        self.rect.y += dy
        if self.rect.collidelist(current_walls) != -1:
            self.rect.y -= dy

        # Clamp to screen
        self.rect.clamp_ip(screen.get_rect())

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=6)
        # Eyes
        pygame.draw.circle(surface, (255,255,255), (self.rect.x + 8, self.rect.y + 8), 4)
        pygame.draw.circle(surface, (255,255,255), (self.rect.x + 24, self.rect.y + 8), 4)

    def reset(self):
        self.rect.topleft = self.start_pos

class Guard:
    def __init__(self, x, y, patrol_path, angle_start, link_id, speed=0, fov=60, vision_len=180, sweep_speed=0):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.patrol_path = patrol_path # List of tuples [(x,y), (x,y)]
        self.current_point = 0
        self.speed = speed
        self.base_angle = angle_start
        self.current_angle = angle_start
        self.vision_length = vision_len
        self.fov = fov
        self.link_id = link_id
        self.active = True
        self.sweep_speed = sweep_speed 
        self.sweep_offset = 0

    def update(self):
        if not self.active: return

        # 1. Patrol Movement (Physical)
        if self.patrol_path and len(self.patrol_path) > 1:
            target = self.patrol_path[self.current_point]
            tx, ty = target
            dir_x, dir_y = tx - self.rect.x, ty - self.rect.y
            dist = math.hypot(dir_x, dir_y)
            
            if dist < self.speed:
                self.current_point = (self.current_point + 1) % len(self.patrol_path)
            else:
                self.rect.x += (dir_x / dist) * self.speed
                self.rect.y += (dir_y / dist) * self.speed
                # Guard faces movement direction if moving
                if self.sweep_speed == 0:
                    self.base_angle = -math.degrees(math.atan2(dir_y, dir_x))

        # 2. Vision Sweeping (Rotation)
        if self.sweep_speed != 0:
            self.sweep_offset += self.sweep_speed
            if abs(self.sweep_offset) > 45: # Limit sweep range
                self.sweep_speed *= -1
            self.current_angle = self.base_angle + self.sweep_offset
        else:
            self.current_angle = self.base_angle

    def draw(self, surface):
        color = C_GUARD if self.active else C_GUARD_OFF
        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        
        if self.active:
            # Draw Vision Cone
            rad = math.radians(-self.current_angle)
            center = self.rect.center
            
            # Left edge of cone
            l_rad = rad - math.radians(self.fov / 2)
            lx = center[0] + math.cos(l_rad) * self.vision_length
            ly = center[1] + math.sin(l_rad) * self.vision_length
            
            # Right edge of cone
            r_rad = rad + math.radians(self.fov / 2)
            rx = center[0] + math.cos(r_rad) * self.vision_length
            ry = center[1] + math.sin(r_rad) * self.vision_length

            # Create a transparent surface for the cone
            cone_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(cone_surf, C_VISION, [center, (lx, ly), (rx, ry)])
            surface.blit(cone_surf, (0,0))

    def check_collision(self, player_rect):
        """Returns True if player hits body OR vision cone."""
        if not self.active: return False
        
        # 1. Body Collision
        if self.rect.colliderect(player_rect):
            return True

        # 2. Vision Cone Collision (Point in Polygon)
        # Check all 4 corners of player
        points = [player_rect.topleft, player_rect.topright, player_rect.bottomleft, player_rect.bottomright]
        
        for px, py in points:
            dx = px - self.rect.centerx
            dy = py - self.rect.centery
            dist = math.hypot(dx, dy)
            
            if dist <= self.vision_length:
                # Calculate angle to player
                angle_to_point = -math.degrees(math.atan2(dy, dx))
                # Normalize angle difference
                diff = (angle_to_point - self.current_angle + 180) % 360 - 180
                if abs(diff) < self.fov / 2:
                    return True
        return False

class Deactivator:
    def __init__(self, x, y, link_id, is_fake=False):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.link_id = link_id
        self.is_pressed = False
        self.is_fake = is_fake # If true, pressing it does nothing

    def update(self, player_rect):
        self.is_pressed = self.rect.colliderect(player_rect)

    def draw(self, surface):
        if self.is_fake:
            color = C_FAKE_DEACTIVATOR
            frame_color = (40, 40, 40)
        else:
            color = (150, 255, 150) if self.is_pressed else C_DEACTIVATOR
            frame_color = (50,0,50)
            
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, frame_color, self.rect.inflate(-10, -10))

class DynamicWall:
    def __init__(self, rect_data, link_id, player_owner):
        self.rect = pygame.Rect(rect_data)
        self.link_id = link_id
        self.is_open = False
        self.player_owner = player_owner # Which player's collision list this wall belongs to

    def draw(self, surface):
        # Draw dynamic wall only if it is closed
        if not self.is_open:
            pygame.draw.rect(surface, C_DYNAMIC_WALL, self.rect, border_radius=2)
            # Add a pattern to show it's dynamic
            if self.rect.width > self.rect.height: # Horizontal
                 pygame.draw.line(surface, C_WALL, self.rect.topleft, self.rect.bottomright, 3)
                 pygame.draw.line(surface, C_WALL, self.rect.topright, self.rect.bottomleft, 3)
            else: # Vertical
                 pygame.draw.line(surface, C_WALL, self.rect.topleft, self.rect.bottomright, 3)
                 pygame.draw.line(surface, C_WALL, self.rect.topright, self.rect.bottomleft, 3)

class PressurePlate:
    def __init__(self, x, y, link_id):
        self.rect = pygame.Rect(x, y, 50, 50)
        self.link_id = link_id
        self.is_pressed = False

    def update(self, player_rect):
        self.is_pressed = self.rect.colliderect(player_rect)

    def draw(self, surface):
        color = (255, 200, 0) if self.is_pressed else C_PRESSURE_PLATE
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        pygame.draw.rect(surface, (100, 50, 0), self.rect.inflate(-10, -10))


# --- LEVEL DEFINITIONS ---

def get_levels():
    # Common Wall Layout (Split Screen)
    # Left Side: 0-630 (P1), Right Side: 650-1280 (P2)
    # Divider at 640
    
    # Base Walls (Borders)
    base_walls = [
        (0,0, SCREEN_WIDTH, 10), # Top
        (0, SCREEN_HEIGHT-10, SCREEN_WIDTH, 10), # Bottom
        (0,0, 10, SCREEN_HEIGHT), # Left
        (SCREEN_WIDTH-10, 0, 10, SCREEN_HEIGHT), # Right
        (635, 0, 10, SCREEN_HEIGHT) # Center Divider
    ]

    levels = []

    # --- LEVEL 1 (NEW): Patience (Sweep) ---
    # Tight corridor. Guards rotate vision, forcing P1 to time their pass.
    l1_walls = list(base_walls)
    l1_walls.extend([
        # Corridor Walls
        (150, 100, 20, 500), # Left Wall of corridor
        (450, 100, 20, 500)  # Right Wall of corridor
    ])
    
    levels.append({
        "name": "Level 1: Patience Protocol",
        "desc": "P1 must wait for Guard 1's vision to sweep away. P2 must hold Switch 2.",
        "p1_start": (300, 650),
        "p2_start": (700, 350),
        "goal": (300, 50, 40, 40), # End of corridor
        "walls": l1_walls,
        "guards": [
            # Guard in corridor, looking down, sweeping left/right
            {"x": 300, "y": 200, "path": [], "angle": 90, "id": 1, "speed": 0, "fov": 40, "len": 250, "sweep_speed": 1.5},
            # Guard at bottom, sweeping up/down, requires P2 to deactivate
            {"x": 300, "y": 500, "path": [], "angle": 270, "id": 2, "speed": 0, "fov": 40, "len": 200, "sweep_speed": 1.5}
        ],
        "deactivators": [
            {"x": 1100, "y": 600, "id": 2}
        ],
        "dynamic_walls": [],
        "pressure_plates": []
    })


    # --- LEVEL 2 (NEW): The Heist (Complex Maze + Deactivator Logic) ---
    # Based on old Level 5, but with P2 maze and no timer. Guards move very fast.
    l2_walls = list(base_walls)
    # P1 Zone Walls (Corridors and blocks)
    l2_walls.extend([
        (0, 200, 400, 20),
        (200, 450, 430, 20)
    ])
    # P2 Zone Walls (The Maze)
    l2_walls.extend([
        (700, 100, 20, 300),
        (850, 400, 20, 310),
        (1000, 100, 20, 400),
        (1150, 300, 20, 400),
        (700, 500, 300, 20),
    ])
    
    levels.append({
        "name": "Level 2: Communication Grid",
        "desc": "P1, tell P2 which of the 3 real switches (out of 6) corresponds to your danger.",
        "p1_start": (50, 50),
        "p2_start": (700, 50),
        "goal": (550, 650, 40, 40), # Bottom Right corner
        "walls": l2_walls,
        "guards": [
            # Guard 1: Horizontal Patrol (ID 1)
            {"x": 50, "y": 300, "path": [(50, 300), (550, 300)], "angle": 0, "id": 1, "speed": 7, "fov": 45, "len": 100},
            # Guard 2: Vertical Patrol (ID 2)
            {"x": 400, "y": 100, "path": [(400, 100), (400, 400)], "angle": 90, "id": 2, "speed": 6, "fov": 45, "len": 150},
            # Guard 3: Sweeping Goal Defense (ID 3)
            {"x": 580, "y": 580, "path": [], "angle": 225, "id": 3, "speed": 0, "fov": 70, "len": 200, "sweep_speed": 2}
        ],
        "deactivators": [
            # Real Switches (IDs 1, 2, 3)
            {"x": 750, "y": 600, "id": 1, "fake": False},
            {"x": 900, "y": 100, "id": 2, "fake": False},
            {"x": 1200, "y": 650, "id": 3, "fake": False},
            # Fake Switches (Do nothing, IDs 4, 5, 6)
            {"x": 800, "y": 450, "id": 4, "fake": True},
            {"x": 1100, "y": 150, "id": 5, "fake": True},
            {"x": 1000, "y": 600, "id": 6, "fake": True}
        ],
        "dynamic_walls": [],
        "pressure_plates": []
    })

    # --- LEVEL 3 (NEW): Interdependence (Pressure Plate + Dynamic Wall) ---
    l3_walls = list(base_walls)
    
    # P2 Zone Maze Walls
    l3_walls.extend([
        (750, 100, 20, 500),
        (900, 400, 370, 20),
        (1050, 200, 20, 400),
    ])
    
    # Dynamic Wall Definition (Needs to be opened by P2's Pressure Plate)
    dynamic_walls = [
        {"rect": (250, 350, 150, 20), "id": 1, "player": "p1"}
    ]

    levels.append({
        "name": "Level 3: Interdependence",
        "desc": "P1 needs 2 switches and P2 must stand still on the Orange Plate to open a wall.",
        "p1_start": (50, 650),
        "p2_start": (1200, 50),
        "goal": (550, 50, 40, 40), # Top Right
        "walls": l3_walls,
        "guards": [
            # Guard 1: Patrols vertically, requires Switch 1
            {"x": 100, "y": 200, "path": [(100, 200), (100, 500)], "angle": 90, "id": 1, "speed": 5, "fov": 60, "len": 180},
            # Guard 2: Sweeping, requires Switch 2
            {"x": 500, "y": 200, "path": [], "angle": 270, "id": 2, "speed": 0, "fov": 60, "len": 180, "sweep_speed": 1.5},
            # Guard 3: Blocks path after Dynamic Wall, requires Switch 3 (fake switch - P1 must time it)
            {"x": 400, "y": 150, "path": [(400, 150), (200, 150)], "angle": 0, "id": 3, "speed": 8, "fov": 45, "len": 120},
        ],
        "deactivators": [
            # Real Switches
            {"x": 1200, "y": 100, "id": 1, "fake": False}, # Top Right of P2 maze
            {"x": 700, "y": 300, "id": 2, "fake": False}, # Left of P2 maze
            # Fake Switch (P1 must rely on timing)
            {"x": 1000, "y": 600, "id": 3, "fake": True},
        ],
        "dynamic_walls": dynamic_walls,
        "pressure_plates": [
            {"x": 980, "y": 50, "id": 1} # Plate 1 opens Dynamic Wall 1
        ]
    })


    return levels

# --- GAME MANAGER ---

class Game:
    def __init__(self):
        self.levels = get_levels()
        self.current_level_idx = 0
        self.state = "MENU"
        self.load_level(self.current_level_idx)
        
    def load_level(self, idx):
        # Check if the campaign is complete
        if idx >= len(self.levels):
            self.state = "CAMPAIGN_COMPLETE"
            return
            
        self.current_level_idx = idx
        data = self.levels[idx]
        self.level_name = data["name"]
        self.level_desc = data["desc"]
        
        # Parse Walls
        self.walls = [pygame.Rect(w) for w in data["walls"]]
        
        # Parse Players
        self.p1 = Player(data["p1_start"][0], data["p1_start"][1], C_P1, 
                        {'up': pygame.K_w, 'down': pygame.K_s, 'left': pygame.K_a, 'right': pygame.K_d})
        self.p2 = Player(data["p2_start"][0], data["p2_start"][1], C_P2, 
                        {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT, 'right': pygame.K_RIGHT})
        
        # Parse Goal
        self.goal_rect = pygame.Rect(data["goal"])
        
        # Parse Guards
        self.guards = []
        for g in data["guards"]:
            sweep = g.get("sweep_speed", 0)
            self.guards.append(Guard(g["x"], g["y"], g["path"], g["angle"], g["id"], g["speed"], g["fov"], g["len"], sweep))
            
        # Parse Deactivators
        self.deactivators = []
        for d in data["deactivators"]:
            self.deactivators.append(Deactivator(d["x"], d["y"], d["id"], d.get("fake", False)))

        # Parse Pressure Plates
        self.pressure_plates = []
        for pp in data["pressure_plates"]:
            self.pressure_plates.append(PressurePlate(pp["x"], pp["y"], pp["id"]))

        # Parse Dynamic Walls (store in a dict for easy state checking)
        self.dynamic_walls = {}
        for dw_data in data["dynamic_walls"]:
            player_obj = self.p1 if dw_data["player"] == "p1" else self.p2
            dw = DynamicWall(dw_data["rect"], dw_data["id"], player_obj)
            self.dynamic_walls[dw.link_id] = {'wall': dw, 'is_open': False, 'player': player_obj}
        
        # Reset Timer (Level 5 has been removed/refactored, so no timer needed)
        self.time_limit = None
        self.start_ticks = pygame.time.get_ticks()
        self.state = "PLAYING" # Automatically start playing after load

    def restart_level(self):
        self.load_level(self.current_level_idx)
        self.state = "PLAYING"
        self.start_ticks = pygame.time.get_ticks()

    def restart_game(self):
        self.current_level_idx = 0
        self.load_level(0)
        self.state = "MENU"

    def update(self):
        keys = pygame.key.get_pressed()
        
        # Global Shortcuts (Shift + 1, 2, 3)
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            if keys[pygame.K_r]: self.restart_game()
            if keys[pygame.K_1]: self.load_level(0)
            if keys[pygame.K_2]: self.load_level(1)
            if keys[pygame.K_3]: self.load_level(2)
            return

        if self.state == "MENU":
            if keys[pygame.K_SPACE]: 
                self.load_level(0) # Load first level
                self.state = "PLAYING"
                self.start_ticks = pygame.time.get_ticks()

        elif self.state == "PLAYING":
            # Update Player Collisions (Pass dynamic wall state to check)
            self.p1.update(keys, self.walls, self.dynamic_walls)
            self.p2.update(keys, self.walls, self.dynamic_walls)
            
            # Deactivator and Pressure Plate Logic
            active_links = {}
            for d in self.deactivators:
                d.update(self.p2.rect)
                if d.is_pressed and not d.is_fake:
                    active_links[d.link_id] = True
            
            for pp in self.pressure_plates:
                pp.update(self.p2.rect)
                if pp.is_pressed:
                    active_links[pp.link_id] = True

            # Dynamic Wall Logic (Open walls if linked pressure plate is active)
            for link_id, dw_data in self.dynamic_walls.items():
                dw_data['is_open'] = active_links.get(link_id, False)
                
            # Guard Logic
            for g in self.guards:
                # Check Deactivation (only if link_id is in active_links)
                g.active = not active_links.get(g.link_id, False)
                
                g.update()
                
                # Check Hit
                if g.check_collision(self.p1.rect):
                    self.p1.reset() # Reset P1 only
            
            # Win Condition
            if self.p1.rect.colliderect(self.goal_rect):
                self.state = "VICTORY"

        elif self.state == "VICTORY":
            if keys[pygame.K_r]:
                self.load_level(self.current_level_idx + 1)
                
        elif self.state == "CAMPAIGN_COMPLETE":
            if keys[pygame.K_r]:
                self.restart_game()


    def draw(self):
        screen.fill(C_BG)
        
        if self.state == "MENU":
            self.draw_centered_text("DUOS & DON'TS", -50, font_title, C_P1)
            self.draw_centered_text("Press SPACE to Start", 50, font_ui)
            self.draw_centered_text("P1 (Blue, WASD) navigates hazards. P2 (Green, Arrows) opens the path.", 100, font_small)
            
        elif self.state in ("PLAYING", "VICTORY"):
            # Draw World
            for wall in self.walls: 
                pygame.draw.rect(screen, C_WALL, wall)
            
            # Draw Dynamic Walls (only if closed)
            for dw_data in self.dynamic_walls.values():
                dw_data['wall'].draw(screen)
            
            # Draw Interactables
            for d in self.deactivators: d.draw(screen)
            for pp in self.pressure_plates: pp.draw(screen)
            
            # Draw Goal
            pygame.draw.rect(screen, C_GOAL, self.goal_rect, border_radius=10)
            
            # Draw Hazards
            for g in self.guards: g.draw(screen)
            
            # Draw Players
            self.p1.draw(screen)
            self.p2.draw(screen)
            
            # HUD
            pygame.draw.rect(screen, C_HUD_BG, (0, 0, SCREEN_WIDTH, 60))
            screen.blit(font_ui.render(self.level_name, True, C_GOAL), (20, 10))
            screen.blit(font_small.render(self.level_desc, True, (200,200,200)), (20, 35))
            
            # Victory Overlay
            if self.state == "VICTORY":
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0,0,0,150))
                screen.blit(overlay, (0,0))
                self.draw_centered_text("LEVEL CLEARED", -30, font_title, C_GOAL)
                self.draw_centered_text("Press 'R' for Next Level", 30, font_ui)

        elif self.state == "CAMPAIGN_COMPLETE":
            self.draw_centered_text("PROTOCOL COMPLETE: SUCCESSFUL SYNC", -50, font_title, C_GOAL)
            self.draw_centered_text("All levels cleared. Interdependence achieved.", 50, font_ui)
            self.draw_centered_text("Click 'R' to Restart Campaign", 100, font_ui)

        pygame.display.flip()

    def draw_centered_text(self, text, y_off, font, color=C_TEXT):
        surf = font.render(text, True, color)
        rect = surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + y_off))
        screen.blit(surf, rect)

# --- MAIN LOOP ---
game = Game()
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False
        if event.type == pygame.KEYDOWN:
            # Handle R key specifically here to ensure it triggers once per press
            mods = pygame.key.get_mods()
            if event.key == pygame.K_r:
                if game.state == "PLAYING":
                    game.restart_level()
                elif game.state == "VICTORY":
                    game.update() # Triggers loading next level
                elif game.state == "CAMPAIGN_COMPLETE":
                    game.update() # Triggers restart

    game.update()
    game.draw()
    clock.tick(FPS)

pygame.quit()
sys.exit()