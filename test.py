import pygame
import sys
import math
import random
import asyncio

# Screen settings
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 80
HUD_OFFSET = 60

# COLORS
C_BG = (15, 15, 20)          
C_WALL = (100, 110, 130)
C_WALL_DANGER = (200, 50, 50)
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
font_title = pygame.font.Font("assets/OpenSans-Bold.ttf", 50)
font_ui = pygame.font.Font("assets/Inconsolata-Regular.ttf", 24)
font_small = pygame.font.Font("assets/Inconsolata-Regular.ttf", 18)
font_rules = pygame.font.Font("assets/Inconsolata-Regular.ttf", 20)

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
        self.is_trapped = False
        self.inverted_controls = False

    def update(self, keys, walls):
        # Frozen Logic
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
            draw_color = (255, 100, 255) # Pink
        if self.is_frozen:
            draw_color = (100, 100, 255) # purple for frozen
            
        pygame.draw.rect(surface, draw_color, self.rect, border_radius=6)
        pygame.draw.circle(surface, (255,255,255), (self.rect.x + 8, self.rect.y + 8), 4)
        pygame.draw.circle(surface, (255,255,255), (self.rect.x + 24, self.rect.y + 8), 4)

    def reset(self):
        self.rect.topleft = self.start_pos
        self.is_frozen = False 
        self.is_trapped = False
        self.inverted_controls = False

class Guard:
    def __init__(self, x, y, patrol_path, angle_start, link_id, speed=0, fov=60, vision_len=180, sweep_speed=0, color=C_GUARD_DEFAULT, target="p1", hidden_cone=False, hidden_body=False, rotate=False, random_patrol=False, pause_frames=0):
        self.rect = pygame.Rect(x, y, 32, 32)
        self.target = target          # which player this guard catches ("p1" or "p2")
        self.hidden_cone = hidden_cone # Level 6: cone exists but is not drawn on the field
        self.hidden_body = hidden_body # Level 7: body is invisible too (radar still shows it)
        self.rotate = rotate          # Level 7: cone revolves continuously instead of oscillating
        self.random_patrol = random_patrol # Level 4: picks its next waypoint at random
        self.pause_frames = pause_frames   # frames to wait at each waypoint
        self.pause_left = 0
        self.frozen = False           # Level 7: switch-frozen (stops moving/rotating, still detects)
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
        self.cone_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

        # PRE-RENDERING SURFACES
        if self.color == C_FIRE:
            self.fire_frames = []
            # We create 3 different frames for the flickering effect
            for flicker in range(3):
                # Flames are taller than the rect, so we make a taller surface
                frame = pygame.Surface((32, 45), pygame.SRCALPHA)
                cx, cy = 16, 45 # Local center-bottom of the frame
                
                # Draw outer flame (same math as your draw loop, but local)
                pts_out = [(cx-15, cy), (cx-10, cy-25-flicker*2), (cx, cy-15), (cx+10, cy-30+flicker*2), (cx+15, cy)]
                pygame.draw.polygon(frame, C_FIRE, pts_out)
                
                # Draw inner flame
                pts_in = [(cx-8, cy), (cx-5, cy-15-flicker), (cx, cy-10), (cx+5, cy-20+flicker), (cx+8, cy)]
                pygame.draw.polygon(frame, C_FIRE_INNER, pts_in)
                
                self.fire_frames.append(frame)
        else:
            # Pre-render the standard Guard body
            self.image_on = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.rect(self.image_on, self.color, (0, 0, self.rect.width, self.rect.height), border_radius=4)
            
            # Pre-render the "Deactivated" Guard body
            self.image_off = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            pygame.draw.rect(self.image_off, C_GUARD_OFF, (0, 0, self.rect.width, self.rect.height), border_radius=4)

        # Vision cone optimization (keeping your small surface fix)
        box_size = self.vision_length * 2
        self.cone_surf = pygame.Surface((box_size, box_size), pygame.SRCALPHA)

    def update(self):
        if not self.active: return
        if self.frozen: return  # Level 7: a frozen guard stops moving and rotating (still detects)

        factor = 0.5 if getattr(self, "calmed", False) else 1.0  # Level 5: partner-on-pad calm

        if self.speed > 0 and self.patrol_path and len(self.patrol_path) > 1:
            if self.pause_left > 0:
                self.pause_left -= 1
            else:
                target = self.patrol_path[self.current_point]
                tx, ty = target
                dir_x, dir_y = tx - self.rect.x, ty - self.rect.y
                dist = math.hypot(dir_x, dir_y)
                step = self.speed * factor

                if dist < step:
                    self.rect.x = tx
                    self.rect.y = ty
                    if self.random_patrol:
                        self.pause_left = self.pause_frames
                        choices = [i for i in range(len(self.patrol_path)) if i != self.current_point]
                        self.current_point = random.choice(choices)
                    else:
                        self.current_point = (self.current_point + 1) % len(self.patrol_path)
                else:
                    self.rect.x += (dir_x / dist) * step
                    self.rect.y += (dir_y / dist) * step
                    if self.sweep_speed == 0 and self.fov < 360:
                        self.base_angle = -math.degrees(math.atan2(dir_y, dir_x))

        if self.rotate:
            # Level 7: lighthouse beam, slow continuous revolution
            self.sweep_offset = (self.sweep_offset + self.sweep_speed * factor) % 360
            self.current_angle = self.base_angle + self.sweep_offset
        elif self.sweep_speed != 0:
            self.sweep_offset += self.sweep_speed * factor
            if abs(self.sweep_offset) > 45: 
                self.sweep_speed *= -1
            self.current_angle = self.base_angle + self.sweep_offset
        else:
            self.current_angle = self.base_angle

    def draw(self, surface):
        # Level 7: fully invisible guard. Freezing it reveals a faint ghost as the reward.
        if self.hidden_body:
            if self.frozen and self.active:
                ghost = pygame.Surface(self.rect.size, pygame.SRCALPHA)
                pygame.draw.rect(ghost, (140, 220, 235, 90), (0, 0, self.rect.width, self.rect.height), border_radius=4)
                pygame.draw.rect(ghost, (140, 220, 235, 160), (0, 0, self.rect.width, self.rect.height), 2, border_radius=4)
                surface.blit(ghost, self.rect)
                # Faint outline of the locked beam so P1 can route around it with confidence
                self.cone_surf.fill((0, 0, 0, 0))
                local_center = (self.vision_length, self.vision_length)
                rad = math.radians(-self.current_angle)
                l_rad = rad - math.radians(self.fov/2); lx = local_center[0] + math.cos(l_rad)*self.vision_length; ly = local_center[1] + math.sin(l_rad)*self.vision_length
                r_rad = rad + math.radians(self.fov/2); rx = local_center[0] + math.cos(r_rad)*self.vision_length; ry = local_center[1] + math.sin(r_rad)*self.vision_length
                pygame.draw.polygon(self.cone_surf, (140, 220, 235, 35), [local_center, (lx, ly), (rx, ry)])
                pygame.draw.lines(self.cone_surf, (140, 220, 235, 90), True, [local_center, (lx, ly), (rx, ry)], 1)
                surface.blit(self.cone_surf, (self.rect.centerx - self.vision_length, self.rect.centery - self.vision_length))
            return

        # Telegraph for the random patrol: a faint line to its next destination
        if self.random_patrol and self.active and self.patrol_path:
            tx, ty = self.patrol_path[self.current_point]
            dest = (tx + self.rect.width // 2, ty + self.rect.height // 2)
            pygame.draw.line(surface, (200, 90, 90), self.rect.center, dest, 1)
            pygame.draw.circle(surface, (200, 90, 90), (int(dest[0]), int(dest[1])), 4, 1)

        # 1. DRAW THE BODY (Blitting the pre-rendered images)
        if self.color == C_FIRE:
            if self.active:
                flicker_idx = (pygame.time.get_ticks() // 100) % 3
                # Blit the pre-rendered fire frame
                # Offset Y slightly so it sits on the floor correctly
                surface.blit(self.fire_frames[flicker_idx], (self.rect.x, self.rect.bottom - 45))
            else:
                # Still draw the simple ellipse for "off" fire
                pygame.draw.ellipse(surface, C_GUARD_OFF, (self.rect.x, self.rect.bottom - 10, 32, 10))
        else:
            # Blit the correct pre-rendered guard image
            img = self.image_on if self.active else self.image_off
            surface.blit(img, self.rect)
            if getattr(self, "calmed", False) and self.active:
                pygame.draw.rect(surface, (110, 170, 255), self.rect, 2, border_radius=4)

        # 2. DRAW THE DETECTION AREA
        if self.active and self.color != C_FIRE and not self.hidden_cone:
            if self.fov >= 360:
                # Aura guard: an unambiguous circle, no cone to misread
                aura = pygame.Surface((self.vision_length * 2, self.vision_length * 2), pygame.SRCALPHA)
                pygame.draw.circle(aura, list(self.color) + [45], (self.vision_length, self.vision_length), self.vision_length)
                pygame.draw.circle(aura, list(self.color) + [120], (self.vision_length, self.vision_length), self.vision_length, 2)
                surface.blit(aura, (self.rect.centerx - self.vision_length, self.rect.centery - self.vision_length))
            else:
                self.cone_surf.fill((0, 0, 0, 0)) 
                local_center = (self.vision_length, self.vision_length)
                
                rad = math.radians(-self.current_angle)
                l_rad = rad - math.radians(self.fov/2); lx = local_center[0] + math.cos(l_rad)*self.vision_length; ly = local_center[1] + math.sin(l_rad)*self.vision_length
                r_rad = rad + math.radians(self.fov/2); rx = local_center[0] + math.cos(r_rad)*self.vision_length; ry = local_center[1] + math.sin(r_rad)*self.vision_length
                
                cone_alpha = 50 if getattr(self, "calmed", False) else 80
                pygame.draw.polygon(self.cone_surf, list(self.color)+[cone_alpha], [local_center, (lx, ly), (rx, ry)])
                surface.blit(self.cone_surf, (self.rect.centerx - self.vision_length, self.rect.centery - self.vision_length))

    def check_collision(self, player_rect):
        if not self.active: return False
        if self.rect.colliderect(player_rect): return True

        points = [player_rect.topleft, player_rect.topright, player_rect.bottomleft, player_rect.bottomright]
        for px, py in points:
            dx = px - self.rect.centerx; dy = py - self.rect.centery; dist = math.hypot(dx, dy)
            if dist <= self.vision_length:
                if self.fov >= 360: return True
                angle_to_point = -math.degrees(math.atan2(dy, dx))
                diff = (angle_to_point - self.current_angle + 180) % 360 - 180
                if abs(diff) < self.fov / 2: return True
        return False

class Deactivator:
    def __init__(self, x, y, link_id, is_fake=False, color=C_DEACTIVATOR_DEFAULT, user="p2", hold_time=0.0, cooldown=0.0):
        self.rect = pygame.Rect(x, y, 40, 40)
        self.link_id = link_id
        self.is_pressed = False
        self.is_fake = is_fake 
        self.base_color = color
        self.user = user            # which player can operate this switch ("p1" or "p2")
        self.hold_time = hold_time  # seconds of continuous hold needed before it activates (Level 5)
        self.cooldown = cooldown    # seconds the switch is dead after being released (Level 5)
        self.charge_start = None
        self.cooldown_until = 0
        self.revealed = False       # Level 6: fake switches get marked once triggered

    def update(self, player_rect):
        now = pygame.time.get_ticks()
        colliding = self.rect.colliderect(player_rect)

        # Switch is dead during cooldown
        if self.cooldown > 0 and now < self.cooldown_until:
            self.charge_start = None
            self.is_pressed = False
            return

        if colliding:
            if self.hold_time > 0:
                # Charge-up switch: needs a continuous hold before it flips
                if self.charge_start is None:
                    self.charge_start = now
                self.is_pressed = (now - self.charge_start) >= self.hold_time * 1000
            else:
                self.is_pressed = True
        else:
            # Releasing an active charge switch starts its cooldown
            if self.is_pressed and self.cooldown > 0:
                self.cooldown_until = now + self.cooldown * 1000
            self.charge_start = None
            self.is_pressed = False

    def draw(self, surface):
        now = pygame.time.get_ticks()
        in_cooldown = self.cooldown > 0 and now < self.cooldown_until

        if in_cooldown:
            color = (70, 70, 80)
            frame_color = (40, 40, 50)
        elif self.is_pressed and not self.is_fake:
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

        # Charge progress fill while a hold switch is charging
        if self.hold_time > 0 and self.charge_start is not None and not self.is_pressed:
            frac = min(1.0, (now - self.charge_start) / (self.hold_time * 1000))
            fill_h = int(self.rect.height * frac)
            fill_rect = pygame.Rect(self.rect.x, self.rect.bottom - fill_h, self.rect.width, fill_h)
            s = pygame.Surface((fill_rect.width, fill_rect.height), pygame.SRCALPHA)
            s.fill((255, 255, 160, 140))
            surface.blit(s, fill_rect.topleft)

        # Cooldown countdown
        if in_cooldown:
            secs = max(0, (self.cooldown_until - now) // 1000 + 1)
            t = font_small.render(str(secs), True, (220, 220, 220))
            surface.blit(t, t.get_rect(center=self.rect.center))

        if self.is_pressed:
             pygame.draw.circle(surface, (255, 255, 255), self.rect.center, 5)

        # A triggered fake (Level 6) stays marked so the pair can learn the layout
        if self.is_fake and self.revealed:
            pygame.draw.line(surface, (255, 60, 60), self.rect.topleft, self.rect.bottomright, 4)
            pygame.draw.line(surface, (255, 60, 60), self.rect.topright, self.rect.bottomleft, 4)

class Gate:
    """A wall segment that is solid until its linked switch(es) are held (Level 4+).
    needs: how many switches with this link must be held at once (Level 5 sync gates use 2).
    latch: once opened, stays open permanently (progress made together doesn't un-happen)."""
    def __init__(self, rect, link_id, needs=1, latch=False):
        self.rect = pygame.Rect(rect)
        self.link_id = link_id
        self.needs = needs
        self.latch = latch
        self.is_open = False

    def draw(self, surface):
        if self.is_open:
            # Faint outline so players still see where the gate sits
            pygame.draw.rect(surface, (90, 160, 90), self.rect, 2)
        else:
            pygame.draw.rect(surface, (225, 150, 40), self.rect)
            pygame.draw.rect(surface, (140, 90, 20), self.rect, 2)
            # Hazard dashes
            if self.rect.width >= self.rect.height:
                for x in range(self.rect.x + 6, self.rect.right - 6, 18):
                    pygame.draw.line(surface, (140, 90, 20), (x, self.rect.y + 3), (x + 8, self.rect.bottom - 3), 2)
            else:
                for y in range(self.rect.y + 6, self.rect.bottom - 6, 18):
                    pygame.draw.line(surface, (140, 90, 20), (self.rect.x + 3, y), (self.rect.right - 3, y + 8), 2)

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
        "briefing_p1": [
            "Navigate the maze using the WASD keys.",
            "",
            "Collect the key.",
            "",
            "Open the chest to win."
        ],
        "briefing_p2": [
            "No role in this level.",
            "",
            "Sit back and watch.",
            "",
            "Use the arrow keys to move around."
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
    # p1 walls
    l1_walls.append(offset_rect((150, 100, 20, 600)))
    l1_walls.append(offset_rect((450, 0, 20, 520)))
    # p2 walls
    l1_walls.append(offset_rect((640, 200, 500, 20)))
    l1_walls.append(offset_rect((800, 500, 500, 20)))

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
        "name": "Level 1: Easy",
        "briefing_p1": [
            "Avoid contact with the obstacles (guards).",
            "",
            "Wait for P2 to deactivate the obstacles."
        ],
        "briefing_p2": [
            "Use the arrow keys to move around.",
            "",
            "Disable obstacles for P1",
            "by hovering over the deactivators."
        ],
        "p1_start": offset_point((70, 620)), "p2_start": offset_point((655, 350)), 
        "key": offset_rect((300, 580, 40, 40)), "chest": offset_rect((550, 50, 40, 40)), 
        "walls": l1_walls,
        "guards": [
            # Top Guard
            {"x": l1_guard1_path[0][0], "y": l1_guard1_path[0][1], "path": l1_guard1_path, "angle": 90, "id": 1, "speed": 0, "fov": 60, "len": 250, "sweep_speed": 5, "color": C_GUARD_DEFAULT},
            # Bottom Guard
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
        "name": "Level 2: Medium",
        "briefing_p1": [
            "Navigate fast-moving guards.",
            "",
            "Reach the chest.",
            "",
            "Be patient while P2 looks", 
            "for the correct deactivator"
        ],
        "briefing_p2": [
            "There are fake deactivators here.",
            "",
            "Find correct ones to disable the obstacles."
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
    l3_walls.append(offset_rect((200, 120, 340, 20)))   # Top/Mid divider
    l3_walls.append(offset_rect((135, 480, 500, 20))) # Mid/Bot divider
    l3_walls.append(offset_rect((200, 0, 20, 120))) # wall b/w p1 origin and treasure chest
    l3_walls.append(offset_rect((500, 500, 20, 80))) # wall near key
    l3_walls.append(offset_rect((400, 250, 20, 250))) # middle vertical wall
    l3_walls.append(offset_rect((520, 140, 20, 200))) # right vertical wall
    l3_walls.append(offset_rect((260, 140, 20, 200))) # left vertical wall
    l3_walls.append(offset_rect((130, 320, 20, 180))) # left vertical wall
    
    # Walls for P2
    l3_walls.append(offset_rect((800, 200, 20, 300))) # middle vertical wall 1
    l3_walls.append(offset_rect((1000, 100, 20, 320))) # middle vertical wall 2
    l3_walls.append(offset_rect((800, 400, 200, 20))) # middle horizontal wall
    l3_walls.append(offset_rect((1000, 550, 20, 100))) # wall to the right of bottom fake deactivator
    l3_walls.append(offset_rect((1170, 100, 150, 20))) # wall below antifreeze switch
    l3_walls.append(offset_rect((1170, 120, 20, 90))) # wall near top fake deactivator
    l3_walls.append(offset_rect((900, 550, 20, 100))) # wall to the left of bottom fake deactivator
    l3_walls.append(offset_rect((640, 100, 150, 20))) # wall below top real deactivator
    l3_walls.append(offset_rect((1000, 300, 135, 20))) # wall near middle real deactivator

    # guard locations
    l3_guard1_path = [offset_point((570, 620)), offset_point((570, 620))] # key guard
    l3_guard2_path = [offset_point((100, 90)), offset_point((100, 90))] # treasure chest guard
    l3_guard3_p2_path = [offset_point((550, 100)), offset_point((50, 580))] # wandering guard

    levels.append({
        "name": "Level 3: HARD",
        "briefing_p1": [
            "Avoid guards.",
            "",
            "If P2 hits a fake switch, you FREEZE",
            "",
            "Wait for the P2 to",
            "bring the game back to normal."
        ],

        "briefing_p2": [
            "Some deactivators are FAKE.",
            "",
            "If you hit a fake one:",
            " - P1 freezes",
            " - Your controls invert (left <-> right)",
            " - If you touch any wall, you respawn",
            "",
            "Reach the CYAN switch to",
            "bring the game back to normal."
        ],
        "p1_start": offset_point((250, 50)), 
        "p2_start": offset_point((640, 620)), 
        "key": offset_rect((580, 500, 40, 40)), # In middle section
        "chest": offset_rect((50, 50, 40, 40)), # In top section
        "walls": l3_walls,
        "guards": [
            # guards
            {"x": l3_guard1_path[0][0], "y": l3_guard1_path[0][1], "path": l3_guard1_path, "angle": 90, "id": 1, "speed": 0, "sweep_speed": 0, "fov": 60, "len": 150, "color": C_GUARD_DEFAULT}, # key guard
            {"x": l3_guard2_path[0][0], "y": l3_guard2_path[0][1], "path": l3_guard2_path, "angle": 140, "id": 2, "speed": 0, "sweep_speed": 6, "fov": 90, "len": 150, "color": C_GUARD_DEFAULT}, # treasure chest guard
            {"x": l3_guard3_p2_path[0][0], "y": l3_guard3_p2_path[0][1], "path": l3_guard3_p2_path, "angle": 90, "id": 3, "speed": 14, "fov": 60, "len": 150, "color": C_GUARD_DEFAULT}, # wandering guard
        ],
        "deactivators": [
            # Real deactivator
            {"x": offset_point((660, 40))[0], "y": offset_point((660, 40))[1], "id": 1, "fake": False, "color": C_DEACTIVATOR_DEFAULT}, # top deactivator
            {"x": offset_point((1220, 135))[0], "y": offset_point((1220, 135))[1], "id": 2, "fake": False, "color": C_DEACTIVATOR_DEFAULT}, # below antifreeze switch
            {"x": offset_point((900, 350))[0], "y": offset_point((900, 350))[1], "id": 3, "fake": False, "color": C_DEACTIVATOR_DEFAULT}, # middle deactivator
            # Fake deactivator
            {"x": offset_point((1030, 340))[0], "y": offset_point((1030, 340))[1], "id": 999, "fake": True, "color": C_DEACTIVATOR_DEFAULT}, # top
            {"x": offset_point((940, 600))[0], "y": offset_point((940, 600))[1], "id": 999, "fake": True, "color": C_DEACTIVATOR_DEFAULT}, # bottom
            # Antifreeze switch
            {"x": offset_point((1220, 30))[0], "y": offset_point((1220, 30))[1], "id": 888, "fake": True, "color": (0, 255, 255)},
        ],
        "instructions": [
             {"id": "l3_hint", "lines": ["Beware of the fake", "Deactivators"], "rect": offset_rect((1030, 570, 220, 60)), "start_active": True},
        ]
    })

    # Level 4: Hand in Hand (mutual dependence + turn taking)
    # Gates (orange) are solid until the PARTNER holds the linked switch.
    # P1 operates the BLUE switches (open P2's gates), P2 operates the red ones.
    # No backups: a deadlock means restarting and coordinating better.
    # A slow aura "warden" wanders the plaza switches at random, telegraphing its
    # next stop with a line, so P2's switch-holds must be timed around it.
    l4_walls = list(base_walls)
    # P1 side: three horizontal rows
    l4_walls.append(offset_rect((10, 440, 470, 20)))   # bottom/mid divider (gate G1 fills the right gap)
    l4_walls.append(offset_rect((160, 220, 475, 20)))  # mid/top divider (gate G2 fills the left gap)
    l4_walls.append(offset_rect((300, 240, 20, 150)))  # middle row weave wall (hangs from divider)
    l4_walls.append(offset_rect((450, 330, 20, 130)))  # middle row weave wall (rises from divider)
    l4_walls.append(offset_rect((180, 460, 20, 120)))  # bottom row weave (hangs)
    l4_walls.append(offset_rect((340, 530, 20, 120)))  # bottom row weave (rises)
    l4_walls.append(offset_rect((360, 10, 20, 140)))   # top row split (gate G5 fills the lower gap)
    # P2 side: left strip, two weave walls, open plaza right, split top rooms
    l4_walls.append(offset_rect((800, 240, 465, 20)))  # top/bottom divider (gate G3 fills the left gap)
    l4_walls.append(offset_rect((1000, 80, 20, 160)))  # splits top region (gate G4 fills the upper gap)
    l4_walls.append(offset_rect((850, 380, 20, 270)))  # weave wall 1 (rises from floor)
    l4_walls.append(offset_rect((1000, 470, 20, 190))) # weave wall 2 (rises from floor)

    C_P1_SWITCH = (70, 130, 220)

    l4_warden_points = [offset_point((1060, 300)), offset_point((1215, 300)),
                        offset_point((1215, 595)), offset_point((1060, 595)),
                        offset_point((1130, 450))]

    levels.append({
        "name": "Level 4: Hand in Hand",
        "briefing_p1": [
            "Orange gates only open while",
            "P2 holds the matching switch.",
            "",
            "Your BLUE switches open P2's",
            "gates: they need you too.",
            "",
            "If you two deadlock, press R,",
            "regroup, and plan it better."
        ],
        "briefing_p2": [
            "A warden circles the plaza",
            "switches. The line shows where",
            "it is heading next: time your",
            "holds around it.",
            "",
            "P1's blue switches open YOUR",
            "gates. Agree on every move:",
            "a deadlock means restarting."
        ],
        "p1_start": offset_point((60, 580)), "p2_start": offset_point((680, 600)),
        "key": offset_rect((80, 300, 40, 40)), "chest": offset_rect((560, 50, 40, 40)),
        "walls": l4_walls,
        "gates": [
            {"rect": offset_rect((480, 440, 155, 20)), "id": 1},  # G1: P1 bottom -> middle
            {"rect": offset_rect((10, 220, 150, 20)),  "id": 2},  # G2: P1 middle -> top-left
            {"rect": offset_rect((360, 150, 20, 70)),  "id": 6},  # G5: P1 top-left -> top-right (chest side)
            {"rect": offset_rect((645, 240, 155, 20)), "id": 3},  # G3: P2 strip -> top-left room
            {"rect": offset_rect((1000, 10, 20, 70)),  "id": 5},  # G4: P2 top-left -> top-right room
        ],
        "guards": [
            # Static guard parked on the chest. No timing window: P2 must hold its switch.
            {"x": offset_point((480, 60))[0], "y": offset_point((480, 60))[1],
             "path": [offset_point((480, 60)), offset_point((480, 60))],
             "angle": 0, "id": 4, "speed": 0, "fov": 60, "len": 170, "color": C_GUARD_DEFAULT},
            # The warden: slow aura guard wandering the plaza switches at random
            {"x": l4_warden_points[4][0], "y": l4_warden_points[4][1],
             "path": l4_warden_points,
             "angle": 0, "id": 0, "speed": 2, "fov": 360, "len": 95, "color": C_GUARD_DEFAULT,
             "target": "p2", "random_patrol": True, "pause_frames": 70},
        ],
        "deactivators": [
            # P2 plaza switches (under the warden's watch)
            {"x": offset_point((1150, 560))[0], "y": offset_point((1150, 560))[1], "id": 1, "fake": False, "color": C_DEACTIVATOR_DEFAULT},  # S1: opens G1
            {"x": offset_point((1060, 420))[0], "y": offset_point((1060, 420))[1], "id": 2, "fake": False, "color": C_DEACTIVATOR_DEFAULT},  # S2: opens G2
            {"x": offset_point((1200, 330))[0], "y": offset_point((1200, 330))[1], "id": 6, "fake": False, "color": C_DEACTIVATOR_DEFAULT},  # S4: opens G5
            # Chest-guard switch, locked behind both blue-gated rooms (the finale)
            {"x": offset_point((1200, 60))[0],  "y": offset_point((1200, 60))[1],  "id": 4, "fake": False, "color": C_DEACTIVATOR_DEFAULT},  # S3: disables chest guard
            # P1 switches (blue): open P2's gates
            {"x": offset_point((400, 30))[0],  "y": offset_point((400, 30))[1],  "id": 3, "fake": False, "color": C_P1_SWITCH, "user": "p1"},  # T1: opens G3
            {"x": offset_point((600, 180))[0],  "y": offset_point((600, 180))[1],  "id": 5, "fake": False, "color": C_P1_SWITCH, "user": "p1"},  # T2: opens G4
        ],
        "instructions": [
            {"id": "l4_p1_blue", "lines": ["Blue switches open", "P2's gates. Hold them!"], "rect": offset_rect((60, 360, 220, 60)), "start_active": True},
            {"id": "l4_p2_warden", "lines": ["The warden's line shows", "its next stop. Time it!"], "rect": offset_rect((648, 300, 235, 60)), "start_active": True},
        ],
    })

    # Level 5: In Step (attunement, co-regulation, secure base)
    # Three stacked chambers per side. Paired SYNC GATES between chambers open only
    # while BOTH players stand on their purple sync pads at the same time, and latch
    # open permanently once passed (joint progress is permanent).
    # Standing ready on a pad CALMS the partner's guards to half speed (co-regulation).
    # Pads are also checkpoints: a caught player returns to their last pad (secure base).
    l5_walls = list(base_walls)
    # P1 chamber dividers (sync gates fill the central gaps)
    l5_walls.append(offset_rect((10, 220, 200, 20)))
    l5_walls.append(offset_rect((365, 220, 270, 20)))
    l5_walls.append(offset_rect((10, 440, 200, 20)))
    l5_walls.append(offset_rect((365, 440, 270, 20)))
    # P2 chamber dividers
    l5_walls.append(offset_rect((645, 220, 200, 20)))
    l5_walls.append(offset_rect((1000, 220, 265, 20)))
    l5_walls.append(offset_rect((645, 440, 200, 20)))
    l5_walls.append(offset_rect((1000, 440, 265, 20)))

    C_SYNC = (180, 130, 230)

    levels.append({
        "name": "Level 5: In Step",
        "briefing_p1": [
            "Move IN STEP. Doors between",
            "chambers open only while you",
            "are BOTH on your purple pads,",
            "then they stay open for good.",
            "",
            "Standing ready on a pad CALMS",
            "your partner's guards.",
            "",
            "Caught = back to your last pad."
        ],
        "briefing_p2": [
            "Each chamber has its own hazard.",
            "Clear yours, then wait on the",
            "purple pad: doors need you BOTH.",
            "",
            "Your presence on a pad slows",
            "P1's guards, and theirs yours.",
            "",
            "Pads are your checkpoints.",
            "Synced doors stay open for good."
        ],
        "p1_start": offset_point((60, 60)), "p2_start": offset_point((680, 60)),
        "key": offset_rect((560, 590, 40, 40)), "chest": offset_rect((560, 50, 40, 40)),
        "walls": l5_walls,
        "gates": [
            {"rect": offset_rect((210, 220, 155, 20)), "id": 11, "needs": 2, "latch": True},  # P1 chamber 1 -> 2
            {"rect": offset_rect((845, 220, 155, 20)), "id": 11, "needs": 2, "latch": True},  # P2 chamber 1 -> 2
            {"rect": offset_rect((210, 440, 155, 20)), "id": 12, "needs": 2, "latch": True},  # P1 chamber 2 -> 3
            {"rect": offset_rect((845, 440, 155, 20)), "id": 12, "needs": 2, "latch": True},  # P2 chamber 2 -> 3
        ],
        "guards": [
            # P1 chambers: slow, readable, dodgeable solo; calmer still with P2 on a pad
            {"x": offset_point((200, 90))[0], "y": offset_point((200, 90))[1],
             "path": [offset_point((200, 90)), offset_point((480, 90))],
             "angle": 0, "id": 0, "speed": 3, "fov": 60, "len": 105, "color": C_GUARD_DEFAULT},
            {"x": offset_point((320, 330))[0], "y": offset_point((320, 330))[1],
             "path": [offset_point((320, 330)), offset_point((320, 330))],
             "angle": 90, "id": 0, "speed": 0, "sweep_speed": 1.2, "fov": 70, "len": 120, "color": C_GUARD_DEFAULT},
            {"x": offset_point((220, 560))[0], "y": offset_point((220, 560))[1],
             "path": [offset_point((220, 560)), offset_point((460, 560))],
             "angle": 0, "id": 0, "speed": 4, "fov": 60, "len": 100, "color": C_GUARD_DEFAULT},
            # P2 chambers: mirrored hazards
            {"x": offset_point((880, 100))[0], "y": offset_point((880, 100))[1],
             "path": [offset_point((880, 100)), offset_point((1150, 100))],
             "angle": 0, "id": 0, "speed": 3, "fov": 60, "len": 105, "color": C_GUARD_DEFAULT, "target": "p2"},
            {"x": offset_point((980, 330))[0], "y": offset_point((980, 330))[1],
             "path": [offset_point((980, 330)), offset_point((980, 330))],
             "angle": 90, "id": 0, "speed": 0, "sweep_speed": -1.2, "fov": 70, "len": 120, "color": C_GUARD_DEFAULT, "target": "p2"},
            {"x": offset_point((900, 560))[0], "y": offset_point((900, 560))[1],
             "path": [offset_point((900, 560)), offset_point((1140, 560))],
             "angle": 0, "id": 0, "speed": 4, "fov": 60, "len": 100, "color": C_GUARD_DEFAULT, "target": "p2"},
        ],
        "deactivators": [
            # Sync pads. Pairs share a link id; the gates need BOTH held at once.
            # Each pad calms the PARTNER's guards and checkpoints its own player.
            {"x": offset_point((60, 150))[0],  "y": offset_point((60, 150))[1],  "id": 11, "fake": False, "color": C_SYNC, "user": "p1", "calms": "p2", "checkpoint": True},
            {"x": offset_point((700, 150))[0], "y": offset_point((700, 150))[1], "id": 11, "fake": False, "color": C_SYNC, "user": "p2", "calms": "p1", "checkpoint": True},
            {"x": offset_point((60, 370))[0],  "y": offset_point((60, 370))[1],  "id": 12, "fake": False, "color": C_SYNC, "user": "p1", "calms": "p2", "checkpoint": True},
            {"x": offset_point((700, 370))[0], "y": offset_point((700, 370))[1], "id": 12, "fake": False, "color": C_SYNC, "user": "p2", "calms": "p1", "checkpoint": True},
            # Bottom-chamber calm stations (no gate link: pure support + checkpoint,
            # useful during the key grab and the return trip)
            {"x": offset_point((60, 600))[0],  "y": offset_point((60, 600))[1],  "id": 13, "fake": False, "color": C_SYNC, "user": "p1", "calms": "p2", "checkpoint": True},
            {"x": offset_point((700, 600))[0], "y": offset_point((700, 600))[1], "id": 13, "fake": False, "color": C_SYNC, "user": "p2", "calms": "p1", "checkpoint": True},
        ],
        "instructions": [
            {"id": "l5_sync", "lines": ["Doors open only when", "BOTH pads are held"], "rect": offset_rect((230, 130, 205, 60)), "start_active": True},
            {"id": "l5_calm", "lines": ["Waiting on a pad CALMS", "your partner's guards"], "rect": offset_rect((860, 130, 230, 60)), "start_active": True},
        ],
    })

    # Level 6: Blind Trust (asymmetric information, forced verbal communication)
    # P1's guards have INVISIBLE vision cones; only P2's radar minimap shows them.
    # P2 faces six identical switches (3 real, 3 fake); only P1's intel panel shows which is which.
    # Stepping on a fake resets BOTH players and permanently marks the fake with an X.
    l6_walls = list(base_walls)
    # P1 side: walled-off pocket (bottom-left) holds the intel panel
    l6_walls.append(offset_rect((10, 430, 280, 20)))
    l6_walls.append(offset_rect((290, 430, 20, 220)))
    # P1 maze
    l6_walls.append(offset_rect((500, 10, 20, 170)))
    l6_walls.append(offset_rect((180, 180, 340, 20)))
    l6_walls.append(offset_rect((470, 320, 20, 180)))
    # P2 side: walled-off pocket (top-right) holds the radar minimap
    l6_walls.append(offset_rect((980, 10, 20, 200)))
    l6_walls.append(offset_rect((980, 210, 290, 20)))
    # P2 maze
    l6_walls.append(offset_rect((830, 300, 20, 360)))
    l6_walls.append(offset_rect((1100, 300, 20, 250)))

    levels.append({
        "name": "Level 6: Blind Trust",
        "briefing_p1": [
            "Your guards' cones are INVISIBLE.",
            "They only appear on the radar,",
            "and the radar only runs while P2",
            "stands on the RADAR pad.",
            "",
            "Stand on your INTEL pad to reveal",
            "which of P2's switches are real.",
            "A fake resets you BOTH."
        ],
        "briefing_p2": [
            "Six identical switches: 3 real,",
            "3 fake. P1's INTEL pad reveals",
            "which is which. A fake resets",
            "BOTH, and stays unmarked:",
            "REMEMBER it together.",
            "",
            "You can hold a switch OR man the",
            "RADAR pad that shows P1 the",
            "hidden cones. Never both."
        ],
        "p1_start": offset_point((60, 60)), "p2_start": offset_point((680, 620)),
        "key": offset_rect((560, 590, 40, 40)), "chest": offset_rect((560, 50, 40, 40)),
        "walls": l6_walls,
        "guards": [
            {"x": offset_point((350, 120))[0], "y": offset_point((350, 120))[1],
             "path": [offset_point((350, 120)), offset_point((560, 120))],
             "angle": 0, "id": 1, "speed": 6, "sweep_speed": 0, "fov": 90, "len": 170, "color": C_GUARD_DEFAULT, "hidden_cone": True},
            {"x": offset_point((40, 330))[0], "y": offset_point((40, 330))[1],
             "path": [offset_point((40, 330)), offset_point((40, 330))],
             "angle": 0, "id": 2, "speed": 0, "sweep_speed": 3, "fov": 80, "len": 160, "color": C_GUARD_DEFAULT, "hidden_cone": True},
            {"x": offset_point((560, 500))[0], "y": offset_point((560, 500))[1],
             "path": [offset_point((560, 500)), offset_point((560, 500))],
             "angle": 90, "id": 3, "speed": 0, "sweep_speed": 3, "fov": 90, "len": 170, "color": C_GUARD_DEFAULT, "hidden_cone": True},
        ],
        "deactivators": [
            # Real switches (all six look identical to P2)
            {"x": offset_point((700, 90))[0],   "y": offset_point((700, 90))[1],   "id": 1,   "fake": False, "color": C_DEACTIVATOR_DEFAULT},
            {"x": offset_point((940, 380))[0],  "y": offset_point((940, 380))[1],  "id": 2,   "fake": False, "color": C_DEACTIVATOR_DEFAULT},
            {"x": offset_point((1200, 580))[0], "y": offset_point((1200, 580))[1], "id": 3,   "fake": False, "color": C_DEACTIVATOR_DEFAULT},
            # Fakes: link 777 = shared reset
            {"x": offset_point((900, 90))[0],   "y": offset_point((900, 90))[1],   "id": 777, "fake": True,  "color": C_DEACTIVATOR_DEFAULT},
            {"x": offset_point((700, 500))[0],  "y": offset_point((700, 500))[1],  "id": 777, "fake": True,  "color": C_DEACTIVATOR_DEFAULT},
            {"x": offset_point((1150, 380))[0], "y": offset_point((1150, 380))[1], "id": 777, "fake": True,  "color": C_DEACTIVATOR_DEFAULT},
        ],
        "consoles": [
            # Panels only render while the owning player stands on their pad.
            {"rect": offset_rect((120, 30, 56, 56)),  "owner": "p1", "label": "INTEL"},
            {"rect": offset_rect((665, 550, 56, 56)), "owner": "p2", "label": "RADAR"},
        ],
        "instructions": [],
    })

    # Level 7: Lighthouses (full trust under invisible threat, calm planning)
    # P1's guards are COMPLETELY invisible: bodies and beams. They never move,
    # only their beams revolve, slowly and at a constant rate (learnable rhythm).
    # Anti-frustration: P1 has a proximity pulse ring (green -> red as a hidden
    # guard nears), and detection starts a visible alert with a grace window
    # to step back before it counts as a catch.
    # P2's switches FREEZE a beam in place while held, which also reveals the
    # guard as a faint ghost. P2 must predict where the beam will point by the
    # time they reach the switch: the radar pad and the switches are far apart.
    l7_walls = list(base_walls)
    # P1 side: light structure to shape the route (beams ignore walls)
    l7_walls.append(offset_rect((150, 250, 320, 20)))
    l7_walls.append(offset_rect((470, 10, 20, 260)))
    l7_walls.append(offset_rect((240, 470, 20, 180)))
    # P2 side: travel structure between the radar pad and the freeze switches
    l7_walls.append(offset_rect((830, 150, 20, 250)))
    l7_walls.append(offset_rect((1060, 400, 20, 250)))

    levels.append({
        "name": "Level 7: Lighthouses",
        "briefing_p1": [
            "The guards here are COMPLETELY",
            "invisible: bodies and beams.",
            "",
            "Your pulse ring warms from green",
            "to red as you near one. If",
            "spotted, you get a short alert",
            "(!) to step back before it",
            "counts. Move slow. Listen."
        ],
        "briefing_p2": [
            "Your RADAR pad shows the slow",
            "revolving beams on P1's side.",
            "",
            "Your switches FREEZE a beam in",
            "place while held, and reveal",
            "that guard as a faint ghost.",
            "Beams keep turning while you",
            "walk: predict, then commit."
        ],
        "p1_start": offset_point((60, 60)), "p2_start": offset_point((680, 620)),
        "key": offset_rect((560, 600, 40, 40)), "chest": offset_rect((560, 50, 40, 40)),
        "walls": l7_walls,
        "switch_mode": "freeze",
        "detect_grace": 0.9,
        "proximity_cue": True,
        "guards": [
            {"x": offset_point((300, 140))[0], "y": offset_point((300, 140))[1],
             "path": [offset_point((300, 140)), offset_point((300, 140))],
             "angle": 0, "id": 1, "speed": 0, "sweep_speed": 0.55, "rotate": True,
             "fov": 70, "len": 190, "color": C_GUARD_DEFAULT, "hidden_body": True},
            {"x": offset_point((140, 440))[0], "y": offset_point((140, 440))[1],
             "path": [offset_point((140, 440)), offset_point((140, 440))],
             "angle": 90, "id": 2, "speed": 0, "sweep_speed": -0.7, "rotate": True,
             "fov": 70, "len": 180, "color": C_GUARD_DEFAULT, "hidden_body": True},
            {"x": offset_point((480, 430))[0], "y": offset_point((480, 430))[1],
             "path": [offset_point((480, 430)), offset_point((480, 430))],
             "angle": 180, "id": 3, "speed": 0, "sweep_speed": 0.65, "rotate": True,
             "fov": 70, "len": 190, "color": C_GUARD_DEFAULT, "hidden_body": True},
        ],
        "deactivators": [
            # Freeze switches: hold to lock the matching beam where it points
            {"x": offset_point((700, 90))[0],   "y": offset_point((700, 90))[1],   "id": 1, "fake": False, "color": C_DEACTIVATOR_DEFAULT},
            {"x": offset_point((950, 380))[0],  "y": offset_point((950, 380))[1],  "id": 2, "fake": False, "color": C_DEACTIVATOR_DEFAULT},
            {"x": offset_point((1200, 580))[0], "y": offset_point((1200, 580))[1], "id": 3, "fake": False, "color": C_DEACTIVATOR_DEFAULT},
        ],
        "consoles": [
            {"rect": offset_rect((665, 550, 56, 56)), "owner": "p2", "label": "RADAR"},
        ],
        "instructions": [],
    })

    return levels

# game manager

class Game:
    def __init__(self):
        self.levels = get_levels()
        self.current_level_idx = 0
        self.state = "MAIN_MENU"
        self.menu_buttons = [
            {"text": "Tutorial", "level_idx": 0, "rect": pygame.Rect(SCREEN_WIDTH//2 - 100, 170, 200, 46)},
            {"text": "Level 1", "level_idx": 1, "rect": pygame.Rect(SCREEN_WIDTH//2 - 100, 230, 200, 46)},
            {"text": "Level 2", "level_idx": 2, "rect": pygame.Rect(SCREEN_WIDTH//2 - 100, 290, 200, 46)},
            {"text": "Level 3", "level_idx": 3, "rect": pygame.Rect(SCREEN_WIDTH//2 - 100, 350, 200, 46)},
            {"text": "Level 4", "level_idx": 4, "rect": pygame.Rect(SCREEN_WIDTH//2 - 100, 410, 200, 46)},
            {"text": "Level 5", "level_idx": 5, "rect": pygame.Rect(SCREEN_WIDTH//2 - 100, 470, 200, 46)},
            {"text": "Level 6", "level_idx": 6, "rect": pygame.Rect(SCREEN_WIDTH//2 - 100, 530, 200, 46)},
            {"text": "Level 7", "level_idx": 7, "rect": pygame.Rect(SCREEN_WIDTH//2 - 100, 590, 200, 46)}
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
        self.briefing_p1 = data["briefing_p1"]
        self.briefing_p2 = data["briefing_p2"]
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
            self.guards.append(Guard(g["x"], g["y"], g["path"], g["angle"], g["id"], g["speed"], g["fov"], g["len"], g.get("sweep_speed",0), g.get("color", C_GUARD_DEFAULT), g.get("target", "p1"), g.get("hidden_cone", False), g.get("hidden_body", False), g.get("rotate", False), g.get("random_patrol", False), g.get("pause_frames", 0)))
            
        self.deactivators = []
        for d_data in data["deactivators"]:
            d = Deactivator(d_data["x"], d_data["y"], d_data["id"], d_data.get("fake", False), d_data.get("color", C_DEACTIVATOR_DEFAULT), d_data.get("user", "p2"), d_data.get("hold_time", 0.0), d_data.get("cooldown", 0.0))
            d.calms = d_data.get("calms")            # Level 5: while held, calm guards targeting this player
            d.checkpoint = d_data.get("checkpoint", False)  # Level 5: pad doubles as a respawn point
            self.deactivators.append(d)

        self.gates = []
        for gate_data in data.get("gates", []):
            self.gates.append(Gate(gate_data["rect"], gate_data["id"], gate_data.get("needs", 1), gate_data.get("latch", False)))

        self.shared_fate = data.get("shared_fate", False)
        self.switch_mode = data.get("switch_mode", "disable")   # "freeze" on Level 7
        self.detect_grace = data.get("detect_grace", 0)         # seconds of alert before a catch counts
        self.proximity_cue = data.get("proximity_cue", False)   # Level 7: pulse ring near hidden guards
        self.alert_start = {"p1": None, "p2": None}
        self.consoles = [{"rect": pygame.Rect(c["rect"]), "owner": c["owner"], "label": c["label"]}
                         for c in data.get("consoles", [])]
        self.flash_msg = None
        self.flash_until = 0

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
        # load_level function handles resetting the level state and instruction flags
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
            # Closed gates are solid walls (state from last frame's switch check)
            collidable_walls = self.walls + [g.rect for g in self.gates if not g.is_open]
            self.p1.update(keys, collidable_walls)
            self.p2.update(keys, collidable_walls)

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
            calm_targets = set()
            for d in self.deactivators:
                if self.current_level_idx == 0: continue
                
                # Route the switch to whichever player operates it
                operator = self.p1 if d.user == "p1" else self.p2
                d.update(operator.rect)
                
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

                    # FAKE SWITCH WITH SHARED CONSEQUENCES (Level 6)
                    # No visual reveal: the pair must REMEMBER which switch this was.
                    elif d.link_id == 777:
                        self.p1.reset()
                        self.p2.reset()
                        self.flash_msg = "FAKE SWITCH! Both players reset. Remember which one that was."
                        self.flash_until = pygame.time.get_ticks() + 2500
                    
                    elif not d.is_fake: 
                        active_links[d.link_id] = active_links.get(d.link_id, 0) + 1
                        if d.calms:
                            calm_targets.add(d.calms)      # calm the guards hunting this player
                        if d.checkpoint:
                            operator.start_pos = (d.rect.x - 4, d.rect.y - 4)  # secure base

            # Gates open while enough linked switches are held.
            # latch: once a sync gate opens, it stays open (joint progress is permanent).
            # Safety: a closing gate waits until no body overlaps its own slab, so nobody
            # is entombed inside a wall. Room-level deadlocks remain possible by design.
            for gate in self.gates:
                want_open = active_links.get(gate.link_id, 0) >= gate.needs
                if gate.latch and gate.is_open:
                    want_open = True
                if not want_open and gate.is_open:
                    if gate.rect.colliderect(self.p1.rect) or gate.rect.colliderect(self.p2.rect):
                        want_open = True  # hold until the doorway itself is clear
                gate.is_open = want_open
            
            seen = {"p1": False, "p2": False}
            for g in self.guards:
                if self.switch_mode == "freeze":
                    g.frozen = active_links.get(g.link_id, 0) > 0   # Level 7: lock the beam in place
                else:
                    g.active = active_links.get(g.link_id, 0) == 0
                g.calmed = g.target in calm_targets
                g.update()
                
                target_player = self.p1 if g.target == "p1" else self.p2
                if g.check_collision(target_player.rect):
                    seen[g.target] = True

            # CATCH LOGIC (with optional grace period: spotted is a warning, not yet a catch)
            now = pygame.time.get_ticks()
            for tname in ("p1", "p2"):
                caught = False
                if self.detect_grace > 0:
                    if seen[tname]:
                        if self.alert_start[tname] is None:
                            self.alert_start[tname] = now
                        elif now - self.alert_start[tname] >= self.detect_grace * 1000:
                            caught = True
                            self.alert_start[tname] = None
                    else:
                        self.alert_start[tname] = None
                else:
                    caught = seen[tname]
                
                if caught:
                    target_player = self.p1 if tname == "p1" else self.p2
                    p1_was_reset = (target_player is self.p1) or self.shared_fate
                    
                    if self.shared_fate:
                        # Either player caught means BOTH respawn (no blame)
                        self.p1.reset()
                        self.p2.reset()
                        self.flash_msg = "CAUGHT! Shared fate: both players respawn."
                        self.flash_until = pygame.time.get_ticks() + 2000
                    else:
                        target_player.reset()
                    
                    # If P1 respawns, reset progression flags for Level 1 logic
                    if self.current_level_idx == 1:
                         self.p1_passed_obs1 = False
                         self.p1_passed_obs2 = False
                    
                    if p1_was_reset and self.p1_has_key:
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
            
            # Draw Walls (Checking for Trap State in Level 3)
            current_wall_color = C_WALL
            if self.current_level_idx == 3 and self.p1.is_frozen:
                 current_wall_color = C_WALL_DANGER
            
            for wall in self.walls: pygame.draw.rect(screen, current_wall_color, wall)
            
            for gate in self.gates: gate.draw(screen)
            
            for d in self.deactivators: d.draw(screen)

            # Console pads (drawn as floor objects so players stay visible on top)
            for c in self.consoles:
                live = self.console_live(c["owner"])
                base = (32, 130, 140) if live else (34, 70, 80)
                pygame.draw.rect(screen, base, c["rect"], border_radius=6)
                pygame.draw.rect(screen, (90, 220, 230), c["rect"], 2, border_radius=6)
                lbl = font_small.render(c["label"], True, (90, 220, 230))
                screen.blit(lbl, (c["rect"].centerx - lbl.get_width() // 2, c["rect"].y - 22))
            
            if not self.p1_has_key:
                draw_visual_key(screen, self.key_rect)
            
            draw_visual_chest(screen, self.chest_rect, self.p1_has_key)
            
            for g in self.guards: g.draw(screen)
            self.p1.draw(screen); self.p2.draw(screen)

            # LEVEL 7: proximity pulse, a soft ring around P1 that warms up near hidden guards
            if self.proximity_cue:
                near = None
                for g in self.guards:
                    if g.hidden_body and g.active and not g.frozen:
                        dist = math.hypot(g.rect.centerx - self.p1.rect.centerx, g.rect.centery - self.p1.rect.centery)
                        near = dist if near is None else min(near, dist)
                if near is not None and near < 280:
                    t = 1 - (near / 280)  # 0 far .. 1 close
                    pulse = 3 * math.sin(pygame.time.get_ticks() * 0.008)
                    radius = int(34 + pulse)
                    color = (int(120 + 135 * t), int(190 - 120 * t), 70)
                    ring = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
                    pygame.draw.circle(ring, list(color) + [int(50 + 150 * t)], (radius + 2, radius + 2), radius, 2)
                    screen.blit(ring, (self.p1.rect.centerx - radius - 2, self.p1.rect.centery - radius - 2))

            # DETECTION ALERT (grace period): spotted, but there is still a beat to step back
            now = pygame.time.get_ticks()
            for tname, player in (("p1", self.p1), ("p2", self.p2)):
                if self.alert_start[tname] is not None:
                    frac = min(1.0, (now - self.alert_start[tname]) / max(1, self.detect_grace * 1000))
                    r = int(30 + 6 * math.sin(now * 0.03))
                    pygame.draw.circle(screen, (255, int(200 - 160 * frac), 60), player.rect.center, r, 3)
                    mark = font_ui.render("!", True, (255, 210, 60))
                    screen.blit(mark, (player.rect.centerx - mark.get_width() // 2, player.rect.y - 34))
            
            # DRAW TUTORIAL BOXES
            for instruction in self.tutorial_instructions:
                instruction.draw(screen)

            # LEVELS 6-7: information panels (each runs only while its owner mans the pad)
            if self.current_level_idx in (6, 7):
                if self.console_live("p2"):
                    self.draw_l6_radar()
                else:
                    self.draw_l6_panel_offline(pygame.Rect(1012, 96, 246, 160), (1012, 76),
                                               "Guard radar: OFFLINE", C_P2,
                                               "P2: stand on the", "RADAR pad")
                if self.current_level_idx == 6:
                    if self.console_live("p1"):
                        self.draw_l6_intel()
                    else:
                        self.draw_l6_panel_offline(pygame.Rect(32, 536, 236, 156), (32, 516),
                                                   "Switch intel: OFFLINE", C_P1,
                                                   "P1: stand on the", "INTEL pad")

            # SHARED FLASH MESSAGE (fake switch / shared fate)
            if self.flash_msg and pygame.time.get_ticks() < self.flash_until:
                flash_surf = font_ui.render(self.flash_msg, True, (255, 80, 80))
                padding = 15
                box_w = flash_surf.get_width() + padding * 2
                box_h = flash_surf.get_height() + padding * 2
                box_rect = pygame.Rect(SCREEN_WIDTH//2 - box_w//2, 85, box_w, box_h)
                s = pygame.Surface((box_rect.width, box_rect.height), pygame.SRCALPHA)
                s.fill(C_TUTORIAL_BOX)
                screen.blit(s, (box_rect.x, box_rect.y))
                pygame.draw.rect(screen, C_TUTORIAL_BORDER, box_rect, 2, border_radius=8)
                screen.blit(flash_surf, (box_rect.x + padding, box_rect.y + padding))

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
                
                # LEVEL 3 TRAP WARNING
            if self.current_level_idx == 3 and self.p1.is_frozen:
                warn_text = "!! P1 FROZEN - P2 DON'T TOUCH WALLS - REACH CYAN SWITCH TO UNDO !!"
                warn_surf = font_ui.render(warn_text, True, (255, 50, 50))
                
                # Calculate box dimensions based on text size
                padding = 15
                box_w = warn_surf.get_width() + (padding * 2)
                box_h = warn_surf.get_height() + (padding * 2)
                box_rect = pygame.Rect(SCREEN_WIDTH//2 - box_w//2, 85, box_w, box_h)
                
                # Semi-Transparent Grey Box
                s = pygame.Surface((box_rect.width, box_rect.height), pygame.SRCALPHA)
                s.fill(C_TUTORIAL_BOX) 
                screen.blit(s, (box_rect.x, box_rect.y))
                pygame.draw.rect(screen, C_TUTORIAL_BORDER, box_rect, 2, border_radius=8) # border
                # Draw the Text centered in the box
                screen.blit(warn_surf, (box_rect.x + padding, box_rect.y + padding))

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

    def console_live(self, owner):
        """A console panel is live only while the owning player stands on their pad."""
        p = self.p1 if owner == "p1" else self.p2
        for c in self.consoles:
            if c["owner"] == owner and p.rect.colliderect(c["rect"]):
                return True
        return False

    def draw_l6_panel_offline(self, map_rect, label_pos, label_text, color, line1, line2):
        label = font_small.render(label_text, True, color)
        screen.blit(label, label_pos)
        panel = pygame.Surface(map_rect.size, pygame.SRCALPHA)
        panel.fill((18, 18, 28, 215))
        screen.blit(panel, map_rect.topleft)
        pygame.draw.rect(screen, (90, 90, 110), map_rect, 2, border_radius=4)
        t1 = font_small.render(line1, True, (140, 140, 160))
        t2 = font_small.render(line2, True, (140, 140, 160))
        screen.blit(t1, (map_rect.centerx - t1.get_width() // 2, map_rect.centery - 20))
        screen.blit(t2, (map_rect.centerx - t2.get_width() // 2, map_rect.centery + 2))

    def draw_l6_radar(self):
        """Guard radar: a minimap of P1's side that DOES show the hidden vision cones.
        Renders only while P2 mans the RADAR pad."""
        label = font_small.render("Guard radar: LIVE", True, C_P2)
        screen.blit(label, (1012, 76))
        
        map_rect = pygame.Rect(1012, 96, 246, 160)
        src = pygame.Rect(10, 10 + HUD_OFFSET, 625, 640)
        sx = map_rect.width / src.width
        sy = map_rect.height / src.height
        s = min(sx, sy)
        
        panel = pygame.Surface(map_rect.size, pygame.SRCALPHA)
        panel.fill((18, 18, 28, 215))
        
        def mp(x, y):
            return ((x - src.x) * sx, (y - src.y) * sy)
        
        # Walls of P1's side
        for w in self.walls:
            c = w.clip(src)
            if c.width > 0 and c.height > 0:
                wx, wy = mp(c.x, c.y)
                pygame.draw.rect(panel, (110, 120, 140), (wx, wy, max(2, c.width * sx), max(2, c.height * sy)))
        
        # Guards and their (otherwise hidden) cones
        for g in self.guards:
            if g.rect.centerx >= 640: continue
            gx, gy = mp(g.rect.centerx, g.rect.centery)
            if g.active:
                rad = math.radians(-g.current_angle)
                L = g.vision_length * s
                l_rad = rad - math.radians(g.fov / 2)
                r_rad = rad + math.radians(g.fov / 2)
                pts = [(gx, gy),
                       (gx + math.cos(l_rad) * L, gy + math.sin(l_rad) * L),
                       (gx + math.cos(r_rad) * L, gy + math.sin(r_rad) * L)]
                pygame.draw.polygon(panel, (255, 60, 60, 110), pts)
            dot_color = (90, 220, 235) if g.frozen else ((255, 70, 70) if g.active else (90, 90, 90))
            pygame.draw.circle(panel, dot_color, (int(gx), int(gy)), 4)
        
        # Key, chest, P1
        if not self.p1_has_key:
            kx, ky = mp(self.key_rect.centerx, self.key_rect.centery)
            pygame.draw.circle(panel, C_KEY, (int(kx), int(ky)), 3)
        cx, cy = mp(self.chest_rect.centerx, self.chest_rect.centery)
        pygame.draw.rect(panel, C_CHEST, (cx - 3, cy - 3, 7, 7))
        px, py = mp(self.p1.rect.centerx, self.p1.rect.centery)
        pygame.draw.circle(panel, C_P1, (int(px), int(py)), 4)
        
        screen.blit(panel, map_rect.topleft)
        pygame.draw.rect(screen, C_P2, map_rect, 2, border_radius=4)

    def draw_l6_intel(self):
        """Switch intel: a schematic of P2's side marking which switches are real or fake.
        Renders only while P1 mans the INTEL pad."""
        label = font_small.render("Switch intel: LIVE", True, C_P1)
        screen.blit(label, (32, 516))
        
        map_rect = pygame.Rect(32, 536, 236, 156)
        src = pygame.Rect(645, 10 + HUD_OFFSET, 625, 640)
        sx = map_rect.width / src.width
        sy = map_rect.height / src.height
        
        panel = pygame.Surface(map_rect.size, pygame.SRCALPHA)
        panel.fill((18, 18, 28, 215))
        
        def mp(x, y):
            return ((x - src.x) * sx, (y - src.y) * sy)
        
        # Walls of P2's side for spatial reference
        for w in self.walls:
            c = w.clip(src)
            if c.width > 0 and c.height > 0:
                wx, wy = mp(c.x, c.y)
                pygame.draw.rect(panel, (110, 120, 140), (wx, wy, max(2, c.width * sx), max(2, c.height * sy)))
        
        # Switches: green ring = real, red X = fake
        for d in self.deactivators:
            if d.rect.centerx < 640: continue
            dx, dy = mp(d.rect.centerx, d.rect.centery)
            if d.is_fake:
                pygame.draw.line(panel, (255, 70, 70), (dx - 5, dy - 5), (dx + 5, dy + 5), 2)
                pygame.draw.line(panel, (255, 70, 70), (dx - 5, dy + 5), (dx + 5, dy - 5), 2)
            else:
                pygame.draw.circle(panel, (90, 230, 90), (int(dx), int(dy)), 5, 2)
        
        # Live P2 position so P1 can give directions
        px, py = mp(self.p2.rect.centerx, self.p2.rect.centery)
        pygame.draw.circle(panel, C_P2, (int(px), int(py)), 4)
        
        screen.blit(panel, map_rect.topleft)
        pygame.draw.rect(screen, C_P1, map_rect, 2, border_radius=4)

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
        
        # Draw Center Divider
        pygame.draw.line(screen, C_WALL, (SCREEN_WIDTH // 2, y_start), (SCREEN_WIDTH // 2, y_start + 400), 2)
        
        # Player 1 Header
        p1_title = font_ui.render("Player 1 (Blue)", True, C_P1)
        screen.blit(p1_title, p1_title.get_rect(centerx=SCREEN_WIDTH // 4, top=y_start))
        
        # Player 2 Header
        p2_title = font_ui.render("Player 2 (Green)", True, C_P2)
        screen.blit(p2_title, p2_title.get_rect(centerx=3 * SCREEN_WIDTH // 4, top=y_start))
        
        y_offset_p1 = y_start + 60
        for line in self.briefing_p1:
            text_surf = font_rules.render(line, True, C_TEXT)
            # Center text within the left half
            screen.blit(text_surf, text_surf.get_rect(centerx=SCREEN_WIDTH // 4, top=y_offset_p1))
            y_offset_p1 += 35
            
        y_offset_p2 = y_start + 60
        for line in self.briefing_p2:
             text_surf = font_rules.render(line, True, C_TEXT)
             # Center text within the right half
             screen.blit(text_surf, text_surf.get_rect(centerx=3 * SCREEN_WIDTH // 4, top=y_offset_p2))
             y_offset_p2 += 35

        draw_centered_text(screen, "Press ENTER to Begin Mission", 250, font_ui, C_KEY)


# MAIN LOOP EXECUTION
async def main():
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
                        elif event.key == pygame.K_4: game.load_level(4)
                        elif event.key == pygame.K_5: game.load_level(5)
                        elif event.key == pygame.K_6: game.load_level(6)
                        elif event.key == pygame.K_7: game.load_level(7)

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
            

            await asyncio.sleep(0) 

    except Exception as e:
        print(f"An unexpected error occurred during the game loop: {e}")
    
    finally:
        if pygame.get_init():
            pygame.quit()
        sys.exit(0)

# MAIN LOOP EXECUTION
if __name__ == '__main__':
    asyncio.run(main())