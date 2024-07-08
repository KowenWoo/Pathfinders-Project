import simpy

class Elder:
    '''
    Health score of each inidvidual calculated as a weighted sum of
    characteristics below. Health score determines radius individual is 
    able to travel for care.
    '''
    def __init__(self, coords, age, chronic, disability):
        self.coords = coords
        self.age = age
        self.chronic = chronic
        self.disability = disability
        self.ltc = [0,0]
        self.health = 0
        self.radius = 0

    def set_health(self):
        #weighted sum of other attributes
        return
    
    def set_radius(self):
        #calculated based off health
        return
    
    def set_ltc(self, ltc):
        #set LTC location 

        return
    
    def move(self):
        #loop until open LTC found
            #call to function to find nearest LTC

            #check availability

        #if found LTC outside radius, add to cost

        #set ltc location
        
        return
    
    def die(self):
        #called every tick
        #subtracts small amount from overall health until threshold
        
        #if threshold met, call clear bed function
        
        return
    

class LTC:
    '''
    
    '''
    def __init__(self, name, coords, beds, staff, resources):
        self.name = name
        self.coords = coords
        self.beds = beds
        self.staff = staff
        self.resources = resources

    def set_resources(self):
        #not sure how to calculate

        return

    def check_available(self) -> bool:
        #check if LTC has enough beds, resources, and staff

        return
    
    def admit_decline(self) -> bool:
        status = self.check_available()

        #handle reward based off status

        return
    
    def clear_bed(self):
        return

