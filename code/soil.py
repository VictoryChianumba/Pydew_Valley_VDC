import pygame
from random import choice
from pytmx.util_pygame import load_pygame
from settings import *
from support import *

class SoilTile(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft = pos)
        self.z = LAYERS['soil']

class WaterTile(pygame.sprite.Sprite):
    def __init__(self, pos, surf, groups):
        super().__init__(groups)
        self.image = surf
        self.rect = self.image.get_rect(topleft = pos)
        self.z = LAYERS['soil water']

class Plant(pygame.sprite.Sprite):
    def __init__(self, plant_type, groups, soil, check_watered):
        super().__init__(groups)
        
        # setup
        self.plant_type = plant_type
        self.frames = import_folder(f'../graphics/fruit/{plant_type}')
        # print(self.frames)
        self.soil = soil
        self.check_watered = check_watered
       
        # plant growing
        self.age = 0
        self.max_age = len(self.frames) - 1
        # print(self.plant_type, self.max_age)
        self.grow_speed = GROW_SPEED[plant_type]
        self.harvestable = False

        # sprite setup
        self.image = self.frames[self.age]
        # print(self.image)
        # print(self.age)
        self.y_offset = -16 if plant_type == 'corn' else -8
        self.rect = self.image.get_rect(midbottom = soil.rect.midbottom + pygame.math.Vector2(0, self.y_offset))
        self.z = LAYERS['ground plant']
    
    def grow(self):
        if self.check_watered(self.rect.center):
            self.age += self.grow_speed

            if int(self.age) > 0:
                self.z = LAYERS['main']
                self.hitbox = self.rect.copy().inflate(-26, -self.rect.height * 0.4)

            if self.age >= self.max_age:
                self.age = self.max_age
                self.harvestable = True
            
            self.image = self.frames[int(self.age)]
            self.rect = self.image.get_rect(midbottom = self.soil.rect.midbottom + pygame.math.Vector2(0, self.y_offset))



class SoilLayer:
    def __init__(self, all_sprites, collision_sprites):
        
        # sprite groups
        self.all_sprites = all_sprites
        self.soil_sprites = pygame.sprite.Group()
        self.water_sprites = pygame.sprite.Group()
        self.plant_sprites = pygame.sprite.Group()
        self.collision_sprites = collision_sprites

        # graphics
        self.soil_surfs = import_folder_dict('../graphics/soil/')
        self.water_surfs = import_folder('../graphics/soil_water')
        
        self.create_soil_grid()
        self.create_hit_rects()

        # sounds
        self.hoe_sound = pygame.mixer.Sound('../audio/hoe.wav')
        self.hoe_sound.set_volume(0.1)
        self.plant_sound = pygame.mixer.Sound('../audio/plant.wav')
        self.plant_sound.set_volume(0.1)

    def create_soil_grid(self):
        ground = pygame.image.load('../graphics/world/ground.png')
        h_tiles, v_tiles = ground.get_width() // TILE_SIZE, ground.get_height() // TILE_SIZE
        
        self.grid = [ [[] for col in range(h_tiles)] for row in range(v_tiles) ]
        for x, y, _ in load_pygame('../data/map.tmx').get_layer_by_name('Farmable').tiles():
            self.grid[y][x].append('F')

    def create_hit_rects(self):
        self.hit_rects = []
        for row_index, row in enumerate(self.grid):
            for col_index, cell in enumerate(row):
                if 'F' in cell:
                    x = col_index * TILE_SIZE
                    y = row_index * TILE_SIZE
                    rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)
                    self.hit_rects.append(rect)
                
    def get_hit(self, point):
        for rect in self.hit_rects:
            if rect.collidepoint(point):
                self.hoe_sound.play()
                x = rect.x // TILE_SIZE
                y = rect.y // TILE_SIZE

                if 'F' in self.grid[y][x]:
                    self.grid[y][x].append('X')
                    self.create_soil_tiles()
                    if self.raining:
                        self.water_all()

    def water(self, target_pos):
        for soil_sprites in self.soil_sprites.sprites():
            if soil_sprites.rect.collidepoint(target_pos):

                x = soil_sprites.rect.x // TILE_SIZE
                y = soil_sprites.rect.y // TILE_SIZE
                self.grid[y][x].append('W')

                pos = soil_sprites.rect.topleft
                water_surf = choice(self.water_surfs)

                WaterTile(pos, water_surf, [self.all_sprites,self.water_sprites])

    def water_all(self):
        for row_index, row in enumerate(self.grid):
            for col_index, cell in enumerate(row):
                if 'X' in cell and 'W' not in cell:
                    cell.append('W')
                    x = col_index * TILE_SIZE
                    y = row_index * TILE_SIZE
                    water_surf = choice(self.water_surfs)
                    WaterTile((x,y), water_surf, [self.all_sprites,self.water_sprites])

    def remove_water(self):
        for water in self.water_sprites.sprites():
            water.kill()
        
        for row in self.grid:
            for cell in row:
                if 'W' in cell:
                    cell.remove('W')

    def check_watered(self, pos):
        x = pos[0] // TILE_SIZE
        y = pos[1] // TILE_SIZE
        cell =  self.grid[y][x]
        is_watered = 'W' in cell
        return is_watered

    def plant_seed(self, target_pos, seed):
        for soil_sprite in self.soil_sprites.sprites():
            if soil_sprite.rect.collidepoint(target_pos):
                self.plant_sound.play()
                x = soil_sprite.rect.x // TILE_SIZE
                y = soil_sprite.rect.y // TILE_SIZE

                if 'P' not in self.grid[y][x]:
                    self.grid[y][x].append('P')
                    Plant(seed,[self.all_sprites, self.plant_sprites, self.collision_sprites] ,soil_sprite, self.check_watered)

    def update_plants(self):
        for plant in self.plant_sprites.sprites():
            plant.grow()

    def create_soil_tiles(self):
        self.soil_sprites.empty()
        for row_index, row in enumerate(self.grid):
            for col_index, cell in enumerate(row):
                if 'X' in cell:
                    x = col_index * TILE_SIZE
                    y = row_index * TILE_SIZE

                    # tile options
                    t = 'X' in self.grid[row_index - 1][col_index]
                    b = 'X' in self.grid[row_index + 1][col_index]
                    r = 'X' in row[col_index + 1]
                    l = 'X' in row[col_index - 1]

                    tile_type = 'o'

                    # all sides
                    if all((t,b,r,l)): tile_type = 'x'
                    
                    # horizontal only
                    if l and not any((t,b,r)): tile_type = 'r'
                    if r and not any((t,b,l)): tile_type = 'l'
                    if l and r and not any((t,b)): tile_type = 'lr'

                    # vertical only
                    if t and not any((l,b,r)): tile_type = 'b'
                    if b and not any((t,r,l)): tile_type = 't'
                    if t and b and not any((l,r)): tile_type = 'tb'

                    # corners
                    if l and b and not any((t,r)): tile_type = 'tr'
                    if r and b and not any((t,l)): tile_type = 'tl'
                    if l and t and not any((b,r)): tile_type = 'br'
                    if r and t and not any((b,l)): tile_type = 'bl'

                    # t shapes
                    if all((t,b,r)) and not l: tile_type = 'tbr'
                    if all((t,b,l)) and not r: tile_type = 'tbl'
                    if all((l,r,t)) and not b: tile_type = 'lrb'
                    if all((l,r,b)) and not t: tile_type = 'lrt'


                    SoilTile(
                        pos = (x, y), 
                        surf = self.soil_surfs[tile_type], 
                        groups = [self.all_sprites, self.soil_sprites])
