from collections import OrderedDict

from pyqtgraph import mkColor

dark_grey = (53, 53, 53)
grey = (70, 70, 70)
almost_white = (240, 240, 240)
green_sea = (22, 160, 133)
nephritis = (39, 174, 96)
belize_hole = (41, 128, 185)
amethyst = (155, 89, 182)
wet_asphalt = (52, 73, 94)
orange = (243, 156, 18)
sun_flower = (241, 196, 15)
pumpkin = (211, 84, 0)
pomegranate = (192, 57, 43)
clouds = (236, 240, 241)
concrete = (149, 165, 166)
blackish = (24, 24, 24)

# Uni Konstanz Corporate Design
seeblau = (89, 199, 235)
peach = (254, 160, 144)
seegrau = (154, 160, 167)
petrol = (7, 113, 135)
seegruen = (10, 144, 134)
karpfenblau = (62, 84, 150)
pinky = (224, 96, 126)
bordeaux = (142, 32, 67)

colors = OrderedDict(
    [
        ('r', pomegranate),
        ('g', nephritis),
        ('b', belize_hole),
        ('c', green_sea),
        ('m', amethyst),
        ('y', sun_flower),
        ('k', wet_asphalt),
        ('w', clouds),
        ('o', orange),
        ('gr', concrete),
        ('red', pomegranate),
        ('green', nephritis),
        ('blue', belize_hole),
        ('cyan', green_sea),
        ('magenta', amethyst),
        ('yellow', sun_flower),
        ('black', blackish),
        ('white', clouds),
        ('orange', orange),
        ('gray', concrete),
        ('seeblau', seeblau),
        ('peach', peach),
        ('seegrau', seegrau),
        ('petrol', petrol),
        ('seegruen', seegruen),
        ('karpfenblau', karpfenblau),
        ('pinky', pinky),
        ('bordeaux', bordeaux),
    ]
)

# cyclic_colors = [
#     colors['r'],
#     colors['g'],
#     colors['b'],
#     colors['m'],
#     colors['c'],
#     colors['o'],
#     colors['gr'],
# ]

cyclic_colors = [
    colors['seeblau'],
    colors['bordeaux'],
    colors['karpfenblau'],
    colors['peach'],
    colors['petrol'],
    colors['pinky'],
    colors['seegruen'],
    colors['seegrau'],
]

def color_cycler():
    i = 0
    while True:
        i = i % len(cyclic_colors)
        color = mkColor(cyclic_colors[i])
        yield color
        i += 1