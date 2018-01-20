import csv
import math

def distance(loc1, loc2):
	assert type(loc1)==Location and type(loc2)==Location
	return math.sqrt((loc1.lat - loc2.lat)**2 + (loc1.long - loc2.long)**2)

class Location(object):
	def __init__(self, lat, long):
		assert type(long) == float
		assert type(lat) == float
		self.lat=lat
		self.long=long

	def __str__(self):
		return "("+str(self.lat)+', '+str(self.long)+')'

class Person(object):
	def __init__(self, id, name, destination, time):
		assert type(id) == int and id>0
		assert type(name) == str
		assert type(destination) == Location
		assert type(time) == str
		self.id=id
		self.name=name
		self.destination=destination

	def __str__(self):
		return self.name

class Car(object):
	def __init__(self, ownerId, size, users):
		assert type(ownerId)==int and ownerId>0
		assert type(size)==int and size>0
		self.ownerId=ownerId
		self.size=size
		self.users=users

	def __str__(self):
		return str(idDict[self.ownerId])+"'s vehicle, size "+str(self.size)
namefile="names.csv"
carfile="cars.csv"

def loadPeopleFromFile():
	global listed_people
	listed_people=[]
	csvfile=open(namefile)
	reader=csv.reader(csvfile, delimiter=';')
	for row in reader:
		assert len(row)==5
		user_destination=Location(lat=float(row[2]), long=float(3))
		listed_people.append(Person(id=int(row[0]), name=row[1], destination=user_destination, time=row[4]))

def loadCarsFromFile():
	global listed_cars
	listed_cars=[]
	csvfile=open(carfile)
	reader=csv.reader(csvfile, delimiter=';')
	for row in reader:
		assert len(row)==2
		listed_carOwnerId=row[0]
		listed_carsize=row[1]
		listed_cars.append(Car(ownerId=int(listed_carOwnerId), size=int(listed_carsize), users=[]))

def getID_dictionary():
	global idDict
	idDict={}
	for person in listed_people:
		idDict[person.id]=person

#LOADING
loadPeopleFromFile()
getID_dictionary()
loadCarsFromFile()

#PRINTING
print("People:\n")
for person in listed_people:
	print(person)
print("\nCars:\n")
for car in listed_cars:
	print(car)