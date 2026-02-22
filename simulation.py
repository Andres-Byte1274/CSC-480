import random
import time
import threading
import pygame
import sys

# =========================
# 2x2 INTERSECTION GRID + CAMERA
# =========================
TILE_W, TILE_H = 1400, 800
GRID_COLS, GRID_ROWS = 2, 2
NO_OF_INTERSECTIONS = GRID_COLS * GRID_ROWS  # 4

# intersection_id layout:
# 0 1
# 2 3
OFFSETS = {
    0: (0, 0),
    1: (TILE_W, 0),
    2: (0, TILE_H),
    3: (TILE_W, TILE_H),
}

# Default values of signal timers
defaultGreen = {0: 10, 1: 10, 2: 10, 3: 10}
defaultRed = 150
defaultYellow = 5

noOfSignals = 4
speeds = {'car': 2.25, 'bus': 1.8, 'truck': 1.8, 'bike': 2.5}

vehicleTypes = {0: 'car', 1: 'bus', 2: 'truck', 3: 'bike'}
directionNumbers = {0: 'right', 1: 'down', 2: 'left', 3: 'up'}

# Coordinates of vehicles' start (BASE for one intersection tile)
BASE_x = {'right': [0, 0, 0], 'down': [755, 727, 697], 'left': [1400, 1400, 1400], 'up': [602, 627, 657]}
BASE_y = {'right': [348, 370, 398], 'down': [0, 0, 0], 'left': [498, 466, 436], 'up': [800, 800, 800]}

# Coordinates of signal image and timer (BASE for one intersection tile)
BASE_signalCoods = [(530, 230), (810, 230), (810, 570), (530, 570)]
BASE_signalTimerCoods = [(530, 210), (810, 210), (810, 550), (530, 550)]

# Coordinates of stop lines (BASE for one intersection tile)
BASE_stopLines = {'right': 590, 'down': 330, 'left': 800, 'up': 535}
BASE_defaultStop = {'right': 580, 'down': 320, 'left': 810, 'up': 545}

# Gap between vehicles
stoppingGap = 15
movingGap = 15

pygame.init()
simulation = pygame.sprite.Group()

# =========================
# PER-INTERSECTION STATE
# =========================
signals = [[] for _ in range(NO_OF_INTERSECTIONS)]
currentGreen = [0] * NO_OF_INTERSECTIONS
nextGreen = [(cg + 1) % noOfSignals for cg in currentGreen]
currentYellow = [0] * NO_OF_INTERSECTIONS

# per-intersection x/y spawn stacks and vehicles buckets
x = []
y = []
vehicles = []
for iid in range(NO_OF_INTERSECTIONS):
    ox, oy = OFFSETS[iid]
    x.append({
        'right': [v + ox for v in BASE_x['right']],
        'down':  [v + ox for v in BASE_x['down']],
        'left':  [v + ox for v in BASE_x['left']],
        'up':    [v + ox for v in BASE_x['up']],
    })
    y.append({
        'right': [v + oy for v in BASE_y['right']],
        'down':  [v + oy for v in BASE_y['down']],
        'left':  [v + oy for v in BASE_y['left']],
        'up':    [v + oy for v in BASE_y['up']],
    })
    vehicles.append({
        'right': {0: [], 1: [], 2: [], 'crossed': 0},
        'down':  {0: [], 1: [], 2: [], 'crossed': 0},
        'left':  {0: [], 1: [], 2: [], 'crossed': 0},
        'up':    {0: [], 1: [], 2: [], 'crossed': 0},
    })

def stopLine(iid, direction):
    ox, oy = OFFSETS[iid]
    if direction in ('right', 'left'):
        return BASE_stopLines[direction] + ox
    return BASE_stopLines[direction] + oy

def defaultStop(iid, direction):
    ox, oy = OFFSETS[iid]
    if direction in ('right', 'left'):
        return BASE_defaultStop[direction] + ox
    return BASE_defaultStop[direction] + oy

class TrafficSignal:
    def __init__(self, red, yellow, green):
        self.red = red
        self.yellow = yellow
        self.green = green
        self.signalText = ""

class Vehicle(pygame.sprite.Sprite):
    def __init__(self, iid, lane, vehicleClass, direction_number, direction):
        pygame.sprite.Sprite.__init__(self)
        self.iid = iid
        self.lane = lane
        self.vehicleClass = vehicleClass
        self.speed = speeds[vehicleClass]
        self.direction_number = direction_number
        self.direction = direction
        self.x = x[iid][direction][lane]
        self.y = y[iid][direction][lane]
        self.crossed = 0

        vehicles[iid][direction][lane].append(self)
        self.index = len(vehicles[iid][direction][lane]) - 1

        path = "images/" + direction + "/" + vehicleClass + ".png"
        self.image = pygame.image.load(path)

        if len(vehicles[iid][direction][lane]) > 1 and vehicles[iid][direction][lane][self.index-1].crossed == 0:
            prev = vehicles[iid][direction][lane][self.index-1]
            if direction == 'right':
                self.stop = prev.stop - prev.image.get_rect().width - stoppingGap
            elif direction == 'left':
                self.stop = prev.stop + prev.image.get_rect().width + stoppingGap
            elif direction == 'down':
                self.stop = prev.stop - prev.image.get_rect().height - stoppingGap
            elif direction == 'up':
                self.stop = prev.stop + prev.image.get_rect().height + stoppingGap
        else:
            self.stop = defaultStop(iid, direction)

        # shift spawn stacks
        if direction == 'right':
            temp = self.image.get_rect().width + stoppingGap
            x[iid][direction][lane] -= temp
        elif direction == 'left':
            temp = self.image.get_rect().width + stoppingGap
            x[iid][direction][lane] += temp
        elif direction == 'down':
            temp = self.image.get_rect().height + stoppingGap
            y[iid][direction][lane] -= temp
        elif direction == 'up':
            temp = self.image.get_rect().height + stoppingGap
            y[iid][direction][lane] += temp

        simulation.add(self)

    def move(self):
        iid = self.iid
        d = self.direction
        w = self.image.get_rect().width
        h = self.image.get_rect().height

        if d == 'right':
            if self.crossed == 0 and self.x + w > stopLine(iid, d):
                self.crossed = 1
            if ((self.x + w <= self.stop or self.crossed == 1 or (currentGreen[iid] == 0 and currentYellow[iid] == 0)) and
                (self.index == 0 or self.x + w < (vehicles[iid][d][self.lane][self.index-1].x - movingGap))):
                self.x += self.speed

        elif d == 'down':
            if self.crossed == 0 and self.y + h > stopLine(iid, d):
                self.crossed = 1
            if ((self.y + h <= self.stop or self.crossed == 1 or (currentGreen[iid] == 1 and currentYellow[iid] == 0)) and
                (self.index == 0 or self.y + h < (vehicles[iid][d][self.lane][self.index-1].y - movingGap))):
                self.y += self.speed

        elif d == 'left':
            if self.crossed == 0 and self.x < stopLine(iid, d):
                self.crossed = 1
            if ((self.x >= self.stop or self.crossed == 1 or (currentGreen[iid] == 2 and currentYellow[iid] == 0)) and
                (self.index == 0 or self.x > (vehicles[iid][d][self.lane][self.index-1].x +
                                              vehicles[iid][d][self.lane][self.index-1].image.get_rect().width + movingGap))):
                self.x -= self.speed

        elif d == 'up':
            if self.crossed == 0 and self.y < stopLine(iid, d):
                self.crossed = 1
            if ((self.y >= self.stop or self.crossed == 1 or (currentGreen[iid] == 3 and currentYellow[iid] == 0)) and
                (self.index == 0 or self.y > (vehicles[iid][d][self.lane][self.index-1].y +
                                              vehicles[iid][d][self.lane][self.index-1].image.get_rect().height + movingGap))):
                self.y -= self.speed

# =========================
# SIGNAL CONTROL PER INTERSECTION
# =========================
def initialize(iid):
    ts1 = TrafficSignal(0, defaultYellow, defaultGreen[0])
    signals[iid].append(ts1)
    ts2 = TrafficSignal(ts1.red + ts1.yellow + ts1.green, defaultYellow, defaultGreen[1])
    signals[iid].append(ts2)
    ts3 = TrafficSignal(defaultRed, defaultYellow, defaultGreen[2])
    signals[iid].append(ts3)
    ts4 = TrafficSignal(defaultRed, defaultYellow, defaultGreen[3])
    signals[iid].append(ts4)
    repeat(iid)

def repeat(iid):
    while signals[iid][currentGreen[iid]].green > 0:
        updateValues(iid)
        time.sleep(1)

    currentYellow[iid] = 1

    # reset stop positions for vehicles on current green direction
    for lane in range(0, 3):
        for v in vehicles[iid][directionNumbers[currentGreen[iid]]][lane]:
            v.stop = defaultStop(iid, directionNumbers[currentGreen[iid]])

    while signals[iid][currentGreen[iid]].yellow > 0:
        updateValues(iid)
        time.sleep(1)

    currentYellow[iid] = 0

    # reset times
    signals[iid][currentGreen[iid]].green = defaultGreen[currentGreen[iid]]
    signals[iid][currentGreen[iid]].yellow = defaultYellow
    signals[iid][currentGreen[iid]].red = defaultRed

    currentGreen[iid] = nextGreen[iid]
    nextGreen[iid] = (currentGreen[iid] + 1) % noOfSignals
    signals[iid][nextGreen[iid]].red = signals[iid][currentGreen[iid]].yellow + signals[iid][currentGreen[iid]].green

    repeat(iid)

def updateValues(iid):
    for i in range(0, noOfSignals):
        if i == currentGreen[iid]:
            if currentYellow[iid] == 0:
                signals[iid][i].green -= 1
            else:
                signals[iid][i].yellow -= 1
        else:
            signals[iid][i].red -= 1

# =========================
# VEHICLE GENERATION
# =========================
def generateVehicles():
    while True:
        iid = random.randint(0, NO_OF_INTERSECTIONS - 1)

        vehicle_type = random.randint(0, 3)
        lane_number = random.randint(1, 2)

        temp = random.randint(0, 99)
        dist = [25, 50, 75, 100]
        if temp < dist[0]:
            direction_number = 0
        elif temp < dist[1]:
            direction_number = 1
        elif temp < dist[2]:
            direction_number = 2
        else:
            direction_number = 3

        Vehicle(iid, lane_number, vehicleTypes[vehicle_type], direction_number, directionNumbers[direction_number])
        time.sleep(1)

class Main:
    # start signal controllers (one per intersection)
    for iid in range(NO_OF_INTERSECTIONS):
        t = threading.Thread(name=f"init_{iid}", target=initialize, args=(iid,), daemon=True)
        t.start()

    # Colors
    black = (0, 0, 0)
    white = (255, 255, 255)

    # WINDOW size (keep as one tile) - camera scroll shows the rest
    screenWidth = TILE_W
    screenHeight = TILE_H
    screenSize = (screenWidth, screenHeight)

    background = pygame.image.load('images/intersection.png')

    screen = pygame.display.set_mode(screenSize)
    pygame.display.set_caption("SIMULATION - 4 Intersections (Camera View)")

    # Loading signal images and font
    redSignal = pygame.image.load('images/signals/red.png')
    yellowSignal = pygame.image.load('images/signals/yellow.png')
    greenSignal = pygame.image.load('images/signals/green.png')
    font = pygame.font.Font(None, 30)

    # =========================
    # WORLD SURFACE + CAMERA
    # =========================
    WORLD_W = TILE_W * GRID_COLS
    WORLD_H = TILE_H * GRID_ROWS
    world = pygame.Surface((WORLD_W, WORLD_H))

    camera_x = 0
    camera_y = 0
    CAMERA_SPEED = 25

    # Vehicle generation thread
    thread2 = threading.Thread(name="generateVehicles", target=generateVehicles, args=(), daemon=True)
    thread2.start()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()

        # =========================
        # DRAW EVERYTHING TO WORLD
        # =========================
        world.fill((0, 0, 0))

        # draw all intersection backgrounds
        for iid in range(NO_OF_INTERSECTIONS):
            ox, oy = OFFSETS[iid]
            world.blit(background, (ox, oy))

        # draw signals + timers
        for iid in range(NO_OF_INTERSECTIONS):
            ox, oy = OFFSETS[iid]
            for i in range(0, noOfSignals):
                signalPos = (BASE_signalCoods[i][0] + ox, BASE_signalCoods[i][1] + oy)
                timerPos = (BASE_signalTimerCoods[i][0] + ox, BASE_signalTimerCoods[i][1] + oy)

                if i == currentGreen[iid]:
                    if currentYellow[iid] == 1:
                        signals[iid][i].signalText = signals[iid][i].yellow
                        world.blit(yellowSignal, signalPos)
                    else:
                        signals[iid][i].signalText = signals[iid][i].green
                        world.blit(greenSignal, signalPos)
                else:
                    if signals[iid][i].red <= 10:
                        signals[iid][i].signalText = signals[iid][i].red
                    else:
                        signals[iid][i].signalText = "---"
                    world.blit(redSignal, signalPos)

                txt = font.render(str(signals[iid][i].signalText), True, white, black)
                world.blit(txt, timerPos)

        # draw vehicles
        for vehicle in simulation:
            world.blit(vehicle.image, [vehicle.x, vehicle.y])
            vehicle.move()

        # =========================
        # CAMERA CONTROLS (ARROWS or WASD)
        # =========================
        keys = pygame.key.get_pressed()

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            camera_x = max(0, camera_x - CAMERA_SPEED)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            camera_x = min(WORLD_W - screenWidth, camera_x + CAMERA_SPEED)
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            camera_y = max(0, camera_y - CAMERA_SPEED)
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            camera_y = min(WORLD_H - screenHeight, camera_y + CAMERA_SPEED)

        # =========================
        # SHOW CAMERA VIEW
        # =========================
        screen.blit(world, (-camera_x, -camera_y))
        pygame.display.update()

Main()