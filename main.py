import pygame
import sys
import math

# Screen settings
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60
HUD_OFFSET = 60

# COLORS
C_BG = (15, 15, 20)          
C_WALL = (100, 110, 130)     
C_P1 = (60, 150, 250)        
C_P2 = (100, 220, 100)       
C_GUARD_DEFAULT = (220, 40, 40) 
C_FIRE = (255, 69, 0)        
C_FIRE_INNER = (255, 200, 0) 
C_GUARD_OFF = (60, 60, 60)   
C_VISION = (255, 0, 0, 80)   
C_KEY = (255, 215, 0)        
C_CHEST = (160, 82, 45)      
C_CHEST_LID = (139, 69, 19)  
C_DEACTIVATOR_DEFAULT = (220, 40, 40) 
C_TEXT = (255, 255, 255)
C_HUD_BG = (30, 30, 40)
C_BUTTON_HOVER = (50, 50, 70)
C_BUTTON_IDLE = (40, 40, 50)
C_TUTORIAL_BOX = (50, 50, 60, 200) 
C_TUTORIAL_BORDER = (200, 200, 200)

# ENGINE SETUP
try:
    pygame.init()
except pygame.error as e:
    print(f"Pygame initialization failed: {e}")
    sys.exit()

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Duos & Don'ts")
clock = pygame.time.Clock()

# Fonts
font_title = pygame.font.SysFont("Arial", 50, bold=True)
font_ui = pygame.font.SysFont("Consolas", 24)
font_small = pygame.font.SysFont("Consolas", 18)
font_rules = pygame.font.SysFont("Consolas", 20)

# HELPERS
def offset_rect(r):
    x, y, w, h = r
    return (x, y + HUD_OFFSET, w, h)

def offset_point(p):
    x, y = p
    return (x, y + HUD_OFFSET)

def draw_visual_key(surface, rect):
    pygame.draw.circle(surface, C_KEY, (rect.x + 10, rect.y + 20), 10)
    pygame.draw.circle(surface, (0,0,0), (rect.x + 10, rect.y + 20), 4)
    pygame.draw.rect(surface, C_KEY, (rect.x + 15, rect.y + 15, 20, 10))
    pygame.draw.rect(surface, C_KEY, (rect.x + 25, rect.y + 25, 5, 10))
    pygame.draw.rect(surface, C_KEY, (rect.x + 32, rect.y + 25, 5, 8))

def draw_visual_chest(surface, rect, is_open):
    pygame.draw.rect(surface, C_CHEST, rect, border_bottom_left_radius=5, border_bottom_right_radius=5)
    lid_rect = pygame.Rect(rect.x, rect.y, rect.width, rect.height // 3)
    pygame.draw.rect(surface, C_CHEST_LID, lid_rect, border_top_left_radius=5, border_top_right_radius=5)
    lock_color = C_KEY if is_open else (50, 50, 50)
    pygame.draw.rect(surface, lock_color, (rect.centerx - 5, rect.centery, 10, 12))

def draw_centered_text(surface, text, y_off, font, color=C_TEXT):
    surf = font.render(text, True, color)
    rect = surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 + y_off))
    surface.blit(surf, rect)

# classes

class TutorialInstruction:
    """Floating box for instructions with state management."""
    def __init__(self, id, text_lines, rect, start_active=False):
        self.id = id
        self.text_lines = text_lines
        self.rect = pygame.Rect(rect)
        self.active = start_active
        self.completed = False
    
    def draw(self, surface):
        if not self.active or self.completed:
            return

        # transparent surface
        s = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
        s.fill(C_TUTORIAL_BOX) # Fill with transparent color
        surface.blit(s, (self.rect.x, self.rect.y))
        
        # Draw Border
        pygame.draw.rect(surface, C_TUTORIAL_BORDER, self.rect, 2, border_radius=8)
        
        y_offset = self.rect.top + 10
        for line in self.text_lines:
            text_surf = font_small.render(line, True, C_TEXT)
            text_rect = text_surf.get_rect(centerx=self.rect.centerx, top=y_offset)
            surface.blit(text_surf, text_rect)
            y_offset += 20

class Player:
    def __init__(self, x, y, color, controls, player_id):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.color = color
        self.controls = controls
        self.speed = 5
        self.start_pos = (x, y)
        self.player_id = player_id 
        self.prev_x = x
        self.prev_y = y
        self.is_frozen = False 
        self.inverted_controls = False

    def update(self, keys, walls):
        # Frozen Logic (P1 specific in context, but generic implementation)
        if self.is_frozen:
            return 

        dx, dy = 0, 0
        speed = self.speed

        # Input Handling with Inversion Logic
        left_key = self.controls['left']
        right_key = self.controls['right']
        up_key = self.controls['up']
        down_key = self.controls['down']

        if self.inverted_controls:
            # Inverted: Left moves Right, Right moves Left
            if keys[left_key]: dx = speed
            if keys[right_key]: dx = -speed
        else:
            # Normal
            if keys[left_key]: dx = -speed
            if keys[right_key]: dx = speed

        if keys[up_key]: dy = -speed
        if keys[down_key]: dy = speed

        self.prev_x = self.rect.x
        self.prev_y = self.rect.y

        current_collidable_walls = walls 
        
        # X Axis Movement & Collision
        self.rect.x += dx
        if self.rect.collidelist(current_collidable_walls) != -1:
            if self.inverted_controls:
                # Penalty: Respawn at start if touching wall while inverted
                self.rect.topleft = self.start_pos
            else:
                self.rect.x -= dx # Standard slide
            
        # Y Axis Movement & Collision
        self.rect.y += dy
        if self.rect.collidelist(current_collidable_walls) != -1:
            if self.inverted_controls:
                # Penalty: Respawn at start if touching wall while inverted
                self.rect.topleft = self.start_pos
            else:
                self.rect.y -= dy

        playable_rect = pygame.Rect(10, 10 + HUD_OFFSET, SCREEN_WIDTH - 20, SCREEN_HEIGHT - 20 - HUD_OFFSET)
        self.rect.clamp_ip(playable_rect)

        if self.player_id == "p1":
            if self.rect.right > 635:
                self.rect.right = 635 
        elif self.player_id == "p2":
            if self.rect.left < 645:
                self.rect.left = 645
            
    def is_moving(self):
        return self.rect.x != self.prev_x or self.rect.y != self.prev_y

    def draw(self, surface):
        draw_color = self.color
        # Visual indicator for Inverted/Frozen states
        if self.inverted_controls:
            draw_color = (255, 100, 255) # Pinkish for confused/inverted
        if self.is_frozen:
            draw_color = (100, 100, 255) # Dark Blue for frozen
            
        pygame.draw.rect(surface, draw_color, self.rect, border_radius=6)
        pygame.draw.circle(surface, (255,255,255), (self.rect.x + 8, self.rect.y + 8), 4)
        pygame.draw.circle(surface, (255,255,255), (self.rect.x + 24, self.rect.y + 8), 4)

    def reset(self):
        self.rect.topleft = self.start_pos
        self.is_frozen = False 
        self.inverted_controls = False

class Guard:
    def __init__(self, x, y, patrol_path, angle_start, link_id, speed=0, fov=60, vision_len=180, sweep_speed=0, color=C_GUARD_DEFAULT):
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
        self.color = color

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
        if self.color == C_FIRE:
            if self.active:
                flicker = (pygame.time.get_ticks() // 100) % 3
                cx, cy = self.rect.centerx, self.rect.bottom
                points_outer = [
                    (cx - 15, cy), (cx - 10, cy - 25 - flicker*2),
                    (cx, cy - 15), (cx + 10, cy - 30 + flicker*2), (cx + 15, cy)
                ]
                pygame.draw.polygon(surface, C_FIRE, points_outer)
                points_inner = [
                    (cx - 8, cy), (cx - 5, cy - 15 - flicker),
                    (cx, cy - 10), (cx + 5, cy - 20 + flicker), (cx + 8, cy)
                ]
                pygame.draw.polygon(surface, C_FIRE_INNER, points_inner)
            else:
                pygame.draw.ellipse(surface, C_GUARD_OFF, (self.rect.x, self.rect.bottom - 10, 32, 10))
        else:
            draw_color = self.color if self.active else C_GUARD_OFF
            pygame.draw.rect(surface, draw_color, self.rect, border_radius=4)
        
        if self.active:
            rad = math.radians(-self.current_angle)
            center = self.rect.center
            l_rad = rad - math.radians(self.fov / 2); lx = center[0] + math.cos(l_rad) * self.vision_length; ly = center[1] + math.sin(l_rad) * self.vision_length
            r_rad = rad + math.radians(self.fov / 2); rx = center[0] + math.cos(r_rad) * self.vision_length; ry = center[1] + math.sin(r_rad) * self.vision_length

            cone_color = list(self.color) + [80] 
            cone_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            pygame.draw.polygon(cone_surf, cone_color, [center, (lx, ly), (rx, ry)])
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
    def __init__(self, x, y, link_id, is_fake=False, color=C_DEACTIVATOR_DEFAULT):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.link_id = link_id
        self.is_pressed = False
        self.is_fake = is_fake 
        self.base_color = color

    def update(self, player_rect):
        self.is_pressed = self.rect.colliderect(player_rect)

    def draw(self, surface):
        if self.is_pressed and not self.is_fake:
            color = (150, 255, 150) # Green when active
            frame_color = (50, 0, 50)
        else:
            color = self.base_color 
            if self.base_color == C_GUARD_DEFAULT:
                 frame_color = (150, 20, 20)
            else:
                 frame_color = (max(0, self.base_color[0]-50), max(0, self.base_color[1]-50), max(0, self.base_color[2]-50))
            
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, frame_color, self.rect.inflate(-10, -10), border_radius=4)
        if self.is_pressed:
             pygame.draw.circle(surface, (255, 255, 255), self.rect.center, 5)

# Level defs

def get_levels():
    
    base_walls = [
        (0, 0, SCREEN_WIDTH, 10 + HUD_OFFSET), 
        offset_rect((0, SCREEN_HEIGHT - 10 - HUD_OFFSET, SCREEN_WIDTH, 10)), 
        offset_rect((0, 0, 10, SCREEN_HEIGHT)), 
        offset_rect((SCREEN_WIDTH - 10, 0, 10, SCREEN_HEIGHT)), 
        offset_rect((635, 0, 10, SCREEN_HEIGHT)) 
    ]

    levels = []

    # level 0: tutorial
    l0_walls = list(base_walls)
    l0_walls.append(offset_rect((150, 100, 20, 600)))
    l0_walls.append(offset_rect((450, 0, 20, 520)))
    
    levels.append({
        "name": "Level 0: Tutorial",
        "briefing": [
            "Welcome to Duos & Don'ts.",
            "Player 1 - Blue: Navigate the maze, collect the key, and open the chest.",
            "Player 2 - Green: No role in this level.",
        ],
        "p1_start": offset_point((70, 540)), "p2_start": offset_point((1230, 30)), 
        "key": offset_rect((300, 580, 40, 40)), "chest": offset_rect((550, 50, 40, 40)), 
        "walls": l0_walls,
        "guards": [],
        "deactivators": [],
        "instructions": [
            # player 1 instructions
            {"id": "p1_wasd", "lines": ["Use the WASD", "keys to navigate"], "rect": offset_rect((20, 580, 200, 60)), "start_active": True},
            {"id": "p1_key", "lines": ["Collect the key"], "rect": offset_rect((350, 580, 200, 40)), "start_active": True},
            {"id": "p1_chest", "lines": ["Unlock the", "treasure chest"], "rect": offset_rect((345, 50, 200, 60)), "start_active": False},
            
            # Player 2: Instructions
            {"id": "p2_arrows", "lines": ["Use the Arrow", "keys to navigate"], "rect": offset_rect((1060, 80, 200, 60)), "start_active": True},
            {"id": "p2_no_role", "lines": ["You don't have any", " roles in this level"], "rect": offset_rect((850, 320, 240, 60)), "start_active": True},
        ],
    })

    # Level 1: with obstacles
    l1_walls = list(base_walls)
    l1_walls.append(offset_rect((150, 100, 20, 600)))
    l1_walls.append(offset_rect((450, 0, 20, 520)))
    
    l1_guard1_path = [offset_point((300, 200)), offset_point((300, 200))] 
    l1_guard2_path = [offset_point((300, 500)), offset_point((300, 500))] 
    
    # INSTRUCTION COORDINATES
    P1_ZONE_YELLOW_RECT_DATA = (180, 250, 465, 400) # Area Player 1 enters after first obstacle
    P1_ZONE_PINK_RECT_DATA = (510, 400, 465, 200)   # Area Player 1 enters after second obstacle
    P1_HINT_TOP = (400, 80)       # P1 Hint position near Top Guard
    P1_HINT_BOTTOM = (440, 495)    # P1 Hint position near Bottom Guard
    P2_HINT_TOP = (950, 120)       # P2 Hint position near Top Deactivator
    P2_HINT_BOTTOM = (920, 620)   # P2 Hint position near Bottom Deactivator
    
    levels.append({
        "name": "Level 1",
        "briefing": [
            "Blue (WASD): Avoid obstacles. P2 controls your path.",
            "Green (Arrows): Step on Matching Buttons to disable Obstacles.",
            "Communicate where the obstacles are and which button P2 needs.",
        ],
        "p1_start": offset_point((70, 620)), "p2_start": offset_point((655, 350)), 
        "key": offset_rect((300, 580, 40, 40)), "chest": offset_rect((550, 50, 40, 40)), 
        "walls": l1_walls,
        "guards": [
            # Top Guard (Guard 1)
            {"x": l1_guard1_path[0][0], "y": l1_guard1_path[0][1], "path": l1_guard1_path, "angle": 90, "id": 1, "speed": 0, "fov": 60, "len": 250, "sweep_speed": 5, "color": C_GUARD_DEFAULT},
            # Bottom Guard (Guard 2)
            {"x": l1_guard2_path[0][0], "y": l1_guard2_path[0][1], "path": l1_guard2_path, "angle": 270, "id": 2, "speed": 0, "fov": 40, "len": 200, "sweep_speed": 5, "color": C_GUARD_DEFAULT}
        ],
        "deactivators": [
            # Deactivator for Top Guard
            {"x": offset_point((750, 100))[0], "y": offset_point((750, 100))[1], "id": 1, "fake": False, "color": C_GUARD_DEFAULT},  
            # Deactivator for Bottom Guard
            {"x": offset_point((1100, 600))[0], "y": offset_point((1100, 600))[1], "id": 2, "fake": False, "color": C_GUARD_DEFAULT}, 
        ],
        "instructions": [
            # P1 instructions
            {"id": "p1_guard", "lines": ["Stay clear", "of the guards"], "rect": offset_rect(P1_HINT_TOP + (200, 60)), "start_active": True},
            {"id": "p1_key", "lines": ["Collect the key"], "rect": offset_rect((370, 550, 200, 40)), "start_active": False},
            
            # P2 instructions
            {"id": "p2_deact_move", "lines": ["Hover over the deactivator", "to disable the obstacles"], "rect": offset_rect(P2_HINT_TOP + (300, 60)), "start_active": True},
        ],
        # instruction logic
        "custom_data": {
            "p1_zone_yellow_rect": P1_ZONE_YELLOW_RECT_DATA,
            "p1_zone_pink_rect": P1_ZONE_PINK_RECT_DATA,
            "p1_hint_top": P1_HINT_TOP,
            "p1_hint_bottom": P1_HINT_BOTTOM,
            "p2_hint_top": P2_HINT_TOP,
            "p2_hint_bottom": P2_HINT_BOTTOM,
        }
    })
    
# Level 2
    l2_walls = list(base_walls)
    l2_walls.extend([
        offset_rect((0, 200, 400, 20)), offset_rect((200, 450, 430, 20)), offset_rect((100, 280, 20, 100)), offset_rect((500, 150, 20, 100)), 
        offset_rect((700, 150, 20, 400)), offset_rect((850, 280, 20, 400)), offset_rect((1000, 150, 20, 400)), 
        offset_rect((700, 450, 150, 20)), offset_rect((900, 450, 100, 20)), offset_rect((850, 280, 200, 20)), 
    ])
    l2_p2_start = offset_point((750, 50)) 
    l2_guard1_path = [offset_point((200, 300)), offset_point((550, 300))]
    l2_guard2_path = [offset_point((400, 100)), offset_point((400, 300))]
    l2_guard3_path = [offset_point((580, 580)), offset_point((580, 580))]
    
    levels.append({
        "name": "Level 2",
        "briefing": [
            "Player 1 must navigate fast-moving guards.",
            "Player 2 must find the correct colored switches.",
            "Communicate efficiently."
        ],
        "p1_start": offset_point((50, 50)), "p2_start": l2_p2_start,
        "key": offset_rect((550, 610, 40, 40)), "chest": offset_rect((100, 50, 40, 40)), 
        "walls": l2_walls,
        "guards": [
            {"x": l2_guard1_path[0][0], "y": l2_guard1_path[0][1], "path": l2_guard1_path, "angle": 0, "id": 1, "speed": 18, "fov": 45, "len": 100, "color": C_GUARD_DEFAULT},
            {"x": l2_guard2_path[0][0], "y": l2_guard2_path[0][1], "path": l2_guard2_path, "angle": 90, "id": 2, "speed": 12, "fov": 45, "len": 150, "color": C_GUARD_DEFAULT},
            {"x": l2_guard3_path[0][0], "y": l2_guard3_path[0][1], "path": l2_guard3_path, "angle": 225, "id": 3, "speed": 0, "fov": 70, "len": 200, "sweep_speed": 2.5, "color": C_GUARD_DEFAULT},
        ],
        "deactivators": [
            # real deactivators
            {"x": offset_point((750, 500))[0], "y": offset_point((750, 500))[1], "id": 1, "fake": False, "color": C_GUARD_DEFAULT}, 
            {"x": offset_point((790, 400))[0], "y": offset_point((790, 400))[1], "id": 2, "fake": False, "color": C_GUARD_DEFAULT}, 
            {"x": offset_point((900, 500))[0], "y": offset_point((900, 500))[1], "id": 3, "fake": False, "color": C_GUARD_DEFAULT},
            #Fake deactivators
            {"x": offset_point((1030, 320))[0], "y": offset_point((1030, 320))[1], "id": 4, "fake": True, "color": C_GUARD_DEFAULT}, 
            {"x": offset_point((900, 200))[0], "y": offset_point((900, 200))[1], "id": 4, "fake": True, "color": C_GUARD_DEFAULT},
            {"x": offset_point((1100, 150))[0], "y": offset_point((1100, 150))[1], "id": 5, "fake": True, "color": C_GUARD_DEFAULT},
        ],
        "instructions": [
            {"id": "l2_p2_fake", "lines": ["There are 3 real ", "deactivators", "and 3 fake ones"], "rect": offset_rect((1050, 30, 210, 72)), "start_active": True},
        ],
    })

    # Level 3
    l3_walls = list(base_walls)
    # walls for P1
    l3_walls.append(offset_rect((200, 120, 200, 20)))   # Top/Mid divider
    l3_walls.append(offset_rect((135, 480, 500, 20))) # Mid/Bot divider
    l3_walls.append(offset_rect((200, 0, 20, 120))) # wall b/w p1 origin and treasure chest
    l3_walls.append(offset_rect((500, 500, 20, 80))) # wall near key
    
    # Walls for P2
    l3_walls.append(offset_rect((800, 200, 20, 300))) # middle vertical wall 1
    l3_walls.append(offset_rect((1000, 100, 20, 320))) # middle vertical wall 2
    l3_walls.append(offset_rect((800, 400, 200, 20))) # middle horizontal wall
    l3_walls.append(offset_rect((1000, 550, 20, 100))) # wall to the right of bottom fake deactivator
    l3_walls.append(offset_rect((1170, 100, 150, 20))) # wall below antifreeze switch
    l3_walls.append(offset_rect((1170, 120, 20, 90))) # wall near top fake deactivator
    l3_walls.append(offset_rect((900, 550, 20, 100))) # wall to the left of bottom fake deactivator
    l3_walls.append(offset_rect((640, 100, 150, 20))) # wall below top real deactivator

    # guard locations
    l3_guard1_path = [offset_point((570, 620)), offset_point((570, 620))] # key guard
    l3_guard2_path = [offset_point((100, 90)), offset_point((100, 90))] # treasure chest guard
    l3_guard3_p2_path = [offset_point((400, 100)), offset_point((400, 600))] # wandering guard

    levels.append({
        "name": "Level 3",
        "briefing": [
            "Beware of FAKE deactivators!",
            "If Player 2 contacts a fake deactivator, Player 1 FREEZES and Player 2's controls INVERT.",
            "To cure: P2 must reach the cyan Antifreeze switch.",
            "If Player 2 hits a wall while trapped, they respawn at the origin."
        ],
        "p1_start": offset_point((250, 50)), 
        "p2_start": offset_point((640, 620)), 
        "key": offset_rect((580, 500, 40, 40)), # In middle section
        "chest": offset_rect((50, 50, 40, 40)), # In top section
        "walls": l3_walls,
        "guards": [
            # P1 Gatekeepers
            {"x": l3_guard1_path[0][0], "y": l3_guard1_path[0][1], "path": l3_guard1_path, "angle": 90, "id": 1, "speed": 0, "sweep_speed": 4, "fov": 70, "len": 150, "color": C_GUARD_DEFAULT}, # key guard
            {"x": l3_guard2_path[0][0], "y": l3_guard2_path[0][1], "path": l3_guard2_path, "angle": 140, "id": 2, "speed": 0, "sweep_speed": 6, "fov": 90, "len": 150, "color": C_GUARD_DEFAULT}, # treasure chest guard
            {"x": l3_guard3_p2_path[0][0], "y": l3_guard3_p2_path[0][1], "path": l3_guard3_p2_path, "angle": 90, "id": 3, "speed": 8, "fov": 60, "len": 150, "color": C_GUARD_DEFAULT}, # wandering guard
        ],
        "deactivators": [
            # Real deactivator
            {"x": offset_point((660, 40))[0], "y": offset_point((660, 40))[1], "id": 1, "fake": False, "color": C_DEACTIVATOR_DEFAULT}, # top deactivator
            {"x": offset_point((1220, 135))[0], "y": offset_point((1220, 135))[1], "id": 2, "fake": False, "color": C_DEACTIVATOR_DEFAULT}, # below antifreeze switch
            {"x": offset_point((900, 350))[0], "y": offset_point((900, 350))[1], "id": 3, "fake": False, "color": C_DEACTIVATOR_DEFAULT}, # middle deactivator
            # Fake deactivator
            {"x": offset_point((1030, 300))[0], "y": offset_point((1030, 300))[1], "id": 999, "fake": True, "color": C_DEACTIVATOR_DEFAULT}, # top
            {"x": offset_point((940, 600))[0], "y": offset_point((940, 600))[1], "id": 999, "fake": True, "color": C_DEACTIVATOR_DEFAULT}, # bottom
            # Antifreeze switch
            {"x": offset_point((1220, 30))[0], "y": offset_point((1220, 30))[1], "id": 888, "fake": True, "color": (0, 255, 255)},
        ],
        "instructions": [
             {"id": "l3_hint", "lines": ["Beware of the fake", "Deactivators"], "rect": offset_rect((860, 30, 220, 60)), "start_active": True},
        ]
    })

    return levels

# game manager

class Game:
    def __init__(self):
        self.levels = get_levels()
        self.current_level_idx = 0
        self.state = "MAIN_MENU"
        self.menu_buttons = [
            {"text": "Tutorial", "level_idx": 0, "rect": pygame.Rect(SCREEN_WIDTH//2 - 100, 270, 200, 50)},
            {"text": "Level 1", "level_idx": 1, "rect": pygame.Rect(SCREEN_WIDTH//2 - 100, 340, 200, 50)},
            {"text": "Level 2", "level_idx": 2, "rect": pygame.Rect(SCREEN_WIDTH//2 - 100, 410, 200, 50)},
            {"text": "Level 3", "level_idx": 3, "rect": pygame.Rect(SCREEN_WIDTH//2 - 100, 480, 200, 50)}
        ]
        
        self.p1_passed_obs1 = False
        self.p1_passed_obs2 = False

        self.load_level(self.current_level_idx, initial_load=True)
        
    def load_level(self, idx, initial_load=False):
        if idx >= len(self.levels):
            self.state = "CAMPAIGN_COMPLETE"
            return
            
        self.current_level_idx = idx
        data = self.levels[idx]
        self.level_name = data["name"]
        self.level_briefing = data["briefing"]
        self.walls = [pygame.Rect(w) for w in data["walls"]]
        
        p1_controls = {'up': pygame.K_w, 'down': pygame.K_s, 'left': pygame.K_a, 'right': pygame.K_d}
        
        self.p1 = Player(data["p1_start"][0], data["p1_start"][1], C_P1, p1_controls, "p1")
        self.p2 = Player(data["p2_start"][0], data["p2_start"][1], C_P2, {'up': pygame.K_UP, 'down': pygame.K_DOWN, 'left': pygame.K_LEFT, 'right': pygame.K_RIGHT}, "p2")
        self.key_data = data["key"] 
        self.key_rect = pygame.Rect(self.key_data)
        self.chest_rect = pygame.Rect(data["chest"])
        self.p1_has_key = False
        
        self.guards = []
        for g in data["guards"]:
            self.guards.append(Guard(g["x"], g["y"], g["path"], g["angle"], g["id"], g["speed"], g["fov"], g["len"], g.get("sweep_speed",0), g.get("color", C_GUARD_DEFAULT)))
            
        self.deactivators = []
        for d_data in data["deactivators"]:
            self.deactivators.append(Deactivator(d_data["x"], d_data["y"], d_data["id"], d_data.get("fake", False), d_data.get("color", C_DEACTIVATOR_DEFAULT)))

        self.p1_zone_yellow = None
        self.p1_zone_pink = None
        
        # instruction set up
        self.tutorial_instructions = []
        for instr in data.get("instructions", []):
            self.tutorial_instructions.append(
                TutorialInstruction(instr["id"], instr["lines"], instr["rect"], instr.get("start_active", False))
            )

        if data.get("custom_data"):
            custom_data = data["custom_data"]
            if custom_data.get("p1_zone_yellow_rect"):
                self.p1_zone_yellow = pygame.Rect(offset_rect(custom_data["p1_zone_yellow_rect"]))
            if custom_data.get("p1_zone_pink_rect"):
                self.p1_zone_pink = pygame.Rect(offset_rect(custom_data["p1_zone_pink_rect"]))

        # Reset Level 1 progression flags on load/restart
        self.p1_passed_obs1 = False
        self.p1_passed_obs2 = False

        self.time_limit = None
        self.start_ticks = pygame.time.get_ticks()

        if not initial_load: self.state = "BRIEFING" 
    
    def restart_level(self):
        # The load_level function handles resetting the level state and instruction flags
        self.load_level(self.current_level_idx)

    def restart_game(self):
        self.state = "MAIN_MENU"

    def handle_menu_click(self, pos):
        for btn in self.menu_buttons:
            if btn["rect"].collidepoint(pos):
                self.load_level(btn["level_idx"])
                return

    def update(self):
        keys = pygame.key.get_pressed()
        
        if self.state == "MAIN_MENU":
            pass

        elif self.state == "BRIEFING":
            pass

        elif self.state == "PLAYING":
            self.p1.update(keys, self.walls)
            self.p2.update(keys, self.walls)

            # instruction logic for level 1
            if self.current_level_idx == 1:
                
                custom_data = self.levels[self.current_level_idx]["custom_data"]
                P1_HINT_TOP = custom_data["p1_hint_top"]
                P1_HINT_BOTTOM = custom_data["p1_hint_bottom"]
                P2_HINT_TOP = custom_data["p2_hint_top"]
                P2_HINT_BOTTOM = custom_data["p2_hint_bottom"]

                p1_guard_instr = next((i for i in self.tutorial_instructions if i.id == "p1_guard"), None)
                p2_deact_instr = next((i for i in self.tutorial_instructions if i.id == "p2_deact_move"), None)
                
                # Check for yellow zone - whether P1 has passed the first obstacle
                if not self.p1_passed_obs1 and self.p1_zone_yellow and self.p1.rect.colliderect(self.p1_zone_yellow):
                    self.p1_passed_obs1 = True
                
                # If the first obstacle is passed, check for the Pink Zone (Obstacle 2 cleared) - USES RECT COLLISION
                if self.p1_passed_obs1 and not self.p1_passed_obs2 and self.p1_zone_pink and self.p1.rect.colliderect(self.p1_zone_pink):
                    self.p1_passed_obs2 = True

                if p1_guard_instr and p2_deact_instr:
                    
                    if not self.p1_passed_obs1:
                        # STATE 1: At the start (Left lane or top crossing area)
                        # Hints focus on Top Obstacle
                        p1_guard_instr.active = True
                        p1_guard_instr.rect.center = offset_point(P1_HINT_TOP)
                        p2_deact_instr.active = True
                        p2_deact_instr.rect.center = offset_point(P2_HINT_TOP)

                    elif self.p1_passed_obs1 and not self.p1_passed_obs2:
                        # STATE 2: Passed first obstacle (Yellow Zone), approaching second (Pink Zone)
                        # Hints focus on Bottom Obstacle
                        p1_guard_instr.active = True
                        p1_guard_instr.rect.center = offset_point(P1_HINT_BOTTOM)
                        p2_deact_instr.active = True
                        p2_deact_instr.rect.center = offset_point(P2_HINT_BOTTOM)

                    elif self.p1_passed_obs2:
                        # STATE 3: Passed both obstacles (Pink Zone)
                        # Hints disappear
                        p1_guard_instr.active = False
                        p2_deact_instr.active = False

            # TUTORIAL LOGIC UPDATE
            elif self.current_level_idx == 0:
                # Level 0: Key Instruction removed when key collected
                p1_key_instr = next((i for i in self.tutorial_instructions if i.id == "p1_key"), None)
                if p1_key_instr and self.p1_has_key:
                    p1_key_instr.completed = True


            active_links = {}
            for d in self.deactivators:
                if self.current_level_idx == 0: continue
                
                d.update(self.p2.rect)
                
                if d.is_pressed:
                    # CHECK FOR SPECIAL TRAP SWITCHES
                    if d.link_id == 999: # TRAP
                        self.p1.is_frozen = True
                        self.p1.is_trapped = True # Keep existing flag for guards potentially
                        self.p2.inverted_controls = True
                    
                    # CHECK FOR CURE SWITCH
                    elif d.link_id == 888: # CURE
                        self.p1.is_frozen = False
                        self.p1.is_trapped = False
                        self.p2.inverted_controls = False
                    
                    elif not d.is_fake: 
                        active_links[d.link_id] = True
            
            for g in self.guards:
                g.active = not active_links.get(g.link_id, False)
                g.update()
                
                # COLLISION & RESPAWN LOGIC 
                if g.check_collision(self.p1.rect):
                    self.p1.reset() 
                    
                    # If P1 respawns, reset progression flags for Level 1 logic
                    if self.current_level_idx == 1:
                         self.p1_passed_obs1 = False
                         self.p1_passed_obs2 = False
                    
                    if self.p1_has_key:
                        self.p1_has_key = False
                        self.key_rect = pygame.Rect(self.key_data)
                        self.p1.is_trapped = False
            
            if not self.p1_has_key and self.p1.rect.colliderect(self.key_rect):
                self.p1_has_key = True
                
                # Activate P1 Chest Instruction (L0/L1)
                p1_chest_instr = next((i for i in self.tutorial_instructions if i.id == "p1_chest"), None)
                if p1_chest_instr: p1_chest_instr.active = True
                self.key_rect.topleft = (-100, -100) 

            if self.p1_has_key and self.p1.rect.colliderect(self.chest_rect):
                self.state = "VICTORY"

        elif self.state == "VICTORY":
            if keys[pygame.K_r]: self.restart_level()
                
        elif self.state == "CAMPAIGN_COMPLETE":
            if keys[pygame.K_r]: self.restart_game()


    def draw(self):
        screen.fill(C_BG)
        
        if self.state == "MAIN_MENU":
            self.draw_main_menu()
            
        elif self.state == "BRIEFING":
            self.draw_briefing_screen()

        elif self.state in ("PLAYING", "VICTORY"):
            for wall in self.walls: pygame.draw.rect(screen, C_WALL, wall)
            for d in self.deactivators: d.draw(screen)
            
            if not self.p1_has_key:
                draw_visual_key(screen, self.key_rect)
            
            draw_visual_chest(screen, self.chest_rect, self.p1_has_key)
            
            for g in self.guards: g.draw(screen)
            self.p1.draw(screen); self.p2.draw(screen)
            
            # DRAW TUTORIAL BOXES
            for instruction in self.tutorial_instructions:
                instruction.draw(screen)

            pygame.draw.rect(screen, C_HUD_BG, (0, 0, SCREEN_WIDTH, HUD_OFFSET))
            key_status_text = "Key: Retrieved" if self.p1_has_key else "Key: Awaiting Retrieval"
            key_status_color = C_KEY if self.p1_has_key else (150, 150, 150)
            status_surf = font_ui.render(key_status_text, True, key_status_color)
            screen.blit(status_surf, (SCREEN_WIDTH - status_surf.get_width() - 20, 15))
            screen.blit(font_ui.render(self.level_name, True, C_KEY), (20, 10))
            
            # Playing UI Hint
            if self.state == "PLAYING":
                restart_text = font_small.render("Press 'R' to Restart Level", True, (100, 100, 120))
                screen.blit(restart_text, (SCREEN_WIDTH // 2 - restart_text.get_width() // 2, 15))

            if self.state == "VICTORY":
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0,0,0,150))
                screen.blit(overlay, (0,0))
                draw_centered_text(screen, "LEVEL CLEARED", -30, font_title, C_KEY)
                draw_centered_text(screen, "Press 'ENTER' for Next Level", 30, font_ui)
                draw_centered_text(screen, "Press 'R' to Replay Level", 70, font_small)

        elif self.state == "CAMPAIGN_COMPLETE":
            draw_centered_text(screen, "All levels cleared!", 50, font_ui)
            draw_centered_text(screen, "Click 'M' to Return to Menu", 100, font_ui)

        pygame.display.flip()

    def draw_main_menu(self):
        draw_centered_text(screen, "DUOS & DON'TS", -250, font_title, C_P1)
        
        mouse_pos = pygame.mouse.get_pos()
        for btn in self.menu_buttons:
            color = C_BUTTON_HOVER if btn["rect"].collidepoint(mouse_pos) else C_BUTTON_IDLE
            pygame.draw.rect(screen, color, btn["rect"], border_radius=10)
            pygame.draw.rect(screen, C_TEXT, btn["rect"], 2, border_radius=10)
            text_surf = font_ui.render(btn["text"], True, C_TEXT)
            screen.blit(text_surf, text_surf.get_rect(center=btn["rect"].center))
    
        nav_text = "For easy navigation click SHIFT + [Level number]"
        nav_surf = font_small.render(nav_text, True, (150, 150, 150))
        screen.blit(nav_surf, nav_surf.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT - 50)))


    def draw_briefing_screen(self):
        screen.fill(C_HUD_BG)
        draw_centered_text(screen, self.level_name, -300, font_title, C_KEY)
        y_start = SCREEN_HEIGHT // 2 - 200
        rules_title = font_ui.render("<< MISSION BRIEFING >>", True, C_P1)
        screen.blit(rules_title, rules_title.get_rect(centerx=SCREEN_WIDTH//2, top=y_start))
        y_offset = y_start + 50
        for line in self.level_briefing:
            text_surf = font_rules.render(line, True, C_TEXT)
            screen.blit(text_surf, text_surf.get_rect(left=SCREEN_WIDTH//6, top=y_offset)) 
            y_offset += 30
        draw_centered_text(screen, "Press ENTER to Begin Mission", 250, font_ui, C_KEY)


# MAIN LOOP EXECUTION
if __name__ == '__main__':
    try:
        game = Game()
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running = False
                
                if event.type == pygame.KEYDOWN:
                    mods = pygame.key.get_mods()
                    if mods & pygame.KMOD_SHIFT:
                        if event.key == pygame.K_0: game.load_level(0) 
                        elif event.key == pygame.K_1: game.load_level(1) 
                        elif event.key == pygame.K_2: game.load_level(2)
                        elif event.key == pygame.K_3: game.load_level(3)

                # --- M Key for Main Menu ---
                if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
                    game.state = "MAIN_MENU" 

                if event.type == pygame.MOUSEBUTTONDOWN and game.state == "MAIN_MENU":
                    game.handle_menu_click(event.pos)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r: 
                        if game.state == "PLAYING": game.restart_level()
                        elif game.state == "VICTORY": game.restart_level()
                        elif game.state == "CAMPAIGN_COMPLETE": game.restart_game()
                    if event.key == pygame.K_RETURN:
                         if game.state == "BRIEFING":
                            game.state = "PLAYING"; game.start_ticks = pygame.time.get_ticks()
                         elif game.state == "VICTORY":
                            game.load_level(game.current_level_idx + 1)
            
            game.update()
            game.draw()
            clock.tick(FPS)

    except Exception as e:
        print(f"An unexpected error occurred during the game loop: {e}")
    
    finally:
        if pygame.get_init():
            pygame.quit()
        sys.exit(0)