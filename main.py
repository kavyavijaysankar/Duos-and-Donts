import pygame
import sys
import math

# --- CONFIGURATION ---
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
HUD_OFFSET = 60 # Shift the entire game world down to make space for the HUD

# COLORS
C_BG = (15, 15, 20)          # Deep Dark Blue
C_WALL = (100, 110, 130)     # Steel Walls
C_P1 = (60, 150, 250)        # Player 1 (Blue)
C_P2 = (100, 220, 100)       # Player 2 (Green)
C_GUARD = (220, 40, 40)      # Active Hazard (Body)
C_GUARD_OFF = (60, 60, 60)   # Disabled Hazard
C_VISION = (255, 0, 0, 100)  # Transparent Red Cone (Visible Danger Zone)
C_KEY = (255, 215, 0)        # Key Gold (Used for Key object, Victory Text, and Titles)
C_CHEST = (255, 255, 100)    # Treasure Chest (Yellow-White)
C_DEACTIVATOR = (200, 100, 200) # Purple Switches
C_TEXT = (255, 255, 255)
C_HUD_BG = (30, 30, 40)
C_DYNAMIC_WALL = (165, 42, 42) # Brown-Red for Walls P2 must open
C_PRESSURE_PLATE = (255, 165, 0) # Orange Plate
C_ESCAPE_POD = (139, 69, 19) # Brown/Wood for the Pod

# --- ENGINE SETUP ---
try:
    pygame.init()
except pygame.error as e:
    print(f"Pygame initialization failed: {e}")
    sys.exit()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Duos & Don'ts: Protocol Sync")
clock = pygame.time.Clock()
font_title = pygame.font.SysFont("Arial", 50, bold=True)
font_ui = pygame.font.SysFont("Consolas", 24)
font_small = pygame.font.SysFont("Consolas", 18)
font_rules = pygame.font.SysFont("Consolas", 20)

# --- CLASSES ---

class DynamicWall:
    def __init__(self, rect_data, link_id, player_owner):
        self.rect = pygame.Rect(rect_data)
        self.link_id = link_id
        self.is_open = False
        self.player_owner = player_owner 

    def draw(self, surface):
        if not self.is_open:
            pygame.draw.rect(surface, C_DYNAMIC_WALL, self.rect, border_radius=2)
            # Drawing an X to clearly show it's a closed barrier
            line_color = (255, 255, 255) 
            pygame.draw.line(surface, line_color, self.rect.topleft, self.rect.bottomright, 3)
            pygame.draw.line(surface, line_color, self.rect.topright, self.rect.bottomleft, 3)

class Player:
    def __init__(self, x, y, color, controls, player_id):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.color = color
        self.controls = controls
        self.speed = 5
        self.start_pos = (x, y)
        self.player_id = player_id # "p1" or "p2"
        self.prev_x = x
        self.prev_y = y
        self.is_trapped = False # New state for Level 3

    def update(self, keys, walls, dynamic_walls_state, escape_pod=None):
        dx, dy = 0, 0
        
        # P1 cannot move if trapped in the Escape Pod
        if self.is_trapped and self.player_id == "p1":
            dx, dy = 0, 0
        else:
            if keys[self.controls['up']]: dy = -self.speed
            if keys[self.controls['down']]: dy = self.speed
            if keys[self.controls['left']]: dx = -self.speed
            if keys[self.controls['right']]: dx = self.speed

        self.prev_x = self.rect.x
        self.prev_y = self.rect.y

        # Define the set of walls that can collide with this player
        current_collidable_walls = walls + [
            dw['wall'].rect for dw in dynamic_walls_state.values() 
            if not dw['is_open'] and dw['player'].player_id == self.player_id
        ]
        
        # Move X
        self.rect.x += dx
        if self.rect.collidelist(current_collidable_walls) != -1:
            self.rect.x -= dx
            
        # Move Y
        self.rect.y += dy
        if self.rect.collidelist(current_collidable_walls) != -1:
            self.rect.y -= dy

        # Clamp to screen boundaries (accounting for HUD_OFFSET)
        playable_rect = pygame.Rect(10, 10 + HUD_OFFSET, SCREEN_WIDTH - 20, SCREEN_HEIGHT - 20 - HUD_OFFSET)
        self.rect.clamp_ip(playable_rect)

        # Boundary Enforcement (P2 must stay right of the divider, P1 must stay left)
        # Note: Center Divider is at x=635 (10 pixels wide)
        if self.player_id == "p1":
            if self.rect.right > 635:
                self.rect.right = 635 
            # If P1 is in the Escape Pod, clamp them to the pod's interior
            if self.is_trapped and escape_pod:
                # This clamping ensures P1 stays inside the pod and moves with it passively 
                # (Actual movement with the pod is handled in Game.update)
                self.rect.clamp_ip(escape_pod.inflate(-8, -8))
                
        elif self.player_id == "p2":
            if self.rect.left < 645:
                self.rect.left = 645
            
    def is_moving(self):
        """Checks if the player moved in the last update cycle."""
        return self.rect.x != self.prev_x or self.rect.y != self.prev_y

    def draw(self, surface):
        pygame.draw.rect(surface, self.color, self.rect, border_radius=6)
        # Eyes
        pygame.draw.circle(surface, (255,255,255), (self.rect.x + 8, self.rect.y + 8), 4)
        pygame.draw.circle(surface, (255,255,255), (self.rect.x + 24, self.rect.y + 8), 4)

    def reset(self):
        self.rect.topleft = self.start_pos
        self.is_trapped = False # Reset trap state

class Guard:
    # (Guard class remains the same as previous iterations)
    def __init__(self, x, y, patrol_path, angle_start, link_id, speed=0, fov=60, vision_len=180, sweep_speed=0):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.patrol_path = patrol_path
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
        
        if self.speed > 0 and self.patrol_path and len(self.patrol_path) > 1:
            target = self.patrol_path[self.current_point]
            tx, ty = target
            dir_x, dir_y = tx - self.rect.x, ty - self.rect.y
            dist = math.hypot(dir_x, dir_y)
            
            if dist < self.speed:
                self.rect.x = tx
                self.rect.y = ty
                self.current_point = (self.current_point + 1) % len(self.patrol_path)
            else:
                self.rect.x += (dir_x / dist) * self.speed
                self.rect.y += (dir_y / dist) * self.speed
                if self.sweep_speed == 0:
                    self.base_angle = -math.degrees(math.atan2(dir_y, dir_x))

        if self.sweep_speed != 0:
            self.sweep_offset += self.sweep_speed
            if abs(self.sweep_offset) > 45: 
                self.sweep_speed *= -1
            self.current_angle = self.base_angle + self.sweep_offset
        else:
            self.current_angle = self.base_angle

    def draw(self, surface):
        color = C_GUARD if self.active else C_GUARD_OFF
        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        
        if self.active:
            rad = math.radians(-self.current_angle)
            center = self.rect.center
            l_rad = rad - math.radians(self.fov / 2); lx = center[0] + math.cos(l_rad) * self.vision_length; ly = center[1] + math.sin(l_rad) * self.vision_length
            r_rad = rad + math.radians(self.fov / 2); rx = center[0] + math.cos(r_rad) * self.vision_length; ry = center[1] + math.sin(r_rad) * self.vision_length

            cone_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(cone_surf, C_VISION, [center, (lx, ly), (rx, ry)])
            surface.blit(cone_surf, (0,0))

    def check_collision(self, player_rect):
        if not self.active: return False
        if self.rect.colliderect(player_rect): return True

        points = [player_rect.topleft, player_rect.topright, player_rect.bottomleft, player_rect.bottomright]
        for px, py in points:
            dx = px - self.rect.centerx; dy = py - self.rect.centery; dist = math.hypot(dx, dy)
            if dist <= self.vision_length:
                angle_to_point = -math.degrees(math.atan2(dy, dx))
                diff = (angle_to_point - self.current_angle + 180) % 360 - 180
                if abs(diff) < self.fov / 2: return True
        return False

class Deactivator:
    # (Deactivator class remains the same as previous iterations)
    def __init__(self, x, y, link_id, is_fake=False):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.link_id = link_id
        self.is_pressed = False
        self.is_fake = is_fake 

    def update(self, player_rect):
        self.is_pressed = self.rect.colliderect(player_rect)

    def draw(self, surface):
        if self.is_pressed and not self.is_fake:
            color = (150, 255, 150) 
            frame_color = (50, 0, 50)
        else:
            color = C_DEACTIVATOR 
            frame_color = (80, 50, 80)
            
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, frame_color, self.rect.inflate(-10, -10), border_radius=4)


class SyncZone: 
    # (SyncZone class remains the same as previous iterations)
    def __init__(self, x, y, link_id):
        self.rect = pygame.Rect(x, y, 50, 50)
        self.link_id = link_id
        self.is_active = False 

    def update(self, player, is_player_moving):
        is_colliding = self.rect.colliderect(player.rect)
        # SyncZone only activates if P2 is inside the zone AND P2 is moving
        self.is_active = is_colliding and is_player_moving 

    def draw(self, surface):
        color = (255, 200, 0) if self.is_active else C_PRESSURE_PLATE
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        pygame.draw.rect(surface, (100, 50, 0), self.rect.inflate(-10, -10), border_radius=8)


# --- LEVEL DEFINITIONS ---

def offset_rect(r):
    """Helper to apply the HUD_OFFSET to all Y coordinates of a rect definition (x, y, w, h)."""
    x, y, w, h = r
    return (x, y + HUD_OFFSET, w, h)

def offset_point(p):
    """Helper to apply the HUD_OFFSET to all Y coordinates of a point definition (x, y)."""
    x, y = p
    return (x, y + HUD_OFFSET)

def get_levels():
    
    # Base Walls (Borders) - APPLY OFFSET HERE
    base_walls = [
        (0, 0, SCREEN_WIDTH, 10 + HUD_OFFSET),  # Top wall, including HUD area
        offset_rect((0, SCREEN_HEIGHT - 10 - HUD_OFFSET, SCREEN_WIDTH, 10)), # Bottom Wall
        offset_rect((0, 0, 10, SCREEN_HEIGHT)), # Left Wall
        offset_rect((SCREEN_WIDTH - 10, 0, 10, SCREEN_HEIGHT)), # Right Wall
        offset_rect((635, 0, 10, SCREEN_HEIGHT)) # Center Divider
    ]

    levels = []

    # --- LEVEL 1: Patience (Sweep) ---
    l1_walls = list(base_walls)
    l1_walls.extend([offset_rect((150, 100, 20, 600)), offset_rect((450, 100, 20, 600))])
    l1_guard1_path = [offset_point((300, 200)), offset_point((300, 200))] 
    l1_guard2_path = [offset_point((300, 500)), offset_point((300, 500))] 
    levels.append({
        "name": "Level 1: Patience Protocol (2 Guards)",
        "briefing": [
            "Objective: Retrieve the Key and return to the Treasure Chest.",
            "P1 (Blue) must navigate the sweeping Guard 1.",
            "P2 (Green) must deactivate Guard 2 by stepping on the purple switch (D2).",
            "D2 is located in the bottom-right corner of P2's side.",
            "P1 can only move past Guard 2 when P2 is actively holding D2."
        ],
        "p1_start": offset_point((300, 620)), "p2_start": offset_point((655, 350)), 
        "key": offset_rect((300, 50, 40, 40)), "chest": offset_rect((250, 620, 40, 40)), 
        "walls": l1_walls,
        "guards": [
            {"x": l1_guard1_path[0][0], "y": l1_guard1_path[0][1], "path": l1_guard1_path, "angle": 90, "id": 1, "speed": 0, "fov": 40, "len": 250, "sweep_speed": 4.5},
            {"x": l1_guard2_path[0][0], "y": l1_guard2_path[0][1], "path": l1_guard2_path, "angle": 270, "id": 2, "speed": 0, "fov": 40, "len": 200, "sweep_speed": 4.5}
        ],
        "deactivators": [
            {"x": offset_point((1100, 600))[0], "y": offset_point((1100, 600))[1], "id": 2, "fake": False}, 
            {"x": offset_point((750, 100))[0], "y": offset_point((750, 100))[1], "id": 1, "fake": False},  
        ],
        "dynamic_walls": [],
        "pressure_plates": [],
        "escape_pod_data": None
    })


    # --- LEVEL 2: Communication Grid (Maze + Real/Fake) ---
    l2_walls = list(base_walls)
    l2_walls.extend([
        offset_rect((0, 200, 400, 20)), offset_rect((200, 450, 430, 20)), offset_rect((100, 350, 20, 100)), offset_rect((500, 150, 20, 100)), 
        offset_rect((700, 150, 20, 400)), offset_rect((850, 280, 20, 400)), offset_rect((1000, 150, 20, 400)), 
        offset_rect((700, 450, 150, 20)), offset_rect((900, 450, 100, 20)), offset_rect((850, 280, 200, 20)), 
    ])
    l2_p2_start = offset_point((750, 50)) 
    l2_guard1_path = [offset_point((50, 300)), offset_point((550, 300))]
    l2_guard2_path = [offset_point((400, 100)), offset_point((400, 400))]
    l2_guard3_path = [offset_point((580, 580)), offset_point((580, 580))]
    levels.append({
        "name": "Level 2: Communication Grid (Fake Switches)",
        "briefing": [
            "Objective: Retrieve the Key and return to the Treasure Chest.",
            "P1 (Blue) must navigate three fast-moving guards.",
            "P2 (Green) must find the 3 real switches (out of 6) to stop the guards.",
            "The fake switches look identical to the real ones.",
            "COMMUNICATION is essential: P1 must guide P2 to the correct switches."
        ],
        "p1_start": offset_point((50, 50)), "p2_start": l2_p2_start,
        "key": offset_rect((550, 610, 40, 40)), "chest": offset_rect((100, 50, 40, 40)), 
        "walls": l2_walls,
        "guards": [
            {"x": l2_guard1_path[0][0], "y": l2_guard1_path[0][1], "path": l2_guard1_path, "angle": 0, "id": 1, "speed": 9, "fov": 45, "len": 100},
            {"x": l2_guard2_path[0][0], "y": l2_guard2_path[0][1], "path": l2_guard2_path, "angle": 90, "id": 2, "speed": 8, "fov": 45, "len": 150},
            {"x": l2_guard3_path[0][0], "y": l2_guard3_path[0][1], "path": l2_guard3_path, "angle": 225, "id": 3, "speed": 0, "fov": 70, "len": 200, "sweep_speed": 2}
        ],
        "deactivators": [
            {"x": offset_point((750, 500))[0], "y": offset_point((750, 500))[1], "id": 1, "fake": False}, 
            {"x": offset_point((790, 400))[0], "y": offset_point((790, 400))[1], "id": 2, "fake": False}, 
            {"x": offset_point((900, 500))[0], "y": offset_point((900, 500))[1], "id": 3, "fake": False},
            {"x": offset_point((1030, 320))[0], "y": offset_point((1030, 320))[1], "id": 4, "fake": True}, 
            {"x": offset_point((900, 200))[0], "y": offset_point((900, 200))[1], "id": 4, "fake": True},
            {"x": offset_point((1100, 150))[0], "y": offset_point((1100, 150))[1], "id": 5, "fake": True},
            {"x": offset_point((1000, 600))[0], "y": offset_point((1000, 600))[1], "id": 6, "fake": True}
        ],
        "dynamic_walls": [],
        "pressure_plates": [],
        "escape_pod_data": None
    })

    # --- LEVEL 3: The Escape Pod Protocol (P1 trapped, P2 moves pod) ---
    l3_walls = list(base_walls)
    
    # Static elements on P1 side (The pod track)
    l3_walls.extend([
        offset_rect((10, 300, 620, 20)), # Top rail
        offset_rect((10, 500, 620, 20)), # Bottom rail
        offset_rect((620, 300, 5, 220)) # End cap (Treasure Chest side)
    ])

    # Dynamic Walls (Trap Walls)
    # DW Link ID 10: P2 initial trap wall (opened by P1 PP1)
    # DW Link ID 11: P1 Escape Pod Trap Walls (closed upon key pickup)
    dynamic_walls = [
        # P2 Initial Trap Wall
        {"rect": offset_rect((900, 50, 20, 250)), "id": 10, "player": "p2"},
        # P1 Escape Pod Trap Walls (start OPEN)
        {"rect": offset_rect((580, 320, 50, 20)), "id": 11, "player": "p1"}, # Left Top
        {"rect": offset_rect((580, 480, 50, 20)), "id": 11, "player": "p1"}, # Left Bottom
    ]
    
    # Guards
    l3_guard1_path = [offset_point((300, 150)), offset_point((500, 150))] 
    l3_guard2_path = [offset_point((400, 600)), offset_point((400, 600))]
    l3_guard3_path = [offset_point((100, 600)), offset_point((100, 600))] 
    
    levels.append({
        "name": "Level 3: The Escape Pod Protocol",
        "briefing": [
            "Challenge: P1 must reach the Key, but will be trapped inside the **Escape Pod**.",
            "P1 starts by finding the **Pressure Plate (PP1)** to free P2.",
            "P2 then uses the **Sync Zones** to move the pod (and P1) to the Chest.",
            "Sync Zone 12 (Left) moves the pod right. Sync Zone 13 (Right) moves the pod left.",
            "P2 must also use the Deactivators (D1-D3) to disable the guards."
        ],
        "p1_start": offset_point((50, 640)),
        "p2_start": offset_point((1200, 50)),
        "key": offset_rect((50, 400, 40, 40)), # Key is inside the initial Escape Pod position
        "chest": offset_rect((550, 400, 40, 40)), 
        "walls": l3_walls,
        "guards": [
            {"x": l3_guard1_path[0][0], "y": l3_guard1_path[0][1], "path": l3_guard1_path, "angle": 0, "id": 1, "speed": 5, "fov": 45, "len": 120}, 
            {"x": l3_guard2_path[0][0], "y": l3_guard2_path[0][1], "path": [offset_point((400, 600))], "angle": 270, "id": 2, "speed": 0, "fov": 70, "len": 180, "sweep_speed": 1.5}, 
            {"x": l3_guard3_path[0][0], "y": l3_guard3_path[0][1], "path": [offset_point((100, 600))], "angle": 0, "id": 3, "speed": 0, "fov": 70, "len": 150, "sweep_speed": 2}, 
        ],
        # 3 Guard Deactivators + 1 P2 trap deactivator + 1 Fake = 5 Total
        "deactivators": [
            {"x": offset_point((700, 600))[0], "y": offset_point((700, 600))[1], "id": 1, "fake": False}, # D1: Stops G1
            {"x": offset_point((1000, 600))[0], "y": offset_point((1000, 600))[1], "id": 2, "fake": False}, # D2: Stops G2
            {"x": offset_point((1200, 600))[0], "y": offset_point((1200, 600))[1], "id": 3, "fake": False}, # D3: Stops G3
            {"x": offset_point((50, 100))[0], "y": offset_point((50, 100))[1], "id": 10, "fake": False}, # PP1: Frees P2 (P1 interacts with this!)
            {"x": offset_point((1100, 100))[0], "y": offset_point((1100, 100))[1], "id": 14, "fake": True}, # Fake Switch
        ],
        "dynamic_walls": dynamic_walls,
        "pressure_plates": [ 
            {"x": offset_point((750, 300))[0], "y": offset_point((750, 300))[1], "id": 12}, # SZ1: Pod Move Right (Link ID 12)
            {"x": offset_point((1150, 300))[0], "y": offset_point((1150, 300))[1], "id": 13} # SZ2: Pod Move Left (Link ID 13)
        ],
        "escape_pod_data": {
            "initial_rect": offset_rect((0, 320, 100, 180)),
            "track_x_min": 10,  # Clamped to the track start
            "track_x_max": 530, # Max movement along the track (just before the end cap)
            "speed": 3 
        }
    })


    return levels

# --- GAME MANAGER ---

class Game:
    def __init__(self):
        self.levels = get_levels()
        self.current_level_idx = 0
        self.state = "MENU"
        self.load_level(self.current_level_idx, initial_load=True)
        
    def load_level(self, idx, initial_load=False):
        if idx >= len(self.levels):
            self.state = "CAMPAIGN_COMPLETE"
            return
            
        self.current_level_idx = idx
        data = self.levels[idx]
        self.level_name = data["name"]
        self.level_briefing = data["briefing"]
        
        # Static Walls
        self.walls = [pygame.Rect(w) for w in data["walls"]]
        
        self.p1 = Player(data["p1_start"][0], data["p1_start"][1], C_P1, 
                         {'up': pygame.K_w, 'down': pygame.K_s, 'left': pygame.K_a, 'right': pygame.K_d}, "p1")
        self.p2 = Player(data["p2_start"][0], data["p2_start"][1], C_P2, 
                         {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT, 'right': pygame.K_RIGHT}, "p2")
        
        self.key_data = data["key"] 
        self.key_rect = pygame.Rect(self.key_data)
        self.chest_rect = pygame.Rect(data["chest"])
        self.p1_has_key = False
        
        self.guards = []
        for g in data["guards"]:
            sweep = g.get("sweep_speed", 0)
            self.guards.append(Guard(g["x"], g["y"], g["path"], g["angle"], g["id"], g["speed"], g["fov"], g["len"], sweep))
            
        self.deactivators = []
        for d_data in data["deactivators"]:
            self.deactivators.append(Deactivator(d_data["x"], d_data["y"], d_data["id"], d_data.get("fake", False)))

        self.sync_zones = []
        for sz_data in data["pressure_plates"]:
            self.sync_zones.append(SyncZone(sz_data["x"], sz_data["y"], sz_data["id"]))

        self.dynamic_walls = {}
        for i, dw_data in enumerate(data.get("dynamic_walls", [])):
            player_obj = self.p1 if dw_data["player"] == "p1" else self.p2
            dw = DynamicWall(dw_data["rect"], dw_data["id"], player_obj)
            
            # --- Initial state for Level 3 dynamic walls ---
            if self.current_level_idx == 2:
                if dw.link_id == 10: # P2 trap wall
                    dw.is_open = False # P2 starts trapped
                elif dw.link_id == 11: # P1 trap walls
                    dw.is_open = True # P1 starts UN-trapped
            
            self.dynamic_walls[i + 1] = {'wall': dw, 'is_open': dw.is_open, 'player': player_obj} 
        
        # Level 3 Specific Setup
        self.escape_pod = None
        if data.get("escape_pod_data"):
            pod_data = data["escape_pod_data"]
            self.escape_pod = pygame.Rect(pod_data["initial_rect"])
            self.pod_speed = pod_data["speed"]
            self.pod_x_min = pod_data["track_x_min"]
            self.pod_x_max = pod_data["track_x_max"]
            

        self.time_limit = None
        self.start_ticks = pygame.time.get_ticks()

        if not initial_load:
             self.state = "BRIEFING" 
    
    def restart_level(self):
        self.load_level(self.current_level_idx)

    def restart_game(self):
        self.current_level_idx = 0
        self.load_level(0, initial_load=True)

    def update(self):
        keys = pygame.key.get_pressed()
        
        # Global Shortcuts (Shift + 1, 2, 3) - kept for development utility
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            if keys[pygame.K_r]: self.restart_game()
            if keys[pygame.K_1]: self.load_level(0)
            if keys[pygame.K_2]: self.load_level(1)
            if keys[pygame.K_3]: self.load_level(2)
            return

        if self.state == "MENU":
            if keys[pygame.K_SPACE]: 
                self.load_level(0) 
        
        elif self.state == "BRIEFING":
            if keys[pygame.K_RETURN]: 
                self.state = "PLAYING"
                self.start_ticks = pygame.time.get_ticks()

        elif self.state == "PLAYING":
            
            # Pass escape_pod to P1 update for clamping if trapped
            self.p1.update(keys, self.walls, self.dynamic_walls, self.escape_pod)
            self.p2.update(keys, self.walls, self.dynamic_walls)

            # --- INTERACTION PROCESSING ---
            active_links = {}

            # 1. Process Deactivators (P2 only, or P1 for Link 10/PP1)
            for d in self.deactivators:
                # P1's PP1 (Link 10) can be triggered by P1
                if d.link_id == 10 and d.rect.colliderect(self.p1.rect):
                    d.is_pressed = True
                # All other deactivators/switches are for P2
                elif d.link_id != 10:
                    d.update(self.p2.rect)
                
                if d.is_pressed and not d.is_fake:
                    active_links[d.link_id] = True
            
            # 2. Process Sync Zones (P2 only)
            for sz in self.sync_zones:
                sz.update(self.p2, self.p2.is_moving())
                if sz.is_active:
                    active_links[sz.link_id] = True

            # 3. Control Dynamic Walls
            for dw_data in self.dynamic_walls.values():
                link_id = dw_data['wall'].link_id
                
                # DW Link 10: P2 trap wall, opened by P1's PP1 (Link 10)
                if link_id == 10:
                    dw_data['is_open'] = active_links.get(10, False)
                    dw_data['wall'].is_open = active_links.get(10, False)
                
                # DW Link 11: P1 trap walls. Control is tied to key pickup. (Level 3 only)
                elif link_id == 11:
                    if self.p1.is_trapped:
                         dw_data['is_open'] = False
                         dw_data['wall'].is_open = False
            
            # 4. Control Guards
            for g in self.guards:
                g.active = not active_links.get(g.link_id, False)
                g.update()
                
                # Check for collision with P1 only
                if g.check_collision(self.p1.rect):
                    # --- Reset Logic ---
                    self.p1.reset() 
                    
                    # If P1 was holding the key, reset key state
                    if self.p1_has_key:
                        self.p1_has_key = False
                        self.key_rect = pygame.Rect(self.key_data)
                        
                        # If trapped (L3), reset P1 trap walls (link 11) to OPEN
                        if self.current_level_idx == 2:
                            for dw_data in self.dynamic_walls.values():
                                if dw_data['wall'].link_id == 11:
                                    dw_data['is_open'] = True
                                    dw_data['wall'].is_open = True
                        self.p1.is_trapped = False
            
            # 5. Check Key (P1 only)
            if not self.p1_has_key and self.p1.rect.colliderect(self.key_rect):
                self.p1_has_key = True
                
                # --- FIX APPLIED HERE: ONLY TRAP P1 IN LEVEL 3 (index 2) ---
                if self.current_level_idx == 2: 
                    self.p1.is_trapped = True # P1 is trapped in the Escape Pod
                
                self.key_rect.topleft = (-100, -100) # Hide key

            # 6. Level 3 Escape Pod Movement Logic
            if self.current_level_idx == 2 and self.escape_pod:
                
                dx = 0
                sz12_active = active_links.get(12, False) # Sync Zone 12 (Move Right)
                sz13_active = active_links.get(13, False) # Sync Zone 13 (Move Left)
                
                # Only allow movement if P1 is trapped inside (Phase 3)
                if self.p1.is_trapped:
                    if sz12_active and not sz13_active:
                        dx = self.pod_speed # Move Right
                    elif sz13_active and not sz12_active:
                        dx = -self.pod_speed # Move Left

                    self.escape_pod.x += dx
                    
                    # Clamp pod to track limits
                    self.escape_pod.x = max(self.pod_x_min, min(self.escape_pod.x, self.pod_x_max))

                    # Move P1 with the pod (This is essential since P1's own movement is disabled)
                    self.p1.rect.x += dx
                    
            # 7. Check Chest Unlock (P1 only)
            # Victory condition is P1 (trapped or not, holding key) reaches the chest.
            if self.p1_has_key and self.p1.rect.colliderect(self.chest_rect):
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
            self.draw_centered_text("DUOS & DON'TS: PROTOCOL SYNC", -50, font_title, C_P1)
            self.draw_centered_text("Press SPACE to Begin Campaign", 50, font_ui)
            self.draw_centered_text("P1 (Blue, WASD) navigates hazards. P2 (Green, Arrows) opens the path.", 100, font_small)
            
        elif self.state == "BRIEFING":
            self.draw_briefing_screen()

        elif self.state in ("PLAYING", "VICTORY"):
            
            # Draw Static Walls
            for wall in self.walls: 
                pygame.draw.rect(screen, C_WALL, wall)
            
            # Draw Escape Pod (if applicable)
            if self.escape_pod:
                pygame.draw.rect(screen, C_ESCAPE_POD, self.escape_pod, border_radius=4)
                pygame.draw.rect(screen, C_ESCAPE_POD, self.escape_pod, 3, border_radius=4) # Draw border
            
            # Draw Dynamic Walls
            for dw_data in self.dynamic_walls.values():
                dw_data['wall'].draw(screen)
            
            # Draw Interactables
            for d in self.deactivators: d.draw(screen)
            for sz in self.sync_zones: sz.draw(screen)
            
            # Draw Key
            if not self.p1_has_key:
                pygame.draw.circle(screen, C_KEY, self.key_rect.center, 20)
                pygame.draw.circle(screen, (0,0,0), self.key_rect.center, 10, 2)
            
            # Draw Treasure Chest
            chest_color = C_CHEST if self.p1_has_key else C_WALL
            lock_color = C_KEY if self.p1_has_key else C_GUARD
            
            pygame.draw.rect(screen, chest_color, self.chest_rect, border_radius=6)
            pygame.draw.rect(screen, (chest_color[0]*0.8, chest_color[1]*0.8, chest_color[2]*0.8), self.chest_rect.inflate(0, -self.chest_rect.height/2), border_radius=6)
            pygame.draw.rect(screen, lock_color, (self.chest_rect.centerx - 4, self.chest_rect.centery + 8, 8, 8), border_radius=2)
            
            # Draw Guards
            for g in self.guards: g.draw(screen)
            
            # Draw Players
            self.p1.draw(screen)
            self.p2.draw(screen)
            
            # HUD
            pygame.draw.rect(screen, C_HUD_BG, (0, 0, SCREEN_WIDTH, HUD_OFFSET))
            
            # Key Status
            key_status_text = "Key: Retrieved" if self.p1_has_key else "Key: Awaiting Retrieval"
            key_status_color = C_KEY if self.p1_has_key else (150, 150, 150)
            status_surf = font_ui.render(key_status_text, True, key_status_color)
            screen.blit(status_surf, (SCREEN_WIDTH - status_surf.get_width() - 20, 15))

            # Level Info 
            screen.blit(font_ui.render(self.level_name, True, C_KEY), (20, 10))

            if self.state == "VICTORY":
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0,0,0,150))
                screen.blit(overlay, (0,0))
                self.draw_centered_text("LEVEL CLEARED - PROTOCOL SYNCED", -30, font_title, C_KEY)
                self.draw_centered_text("Press 'R' for Next Level", 30, font_ui)

        elif self.state == "CAMPAIGN_COMPLETE":
            self.draw_centered_text("PROTOCOL COMPLETE: SUCCESSFUL SYNC", -50, font_title, C_KEY)
            self.draw_centered_text("All levels cleared. Interdependence achieved.", 50, font_ui)
            self.draw_centered_text("Click 'R' to Restart Campaign", 100, font_ui)

        pygame.display.flip()

    def draw_centered_text(self, text, y_off, font, color=C_TEXT):
        surf = font.render(text, True, color)
        rect = surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + y_off))
        screen.blit(surf, rect)

    def draw_briefing_screen(self):
        screen.fill(C_HUD_BG)
        self.draw_centered_text(self.level_name, -300, font_title, C_KEY)

        y_start = SCREEN_HEIGHT // 2 - 200
        
        rules_title = font_ui.render("<< MISSION BRIEFING >>", True, C_P1)
        screen.blit(rules_title, rules_title.get_rect(centerx=SCREEN_WIDTH//2, top=y_start))
        
        y_offset = y_start + 50
        
        for line in self.level_briefing:
            text_surf = font_rules.render(line, True, C_TEXT)
            screen.blit(text_surf, text_surf.get_rect(left=SCREEN_WIDTH//6, top=y_offset)) 
            y_offset += 30
        
        self.draw_centered_text("Press ENTER to Begin Mission", 250, font_ui, C_KEY)


# --- MAIN LOOP EXECUTION ---
if __name__ == '__main__':
    try:
        game = Game()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.K_r: # Handle R outside of game.update for responsiveness
                    if game.state == "PLAYING": game.restart_level()
                    elif game.state == "VICTORY": game.load_level(game.current_level_idx + 1)
                    elif game.state == "CAMPAIGN_COMPLETE": game.restart_game()
                if event.type == pygame.K_RETURN and game.state == "BRIEFING":
                    game.state = "PLAYING"; game.start_ticks = pygame.time.get_ticks()
            
            game.update()
            game.draw()
            clock.tick(FPS)

    except Exception as e:
        print(f"An unexpected error occurred during the game loop: {e}")
    
    finally:
        if pygame.get_init():
            pygame.quit()
        sys.exit(0)