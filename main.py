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
C_GOAL = (255, 215, 0)       # Treasure Gold
C_DEACTIVATOR = (200, 100, 200) # Purple Switches (Used for both real and fake, when not pressed)
C_TEXT = (255, 255, 255)
C_HUD_BG = (30, 30, 40)
C_DYNAMIC_WALL = (165, 42, 42) # Brown-Red for Walls P2 must open
C_PRESSURE_PLATE = (255, 165, 0) # Orange Plate

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
font_small = pygame.font.SysFont("Consolas", 16)

# --- CLASSES ---

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

    def update(self, keys, walls, dynamic_walls_state):
        dx, dy = 0, 0
        if keys[self.controls['up']]: dy = -self.speed
        if keys[self.controls['down']]: dy = self.speed
        if keys[self.controls['left']]: dx = -self.speed
        if keys[self.controls['right']]: dx = self.speed

        # Store previous position for movement check in SyncZone logic
        self.prev_x = self.rect.x
        self.prev_y = self.rect.y

        # Move X
        self.rect.x += dx
        
        # Check collision with static walls and currently closed dynamic walls
        # Must extract the Rect object from the dynamic wall dictionary item
        # The filter checks if the wall belongs to THIS player's collision space
        current_walls = walls + [dw['wall'].rect for dw in dynamic_walls_state.values() if not dw['is_open'] and dw['player'] == self]
        if self.rect.collidelist(current_walls) != -1:
            self.rect.x -= dx
            
        # Move Y
        self.rect.y += dy
        if self.rect.collidelist(current_walls) != -1:
            self.rect.y -= dy

        # Clamp to screen boundaries (accounting for HUD_OFFSET)
        playable_rect = pygame.Rect(10, 10 + HUD_OFFSET, SCREEN_WIDTH - 20, SCREEN_HEIGHT - 20 - HUD_OFFSET)
        self.rect.clamp_ip(playable_rect)

        # Boundary Enforcement (P2 must stay right of the divider, P1 must stay left)
        reset_required = False
        if self.player_id == "p1":
            # P1 (Left side) checks if they crossed right of the divider (x=640)
            if self.rect.right > 640:
                reset_required = True
        elif self.player_id == "p2":
            # P2 (Right side) checks if they crossed left of the divider (x=645)
            if self.rect.left < 645:
                reset_required = True
        
        if reset_required:
            self.reset()
            
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

class Guard:
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

        # 1. Patrol Movement (Physical)
        # FIX: Check self.speed > 0 to prevent float division by zero when speed is 0
        if self.speed > 0 and self.patrol_path and len(self.patrol_path) > 1:
            target = self.patrol_path[self.current_point]
            tx, ty = target
            dir_x, dir_y = tx - self.rect.x, ty - self.rect.y
            dist = math.hypot(dir_x, dir_y)
            
            if dist < self.speed:
                # Arrived or overshot, snap to target and move to next point
                self.rect.x = tx
                self.rect.y = ty
                self.current_point = (self.current_point + 1) % len(self.patrol_path)
            else:
                # Normal movement (dist is guaranteed > 0 here because speed > 0)
                self.rect.x += (dir_x / dist) * self.speed
                self.rect.y += (dir_y / dist) * self.speed
                if self.sweep_speed == 0:
                    self.base_angle = -math.degrees(math.atan2(dir_y, dir_x))

        # 2. Vision Sweeping (Rotation)
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
            # Draw Vision Cone
            rad = math.radians(-self.current_angle)
            center = self.rect.center
            
            l_rad = rad - math.radians(self.fov / 2)
            lx = center[0] + math.cos(l_rad) * self.vision_length
            ly = center[1] + math.sin(l_rad) * self.vision_length
            
            r_rad = rad + math.radians(self.fov / 2)
            rx = center[0] + math.cos(r_rad) * self.vision_length
            ry = center[1] + math.sin(r_rad) * self.vision_length

            cone_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(cone_surf, C_VISION, [center, (lx, ly), (rx, ry)])
            surface.blit(cone_surf, (0,0))

    def check_collision(self, player_rect):
        """Returns True if player hits body OR vision cone."""
        if not self.active: return False
        
        # 1. Body Collision
        if self.rect.colliderect(player_rect):
            return True

        # 2. Vision Cone Collision
        points = [player_rect.topleft, player_rect.topright, player_rect.bottomleft, player_rect.bottomright]
        
        for px, py in points:
            dx = px - self.rect.centerx
            dy = py - self.rect.centery
            dist = math.hypot(dx, dy)
            
            if dist <= self.vision_length:
                # Check if the player point is within the FOV angle
                angle_to_point = -math.degrees(math.atan2(dy, dx))
                diff = (angle_to_point - self.current_angle + 180) % 360 - 180
                if abs(diff) < self.fov / 2:
                    return True
        return False

class Deactivator:
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
            frame_color = (50,0,50)
        else:
            color = C_DEACTIVATOR 
            frame_color = (80, 50, 80)
            
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, frame_color, self.rect.inflate(-10, -10))

class DynamicWall:
    def __init__(self, rect_data, link_id, player_owner):
        self.rect = pygame.Rect(rect_data)
        self.link_id = link_id
        self.is_open = False
        self.player_owner = player_owner 

    def draw(self, surface):
        if not self.is_open:
            pygame.draw.rect(surface, C_DYNAMIC_WALL, self.rect, border_radius=2)
            if self.rect.width > self.rect.height:
                 pygame.draw.line(surface, C_WALL, self.rect.topleft, self.rect.bottomright, 3)
                 pygame.draw.line(surface, C_WALL, self.rect.topright, self.rect.bottomleft, 3)
            else:
                 pygame.draw.line(surface, C_WALL, self.rect.topleft, self.rect.bottomright, 3)
                 pygame.draw.line(surface, C_WALL, self.rect.topright, self.rect.bottomleft, 3)

class SyncZone: 
    def __init__(self, x, y, link_id):
        self.rect = pygame.Rect(x, y, 50, 50)
        self.link_id = link_id
        self.is_active = False 

    def update(self, player, is_player_moving):
        is_colliding = self.rect.colliderect(player.rect)
        self.is_active = is_colliding and is_player_moving

    def draw(self, surface):
        color = (255, 200, 0) if self.is_active else C_PRESSURE_PLATE
        pygame.draw.rect(surface, color, self.rect, border_radius=12)
        pygame.draw.rect(surface, (100, 50, 0), self.rect.inflate(-10, -10))


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
        (0, 0, SCREEN_WIDTH, 10 + HUD_OFFSET), 
        offset_rect((0, SCREEN_HEIGHT - 10 - HUD_OFFSET, SCREEN_WIDTH, 10)), 
        offset_rect((0, 0, 10, SCREEN_HEIGHT)), 
        offset_rect((SCREEN_WIDTH - 10, 0, 10, SCREEN_HEIGHT)), 
        offset_rect((635, 0, 10, SCREEN_HEIGHT)) # Center Divider
    ]

    levels = []

    # --- LEVEL 1: Patience (Sweep) ---
    l1_walls = list(base_walls)
    l1_walls.extend([
        offset_rect((150, 100, 20, 500)), 
        offset_rect((450, 100, 20, 500))  
    ])
    
    l1_guard1_path = [offset_point((300, 200)), offset_point((300, 200))] 
    l1_guard2_path = [offset_point((300, 500)), offset_point((300, 500))] 
    
    levels.append({
        "name": "Level 1: Patience Protocol (2 Guards)",
        "desc": "P1 must wait for Guard 1's sweep AND P2 must deactivate Guard 2. Both switches needed.",
        "p1_start": offset_point((300, 650)),
        "p2_start": offset_point((700, 350)),
        "goal": offset_rect((300, 50, 40, 40)), 
        "walls": l1_walls,
        "guards": [
            {"x": l1_guard1_path[0][0], "y": l1_guard1_path[0][1], "path": l1_guard1_path, "angle": 90, "id": 1, "speed": 0, "fov": 40, "len": 250, "sweep_speed": 1.5},
            {"x": l1_guard2_path[0][0], "y": l1_guard2_path[0][1], "path": l1_guard2_path, "angle": 270, "id": 2, "speed": 0, "fov": 40, "len": 200, "sweep_speed": 1.5}
        ],
        "deactivators": [
            {"x": offset_point((1100, 600))[0], "y": offset_point((1100, 600))[1], "id": 2, "fake": False}, 
            {"x": offset_point((750, 100))[0], "y": offset_point((750, 100))[1], "id": 1, "fake": False}, 
        ],
        "dynamic_walls": [],
        "pressure_plates": []
    })


    # --- LEVEL 2: Communication Grid (Maze + Real/Fake) ---
    l2_walls = list(base_walls)
    l2_walls.extend([
        offset_rect((0, 200, 400, 20)),
        offset_rect((200, 450, 430, 20)),
        offset_rect((700, 100, 20, 300)),
        offset_rect((850, 400, 20, 310)),
        offset_rect((1000, 100, 20, 400)),
        offset_rect((1150, 300, 20, 400)),
        offset_rect((700, 500, 300, 20)),
    ])
    
    l2_guard1_path = [offset_point((50, 300)), offset_point((550, 300))]
    l2_guard2_path = [offset_point((400, 100)), offset_point((400, 400))]
    l2_guard3_path = [offset_point((580, 580)), offset_point((580, 580))]
    
    levels.append({
        "name": "Level 2: Communication Grid (Fake Switches)",
        "desc": "P1 must guide P2 to the 3 real switches (out of 6) to stop the fast-moving guards.",
        "p1_start": offset_point((50, 50)),
        "p2_start": offset_point((700, 50)),
        "goal": offset_rect((550, 650, 40, 40)),
        "walls": l2_walls,
        "guards": [
            {"x": l2_guard1_path[0][0], "y": l2_guard1_path[0][1], "path": l2_guard1_path, "angle": 0, "id": 1, "speed": 7, "fov": 45, "len": 100},
            {"x": l2_guard2_path[0][0], "y": l2_guard2_path[0][1], "path": l2_guard2_path, "angle": 90, "id": 2, "speed": 6, "fov": 45, "len": 150},
            {"x": l2_guard3_path[0][0], "y": l2_guard3_path[0][1], "path": l2_guard3_path, "angle": 225, "id": 3, "speed": 0, "fov": 70, "len": 200, "sweep_speed": 2}
        ],
        "deactivators": [
            {"x": offset_point((750, 600))[0], "y": offset_point((750, 600))[1], "id": 1, "fake": False},
            {"x": offset_point((900, 100))[0], "y": offset_point((900, 100))[1], "id": 2, "fake": False},
            {"x": offset_point((1200, 650))[0], "y": offset_point((1200, 650))[1], "id": 3, "fake": False},
            # Fake Switches
            {"x": offset_point((800, 450))[0], "y": offset_point((800, 450))[1], "id": 4, "fake": True},
            {"x": offset_point((1100, 150))[0], "y": offset_point((1100, 150))[1], "id": 5, "fake": True},
            {"x": offset_point((1000, 600))[0], "y": offset_point((1000, 600))[1], "id": 6, "fake": True}
        ],
        "dynamic_walls": [],
        "pressure_plates": []
    })

    # --- LEVEL 3: Interdependence (Sync Zone + Dynamic Wall) ---
    l3_walls = list(base_walls)
    
    l3_walls.extend([
        offset_rect((750, 100, 20, 500)),
        offset_rect((900, 400, 370, 20)),
        offset_rect((1050, 200, 20, 400)),
    ])
    
    dynamic_walls = [
        {"rect": offset_rect((250, 350, 150, 20)), "id": 1, "player": "p1"}
    ]

    l3_guard1_path = [offset_point((100, 200)), offset_point((100, 500))]
    l3_guard2_path = [offset_point((500, 200)), offset_point((500, 200))]
    l3_guard3_path = [offset_point((400, 150)), offset_point((200, 150))]
    
    levels.append({
        "name": "Level 3: Interdependence (Sync Zone)",
        "desc": "P1 needs 2 switches and P2 must constantly move inside the Orange Sync Zone to open a critical wall.",
        "p1_start": offset_point((50, 650)),
        "p2_start": offset_point((1200, 50)),
        "goal": offset_rect((550, 50, 40, 40)),
        "walls": l3_walls,
        "guards": [
            {"x": l3_guard1_path[0][0], "y": l3_guard1_path[0][1], "path": l3_guard1_path, "angle": 90, "id": 1, "speed": 5, "fov": 60, "len": 180},
            {"x": l3_guard2_path[0][0], "y": l3_guard2_path[0][1], "path": l3_guard2_path, "angle": 270, "id": 2, "speed": 0, "fov": 60, "len": 180, "sweep_speed": 1.5},
            {"x": l3_guard3_path[0][0], "y": l3_guard3_path[0][1], "path": l3_guard3_path, "angle": 0, "id": 3, "speed": 8, "fov": 45, "len": 120},
        ],
        "deactivators": [
            {"x": offset_point((1200, 100))[0], "y": offset_point((1200, 100))[1], "id": 1, "fake": False}, 
            {"x": offset_point((700, 300))[0], "y": offset_point((700, 300))[1], "id": 2, "fake": False}, 
            {"x": offset_point((1000, 600))[0], "y": offset_point((1000, 600))[1], "id": 3, "fake": True},
        ],
        "dynamic_walls": dynamic_walls,
        "pressure_plates": [ 
            {"x": offset_point((980, 50))[0], "y": offset_point((980, 50))[1], "id": 1} 
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
        if idx >= len(self.levels):
            self.state = "CAMPAIGN_COMPLETE"
            return
            
        self.current_level_idx = idx
        data = self.levels[idx]
        self.level_name = data["name"]
        self.level_desc = data["desc"]
        
        self.walls = [pygame.Rect(w) for w in data["walls"]]
        
        self.p1 = Player(data["p1_start"][0], data["p1_start"][1], C_P1, 
                        {'up': pygame.K_w, 'down': pygame.K_s, 'left': pygame.K_a, 'right': pygame.K_d}, "p1")
        self.p2 = Player(data["p2_start"][0], data["p2_start"][1], C_P2, 
                        {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT, 'right': pygame.K_RIGHT}, "p2")
        
        self.goal_rect = pygame.Rect(data["goal"])
        
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
        for dw_data in data["dynamic_walls"]:
            player_obj = self.p1 if dw_data["player"] == "p1" else self.p2
            dw = DynamicWall(dw_data["rect"], dw_data["id"], player_obj)
            self.dynamic_walls[dw.link_id] = {'wall': dw, 'is_open': False, 'player': player_obj}
        
        self.time_limit = None
        self.start_ticks = pygame.time.get_ticks()
        self.state = "PLAYING" 

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
                self.load_level(0)
                self.state = "PLAYING"
                self.start_ticks = pygame.time.get_ticks()

        elif self.state == "PLAYING":
            
            self.p1.update(keys, self.walls, self.dynamic_walls)
            self.p2.update(keys, self.walls, self.dynamic_walls)

            p2_is_moving = self.p2.is_moving()
            
            active_links = {}
            for d in self.deactivators:
                d.update(self.p2.rect)
                if d.is_pressed and not d.is_fake:
                    active_links[d.link_id] = True
            
            for sz in self.sync_zones: 
                sz.update(self.p2, p2_is_moving) 
                if sz.is_active: 
                    active_links[sz.link_id] = True

            for link_id, dw_data in self.dynamic_walls.items():
                dw_data['is_open'] = active_links.get(link_id, False)
                
            for g in self.guards:
                g.active = not active_links.get(g.link_id, False)
                g.update()
                
                if g.check_collision(self.p1.rect):
                    self.p1.reset() 
            
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
            
            for wall in self.walls: 
                pygame.draw.rect(screen, C_WALL, wall)
            
            for dw_data in self.dynamic_walls.values():
                dw_data['wall'].draw(screen)
            
            for d in self.deactivators: d.draw(screen)
            for sz in self.sync_zones: sz.draw(screen)
            
            pygame.draw.rect(screen, C_GOAL, self.goal_rect, border_radius=10)
            
            for g in self.guards: g.draw(screen)
            
            self.p1.draw(screen)
            self.p2.draw(screen)
            
            # HUD
            pygame.draw.rect(screen, C_HUD_BG, (0, 0, SCREEN_WIDTH, HUD_OFFSET))
            screen.blit(font_ui.render(self.level_name, True, C_GOAL), (20, 10))
            screen.blit(font_small.render(self.level_desc, True, (200,200,200)), (20, 35))
            
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

# --- MAIN LOOP EXECUTION ---
if __name__ == '__main__':
    try:
        game = Game()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        if game.state == "PLAYING":
                            game.restart_level()
                        elif game.state == "VICTORY":
                            game.update()
                        elif game.state == "CAMPAIGN_COMPLETE":
                            game.update()

            game.update()
            game.draw()
            clock.tick(FPS)

    except Exception as e:
        print(f"An unexpected error occurred during the game loop: {e}")
    
    finally:
        if pygame.get_init():
            pygame.quit()
        sys.exit()