import simpy
from rtree import index
import numpy as np
import geopy.distance
import random as rand

class Ltc(simpy.Container):
    def __init__(self, env, coord, beds, staff, patients):
        # Initialize the parent class (simpy.Container)
        super().__init__(env, init=beds, capacity=beds)
        
        # Initialize custom attributes
        self.env = env
        self.coord = coord
        self.staff = staff
        self.patients = patients

    def __str__(self):
        return str(self.coord)
    
class Elder:
    def __init__(self, env, coords, age, chronic, disability, mental_health):
        self.env = env
        self.coords = coords #[x,y]
        self.age = age #int
        self.chronic = chronic #int representing number of chronic illnesses person has
        self.disability = disability #bool
        self.mental_health = mental_health #int 1-10
        self.ltc = False
        self.deceased = False
        self.set_health()
        self.set_radius()

    def set_health(self):
        '''
        weighted sum of other attributes
        arbitrary balanced values for now, need professional consultation for accurate health scores
        '''
        if self.disability:
            self.health = 100 - (self.chronic * -10) + (self.age * -0.1) + (self.mental_health * 2) - 10
        else:
            self.health = 100 - (self.chronic * -10) + (self.age * -0.1) + (self.mental_health * 2) 
    
    def set_radius(self):
        '''
        radius of maximum preferred distance of travel for ltc in km
        '''
        if self.health > 50:
            self.radius = self.health * 5
        else:
            self.radius = self.health * 2.5

    def life_span(self):
        '''
        calculate lifespan of person based off decay rate of 0.5
        '''
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
        if distance > self.radius:
            OUT_RADIUS += 1
        
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
            self.idx.insert(cnt, (coords[0], coords[1], coords[0], coords[1]), obj = name)
            cnt += 1

    def distance(self, coord1, coord2):
        '''
        Distance between 2 coordinates on earth in km
        '''
        return geopy.distance.geodesic(coord1, coord2).km
    
    def find_ltc(self, person_coords):
        '''
        finds nearest ltc for person with available resources
        '''
        lat, lon = person_coords
        nearest_list = list(self.idx.nearest((lat, lon, lat, lon), len(self.centers), objects=True))
        
        for item in nearest_list:
            name = item.object
            ltc = self.centers[name]

            if ltc.patients != 0: #error handling for staff:patient
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
     '''
     extract info from ltc locations file:
     many locations are missing info so I substituted by choosing
     random numbers within a reasonable range for certain stats
     '''
     with open(file, "r", encoding = "utf-8") as f:
        data = f.read().splitlines()
        names = []
        coords = []
        beds = []
        staff = []
        for i in range(1, nbr_ltc, 1):
            line = data[i].split(",")
            names.append(line[4])
            coords.append((float(line[1]), float(line[0])))
            beds.append(rand.randint(10, 20)) #randomly chosen
            staff.append(rand.randint(20, 50))#randomly chosen
        return names, coords, beds, staff
     

def pick_coords():
    '''
    randomly determines coords for person based on given range:
    based off rough estimate of range of coordinates in first 20 
    LTC in csv file I have
    '''
    return [rand.uniform(50, 65), rand.uniform(-140, -100)]

def pick_age():
    '''
    N ~ (80, 5), range - 65-100
    '''
    mean = 80
    std_dev = 5
    size = 500

    ages = np.random.normal(loc=mean, scale=std_dev, size=size)
    return np.clip(ages, a_min=65, a_max=100)

def chronic_prob():
    '''
    Determined by study from Preventing and Managing 
    Chronic Disease in First Nations Communities: A GUIDANCE FRAMEWORK
    '''
    numbers = [1, 2, 3, 4, 5, 6] 
    probs = [0.5] * 6

    # Pick a random integer based on probabilities
    return rand.choices(numbers, weights =probs )[0]

def disability_prob():
    '''
    Determined by Native Women's Association of Canada
    '''
    random_number = rand.random()
    return random_number < 0.3

def det_mental_health():
    '''
    N ~ (80, 5), range - 65-100
    '''
    mean = 5
    std_dev = 2
    size = 500

    mh = np.random.normal(loc=mean, scale=std_dev, size=size)
    return np.clip(mh, a_min=1, a_max=10)

def init_population(env, pop_size):
    population = []
    ages = pick_age()
    mental_health = det_mental_health()

    for i in range(pop_size):
        population.append(Elder(env, pick_coords(), rand.choice(ages), chronic_prob(), disability_prob(), rand.choice(mental_health)))
    return population


def go_to_ltc(env, rtree, person):
    '''
    Logic of simulation called upon by generator
    '''
    while person.deceased == False:
        ltc, distance, available = rtree.find_ltc(person.coords)
        if distance > person.radius:
            person.outside_radius(distance)

        if available:
            # person gets a bed at ltc found
            print(f"{person} has found an available bed at {ltc}")
            person.set_ltc()
            yield ltc.get(1)

            # person occupies bed until end of calculated lifespan
            yield env.timeout(person.life_span())

            # bed becomes available
            person.set_deceased()
            print(f"{person} has died and a bed is available at {ltc}")
            yield ltc.put(1)
        else:
            # wait for available bed in nearest LTC
            req_time = env.now
            with ltc.get(1) as req:  # Generate a request event
                print(f"{person} is waiting for a bed at {ltc} at {env.now}")
                yield req  # Wait for access
                yield env.timeout(1)

            # checks if person is alive to occupy bed
            wait_time = env.now - req_time
            if wait_time * 0.5 >= person.health:
                person.set_deceased()
                print(f"{person} has died and a bed is available at {ltc}")
                yield ltc.put(1)
                person.no_ltc()
            else:
                print(f"{person} is off waiting list and found bed")
                person.set_ltc()
                yield env.timeout(person.life_span())

                # bed becomes available
                person.set_deceased()
                print(f"{person} has died and a bed is available at {ltc}")
                yield ltc.put(1)


# def decrease_health(env, people):
#     while True:
#         for person in people[:]:  # Use a slice to avoid modification issues during iteration
#             person.decay()
#             if person.health <= 0:
#                 print(f"Removing {person} from the population")
#                 people.remove(person)
#         yield env.timeout(1)

def gen_migration(env, rtree, people):
    '''
    generates people to engage in simulation
    '''
    while True:
        for person in people:
            env.process(go_to_ltc(env, rtree, person))
        yield env.timeout(1)
    
def main():

    #initialization info
    nbr_ltc = 5
    pop_size = 100             
    file = "C:/Users/kowen/OneDrive/AI Pathfinders/Datasets/LTC_locations.csv"
    names, coords, beds, staff = extract_info(file, nbr_ltc)
    patients = [0] * nbr_ltc

    env = simpy.Environment()

    center_objects = {
        names[i]: Ltc(env, coords[i], beds[i], staff[i], patients[i])
        for i in range(len(names))
    }
    population_objects = init_population(env, pop_size) #initialize list of Elder objects
    rtree = LTCFinderRTree(center_objects)

    global NO_LTC #num of people that had no near LTC or were unable to get into near ltc due to resource issues
    NO_LTC = 0
    global OUT_RADIUS #num of people who had to travel outside prefferred radius for LTC
    OUT_RADIUS = 0

    # Add the decay process to the environment
    env.process(gen_migration(env, rtree, population_objects)) #create generator object
    # env.process(decrease_health(env, population_objects))
    env.run(300)

main()
print(NO_LTC, OUT_RADIUS)