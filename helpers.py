import math
from geopy.geocoders import Nominatim
import requests
from copy import deepcopy

geolocator = Nominatim(timeout=5)
#


def getID_dictionary(listed_people):
    idDict = {}
    for person in listed_people:
        idDict[person['id']] = person
    return idDict

# class Car(object):
# 	def __init__(self, ownerId, size, users):
# 		assert type(ownerId)==int and ownerId>0
# 		assert type(size)==int and size>0
# 		self.ownerId=ownerId
# 		self.size=size
# 		self.users=users
#
# 	def __str__(self):
# 		return str(idDict[self.ownerId])+"'s vehicle, size "+str(self.size)


class User(object):
    def __init__(self, id, name, contact):
        assert type(id) == int and id > 0
        assert type(name) == str
        assert type(contact) == str
        self.id = id
        self.name = name
        self.contact = contact

    def __str__(self):
        return self.name + ', reachable at ' + self.contact


def distance(loc1, loc2):
    assert type(loc1) == Location and type(loc2) == Location
    return math.sqrt((loc1.lat - loc2.lat)**2 + (loc1.long - loc2.long)**2) * 111.699


class Location(object):
    def __init__(self, lat, long):
        assert type(long) == float
        assert type(lat) == float
        self.lat = lat
        self.long = long

    def __str__(self):
        return "(" + str(self.lat) + ', ' + str(self.long) + ')'


def locationFromString(string):
    string = string.replace(" ", "+")
    response = requests.get(
        'https://maps.googleapis.com/maps/api/geocode/json?address=' + string)
    resp_json_payload = response.json()
    return tuple(resp_json_payload['results'][0]['geometry']['location'].values())


from flask import redirect, render_template, request, session, url_for
from functools import wraps


def apology(top="", bottom=""):
    """Renders message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=escape(top), bottom=escape(bottom))


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.11/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function


def computeTotalDistance(locationSeq):
    tot = 0
    for i in range(len(locationSeq)):
        if i >= len(locationSeq) - 1:
            return tot
        tot += distance(locationSeq[i], locationSeq[i + 1])


def sortViables(host, viables):

    def f(n):
        return n[0]

    origin = Location(host['origin_lat'], host['origin_long'])
    viables_with_dist = []
    for rider in viables:
        hostDestination = Location(
            host['destinationLat'], host['destinationLong'])
        riderDestination = Location(
            rider['destinationLat'], rider['destinationLong'])
        dist = computeTotalDistance(
            [origin, riderDestination, hostDestination])
        viables_with_dist.append([dist, rider])
    viables_with_dist.sort(key=f)
    return viables_with_dist


def closestHost(rider, hosts):
    best = [None, None]
    for host in hosts:
        hostDestination = Location(
            host['destinationLat'], host['destinationLong'])
        riderDestination = Location(
            rider['destinationLat'], rider['destinationLong'])
        dist = distance(hostDestination, riderDestination)
        if best[0] == None or dist < best[0]:
            best = [dist, host]
    return best[1]


def timeDifference(time1, time2):
    assert len(time1) == 5 and time1[2] == ':'
    assert len(time2) == 5 and time2[2] == ':'
    minutes = [time1[3:], time2[3:]]
    hours = [time1[:2], time2[:2]]
    hoursdelta = int(hours[0]) - int(hours[1])
    minutesdelta = int(minutes[0]) - int(minutes[1])
    return abs(hoursdelta * 60 + minutesdelta)


def getViableDict(hosts, riders, full, ignoreDistance=3):

    def ignore(host, rider):
        seq = [Location(host['origin_lat'], host['origin_long']), Location(
            rider['destinationLat'], rider['destinationLong']), Location(host['destinationLat'], host['destinationLong'])]
        if computeTotalDistance(seq) - distance(Location(host['origin_lat'], host['origin_long']), Location(host['destinationLat'], host['destinationLong'])) > ignoreDistance:
            return True
        return False

    hostViableDict = {}
    newHosts = []
    for host in hosts:
        if host['id'] in full:
            continue
        newHosts.append(host)
    hosts = deepcopy(newHosts)
    for host in hosts:
        viables = []
        for rider in riders:
            loc1 = Location(rider['origin_lat'], rider['origin_long'])
            loc2 = Location(host['origin_lat'], host['origin_long'])
            if ignore(host, rider):
                continue
            if distance(loc1, loc2) > 1:
                continue
            if timeDifference(host['timeOfArrival'], rider['timeOfArrival']) > 30:
                continue
            if closestHost(rider, hosts)['id'] != host['id']:
                continue
            viables.append(rider)
        viables = sortViables(host, viables)
        newViables = []
        for item in viables:
            newViables.append(item[1]['id'])
        viables = deepcopy(newViables)
        hostViableDict[host['id']] = deepcopy(viables)
    return hostViableDict


def mapUsers(users, rides):

    idDict = getID_dictionary(users)

    newUsers = []
    for ride in rides:
        if ride['id'] in idDict:
            newUser = {}
            person = deepcopy(idDict[ride['id']])
            for key in person:
                if key == 'hash':
                    continue
                newUser[key] = deepcopy(person[key])
            for key in ride:
                newUser[key] = deepcopy(ride[key])
            newUsers.append(newUser)
    users = deepcopy(newUsers)

    riders = []
    hosts = []
    for user in users:
        if user['carAvailable'] == "N":
            riders.append(user)
        else:
            hosts.append(user)

    riders = riders
    full = []
    assigned = {}
    sizeLeft = {}
    k = 0
    while len(riders) > 0 and len(full) != len(hosts):
        host = hosts[k % len(hosts)]
        viableDict = getViableDict(hosts, riders, full)
        breakOut = True
        for item in viableDict.values():
            if item != []:
                breakOut = False
        if breakOut:
            break
        sizeLeft[host['id']] = host['carsize']
        while sizeLeft[host['id']] > 0 and len(viableDict[host['id']]) > 0:
            riderId = viableDict[host['id']][0]
            assigned[riderId] = host['id']
            for i in range(len(riders)):
                if not i < len(riders):
                    continue
                if riders[i]['id'] == riderId:
                    del riders[i]

            sizeLeft[host['id']] -= 1
            viableDict = getViableDict(hosts, riders, full)
        if sizeLeft[host['id']] == 0:
            full.append(host['id'])
        k += 1
    return assigned
#
# rides=[
# 	{'id': 17, 'carAvailable': 'Y', 'carsize': 7, 'destinationLat': 13.0442747, 'destinationLong': 77.56573019999999, 'timeOfArrival': '09:45'},
# 	{'id': 18, 'carAvailable': 'Y', 'carsize': 4, 'destinationLat': 12.9234947, 'destinationLong': 77.6851069, 'timeOfArrival': '09:45'},
# 	{'id': 19, 'carAvailable': 'Y', 'carsize': 4, 'destinationLat': 12.9234947, 'destinationLong': 77.6851069, 'timeOfArrival': '09:45'},
# 	{'id': 20, 'carAvailable': 'Y', 'carsize': 4, 'destinationLat': 12.9234947, 'destinationLong': 77.6851069, 'timeOfArrival': '09:45'},
# 	{'id': 21, 'carAvailable': 'Y', 'carsize': 6, 'destinationLat': 12.9079411, 'destinationLong':77.74167, 'timeOfArrival': '09:45'},
# ]
#
# users=[
# 	{'id': 17, 'username': 'nitvishn', 'first': 'Vishnu', 'last': '', 'hash': '$6$rounds=656000$j/rTbTi5PNZiSgLv$TGkzJmeuAqx8SUryz7O0Lf4Jt1QhrhrPaPKuR6EI.7YUeWYCQ/xBk1qk.TLn5F6V8.5toeau5Ts40fAOWK5p4.', 'contact': '12345678', 'origin_lat': 17.4191058, 'origin_long': 78.3638947},
# 	{'id': 18, 'username': 'a', 'first': 'A', 'last': '', 'hash': '$6$rounds=656000$gEG8L9J4PjYbOqYw$51R7mCM6ncdGyxAF4jn2cojzPy453WdrTwmMKpAsWovJny6BJjxyyLB7GJXItxNZE.sn0k58dr2kfjYDfSW2G1', 'contact': '12345678', 'origin_lat': 17.4191058, 'origin_long': 78.3638947},
# 	{'id': 19, 'username': 'B', 'first': 'B', 'last': '', 'hash': '$6$rounds=656000$cZFHL/cQDsNbljxm$lJQav49OU/pIDh/QlG/v7ZCyKN4pNQxfTNS/jo5xogzqleUG4P5GwaqM8zAC0eLT3ybV2RFX4uEi.h8Qluo0p0', 'contact': '12345678', 'origin_lat': 17.4191058, 'origin_long': 78.3638947},
# 	{'id': 20, 'username': 'c', 'first': 'C', 'last': '', 'hash': '$6$rounds=656000$Pcnd2RCbbtD4.E1r$NEayYA2adyjVnXMf7BeGFZ6hRAlsn1iSlGJCqtURoP12pbE1kSHc2V5OhQs0.vvtBUp3ZrU94xSW1LLlxyCPa/', 'contact': '12345678', 'origin_lat': 17.4191058, 'origin_long': 78.3638947},
# 	{'id': 21, 'username': 'E', 'first': 'E', 'last': '', 'hash': '$6$rounds=656000$BuUs3.0EpftH0OyE$y2XpS2Xg7HsmSpSbAaAk7esGZX5txMNEYXQtG7p2SjITkvWfTqFWZdDr0KeNKdX/PC6w7fE1KiMawRUhOqEP41', 'contact': '12345678', 'origin_lat': 17.4191058, 'origin_long': 78.3638947},
# ]
#
# pools=[]
#
# idDict=getID_dictionary(users)
# result=mapUsers(users, rides, pools)
# for key in result:
# 	rider=idDict[key]
# 	owner=idDict[result[key]]
# 	print(rider['first']+' in '+owner['first']+"'s car")
