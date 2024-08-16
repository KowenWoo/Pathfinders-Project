import simpy
import simpy
from rtree import index
import geopy.distance
from math import radians, cos, sin, atan2, degrees
from geopy import Point
import numpy as np
import random as rand
import matplotlib.pyplot as plt
import matplotlib.animation as animation

class Ltc(simpy.Container):
    def __init__(self, env, coord, beds, staff, patients):
        super().__init__(env, init=beds, capacity=beds)
        self.env = env
        self.coord = coord
        self.staff = staff
        self.patients = patients

    def __str__(self):
        return str(self.coord)

class Elder:
    def __init__(self, env, coords, age, chronic, disability, mental_health):
        self.env = env
        self.coords = coords
        self.past = [coords]
        self.age = age
        self.chronic = chronic
        self.disability = disability
        self.mental_health = mental_health
        self.ltc = False
        self.deceased = False
        self.exceeded_radius = False  # Flag to track if the elder has exceeded their radius
        self.set_health()
        self.set_radius()

    def set_health(self):
        if self.disability:
            self.health = 100 - (self.chronic * -10) + (self.age * -0.1) + (self.mental_health * 2) - 10
        else:
            self.health = 100 - (self.chronic * -10) + (self.age * -0.1) + (self.mental_health * 2) 
    
    def set_radius(self):
        if self.health > 50:
            self.radius = self.health * 5
        else:
            self.radius = self.health * 2.5

    def life_span(self):
        steps = self.health / 2
        return int(steps) + (1 if self.health % 2 != 0 else 0)
    
    def decay(self):
        self.health -= 2
        if self.health <= 0:
            self.set_deceased()

    def set_deceased(self):
        self.deceased = True

    def set_ltc(self):
        self.ltc = True

    def outside_radius(self, distance):
        global OUT_RADIUS
        if distance > self.radius and not self.exceeded_radius:
            OUT_RADIUS += 1
            self.exceeded_radius = True  # Set the flag to prevent further increments
        
    def no_ltc(self):
        global NO_LTC
        NO_LTC += 1 


class LTCFinderRTree:
    def __init__(self, centers):
        self.centers = centers
        self.idx = index.Index()
        cnt = 0
        for name, ltc in centers.items():
            coords = ltc.coord
            self.idx.insert(cnt, (coords[0], coords[1], coords[0], coords[1]), obj=name)
            cnt += 1

    def distance(self, coord1, coord2):
        return geopy.distance.geodesic(coord1, coord2).km
    
    def initial_bearing(self, coord1, coord2):
        lat1, lon1 = radians(coord1[0]), radians(coord1[1])
        lat2, lon2 = radians(coord2[0]), radians(coord2[1])

        d_lon = lon2 - lon1
        x = sin(d_lon) * cos(lat2)
        y = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(d_lon)
        bearing = atan2(x, y)
        return (degrees(bearing) + 360) % 360

    def quarter_distance_coords(self, coord1, coord2):
        distance = self.distance(coord1, coord2)
        quarter_distance = distance / 4

        bearing = self.initial_bearing(coord1, coord2)

        quarter_coords = []
        for i in range(1, 4):
            intermediate_point = geopy.distance.distance(kilometers=quarter_distance * i).destination(Point(coord1[0], coord1[1]), bearing)
            quarter_coords.append((intermediate_point.latitude, intermediate_point.longitude))

        return quarter_coords
    
    def find_ltc(self, person_coords):
        lat, lon = person_coords
        nearest_list = list(self.idx.nearest((lat, lon, lat, lon), len(self.centers), objects=True))
        
        for item in nearest_list:
            name = item.object
            ltc = self.centers[name]
            if ltc.patients != 0:
                s_p_ratio = ltc.staff / (ltc.capacity - ltc.level)
            else:
                s_p_ratio = ltc.staff
            
            distance = self.distance((lat, lon), ltc.coord)
            if ltc.level > 0 and s_p_ratio > 3/14:
                return ltc, distance, True
        
        ltc = self.centers[nearest_list[0].object]
        distance = self.distance((lat, lon), ltc.coord)
        return ltc, distance, False

def extract_info(file, nbr_ltc):
    with open(file, "r", encoding="utf-8") as f:
        data = f.read().splitlines()
        names, coords, beds, staff = [], [], [], []
        for i in range(1, nbr_ltc+1, 1):
            line = data[i].split(",")
            names.append(line[4])
            coords.append((float(line[1]), float(line[0])))
            beds.append(rand.randint(10, 20))
            staff.append(rand.randint(20, 50))
        return names, coords, beds, staff
     
def pick_coords():
    return (rand.uniform(50, 65), rand.uniform(-140, -100))

def pick_age():
    mean, std_dev, size = 80, 5, 500
    ages = np.random.normal(loc=mean, scale=std_dev, size=size)
    return np.clip(ages, a_min=65, a_max=100)

def chronic_prob():
    numbers, probs = [1, 2, 3, 4, 5, 6], [0.5] * 6
    return rand.choices(numbers, weights=probs)[0]

def disability_prob():
    return rand.random() < 0.3

def det_mental_health():
    mean, std_dev, size = 5, 2, 500
    mh = np.random.normal(loc=mean, scale=std_dev, size=size)
    return np.clip(mh, a_min=1, a_max=10)

def init_population(env, pop_size):
    population = []
    ages = pick_age()
    mental_health = det_mental_health()
    for i in range(pop_size):
        population.append(Elder(env, pick_coords(), rand.choice(ages), chronic_prob(), disability_prob(), rand.choice(mental_health)))
    return population

# def go_to_ltc(env, rtree, person):
#     while not person.deceased and not person.ltc:
#         ltc, distance, available = rtree.find_ltc(person.coords)
#         if distance > person.radius:
#             person.outside_radius(distance)
#         if available: #person gets ltc bed immediately
#             quarter_coords = rtree.quarter_distance_coords(person.coords, ltc.coord)
#             for i in quarter_coords:
#                 person.past.append(i) #append quarter points for migration visualization
#             print(f"{person} has found an available bed at {ltc}")
#             person.set_ltc()
#             yield ltc.get(1)
#             yield env.timeout(person.life_span())
#             person.set_deceased()
#             print(f"{person} has died and a bed is available at {ltc}")
#             yield ltc.put(1)
#             person.past.append(ltc.coord)
#         else: #waitlist logic
#             req_time = env.now
#             with ltc.get(1) as req:
#                 print(f"{person} is waiting for a bed at {ltc} at {env.now}")
#                 yield req
#                 yield env.timeout(1)
#             wait_time = env.now - req_time
#             if wait_time * 0.5 >= person.health: #person dies on waitlist, doesn't get ltc
#                 person.set_deceased()
#                 print(f"{person} has died and a bed is available at {ltc}")
#                 yield ltc.put(1)
#                 person.no_ltc()
#             else: #person gets ltc bed after waiting
#                 quarter_coords = rtree.quarter_distance_coords(person.coords, ltc.coord)
#                 for i in quarter_coords:
#                     person.past.append(i) #append quarter points for migration visualization 
#                 print(f"{person} is off waiting list and found bed")
#                 person.set_ltc()
#                 yield env.timeout(person.life_span())
#                 person.set_deceased()
#                 print(f"{person} has died and a bed is available at {ltc}")
#                 yield ltc.put(1)
#                 person.past.append(ltc.coord)

def go_to_ltc(env, rtree, person):
    while not person.deceased and not person.ltc:
        ltc, distance, available = rtree.find_ltc(person.coords)
        
        if distance > person.radius:
            person.outside_radius(distance)

        if available:  # person gets LTC bed immediately           
            with ltc.get(1) as req:
                yield req
                quarter_coords = rtree.quarter_distance_coords(person.coords, ltc.coord)
                for i in quarter_coords:
                    person.past.append(i)  # append quarter points for migration visualization
                print(f"{person} has found an available bed at {ltc}")
                yield env.timeout(person.life_span())
                person.set_ltc()
                person.set_deceased()
                print(f"{person} has died and a bed is available at {ltc}")
                yield ltc.put(1)
                person.past.append(ltc.coord)
                
        else:  # waitlist logic
            req_time = env.now
            wait_duration = 0
            bed_found = False
            
            with ltc.get(1) as req:
                print(f"{person} is waiting for a bed at {ltc} at {env.now}")
                
                while not req.processed and not person.deceased:
                    wait_duration += 1
                    if wait_duration * 2 >= person.health:  # person dies on waitlist, doesn't get LTC
                        person.set_deceased()
                        print(f"{person} has died waiting for a bed at {ltc}")
                        break
                    
                    result = yield req | env.timeout(1)
                    if req.processed:
                        bed_found = True
                        break
                
                if bed_found:
                    quarter_coords = rtree.quarter_distance_coords(person.coords, ltc.coord)
                    for i in quarter_coords:
                        person.past.append(i)  # append quarter points for migration visualization
                    print(f"{person} is off waiting list and found bed")
                    person.set_ltc()
                    yield env.timeout(person.life_span())
                    person.set_deceased()
                    print(f"{person} has died and a bed is available at {ltc}")
                    yield ltc.put(1)
                    person.past.append(ltc.coord)
                    
                elif not person.deceased:
                    person.no_ltc()


def gen_migration(env, rtree, people):
    while True:
        for person in people:
            env.process(go_to_ltc(env, rtree, person))
        yield env.timeout(1)

def decay_every_step(env, population):
    while True:
        for person in population:
            if not person.deceased:
                person.decay()
        yield env.timeout(1)  # Wait for one time unit


def main():
    nbr_ltc, pop_size, file = 10, 1000, "C:/Users/kowen/OneDrive/AI Pathfinders/Datasets/LTC_locations.csv"
    names, coords, beds, staff = extract_info(file, nbr_ltc)
    patients = [0] * nbr_ltc

    env = simpy.Environment()
    center_objects = {names[i]: Ltc(env, coords[i], beds[i], staff[i], patients[i]) for i in range(len(names))}
    global center_coords
    center_coords = [ltc.coord for ltc in center_objects.values()]
    # for i in center_objects.values():
    #     print(i.capacity)

    global population_objects
    population_objects = init_population(env, pop_size)
    rtree = LTCFinderRTree(center_objects)

    global NO_LTC
    NO_LTC = 0
    global OUT_RADIUS
    OUT_RADIUS = 0
    
    env.process(decay_every_step(env, population_objects))
    env.process(gen_migration(env, rtree, population_objects))
    env.run(until=100)
    
main()
print(NO_LTC, OUT_RADIUS)

#visualize simulation
fig, ax = plt.subplots()
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')
ax.set_title('Seniors and LTC Centers on the Map')
ax.grid(True)
ax.set_xlim(50, 65)
ax.set_ylim(-140, -100)

# Track initial coordinates for people who couldn't find an LTC
initial_coords = {person: person.coords for person in population_objects if not person.ltc}

def update(frame):
    people_w_ltc_positions = []
    people_positions = []
    
    people_indexes = []
    cnt = 0
    for person in population_objects:
        if person.past != []:
            if person.past == [person.coords] or cnt in people_indexes:
                people_positions.append(person.past[0])
                people_indexes.append(cnt)
            else:
                people_w_ltc_positions.append(person.past.pop(0))
            # people_positions.append(person.past.pop(0))
        cnt += 1

    ax.clear()
    ax.set_xlim(50, 65)
    ax.set_ylim(-140, -100)
    
    # Plot LTC centers
    for building in center_coords:
        ax.plot(building[0], building[1], 'bs', markersize=10, label='Building')
    
    # Plot people
    for person in people_positions:
        ax.plot(person[0], person[1], 'ro', markersize=5, label='Person')
    for person in people_w_ltc_positions:
        ax.plot(person[0], person[1], 'go', markersize=5, label='Person')
    
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('People and Buildings on the Map')
    ax.grid(True)
    
    return ax

def init():
    buildings = [ax.plot(building[0], building[1], 'bs', markersize=10)[0] for building in center_coords]
    # Include people who couldn't find LTC in the initialization
    people = [ax.plot(person.coords[0], person.coords[1], 'go', markersize=5)[0] for person in population_objects]
    return buildings + people

ani = animation.FuncAnimation(fig, update, frames=100, init_func=init, interval=2000, blit=False)
plt.show()

