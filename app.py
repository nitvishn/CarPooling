from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from helpers import *

app = Flask(__name__)
global loggedIn
loggedIn=False

# ensure responses aren't cached
if app.config["DEBUG"]:
	@app.after_request
	def after_request(response):
		response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
		response.headers["Expires"] = 0
		response.headers["Pragma"] = "no-cache"
		return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

db=SQL("sqlite:///database.db")

@app.route('/', methods=["GET", "POST"])
@login_required
def index():
	if request.method == "POST":
		purpose=request.form.get("submit")
		if purpose=="findride":
			return redirect(url_for('findride'))
		elif purpose=="giveride":
			return redirect(url_for('giveride'))
		elif purpose=="withdraw":
			return redirect(url_for('withdraw'))
		elif purpose=="finalise":
			return redirect(url_for("finalise"))
		elif purpose=="complete":
			return redirect(url_for("complete"))
		else:
			return render_template('index.html', user=user)
	else:
		users = db.execute("SELECT * FROM users")
		idDict=getID_dictionary(users)
		person_type=None
		ridedata=db.execute("SELECT * FROM rides WHERE id=:id", id=user['id'])
		if ridedata==[]:
			pooldata=db.execute("SELECT * FROM pools WHERE userid=:id", id=user['id'])
			person_type='rider'
			if not pooldata:
				pooldata=db.execute("SELECT * FROM pools WHERE ownerId=:id", id=user['id'])
			if not pooldata:
				return render_template("index.html", user=user, listed=False)
			else:
				person_type="giver"

			if person_type=="rider":
				info=idDict[db.execute("SELECT * FROM pools WHERE userid=:id", id=user['id'])[0]['ownerId']]
			else:
				info=db.execute("SELECT * FROM pools WHERE ownerId=:id", id=user['id'])
				people=[]
				print(info)
				for row in info:
					people.append(idDict[row['userid']])
				info=people

			return render_template("index.html", user=user, listed=True, info=info, person_type=person_type, finalised=True)

		else:
			#UNFINALISED
			ridedata=ridedata[0]
			if ridedata['carAvailable']=='Y':
				person_type="giver"
			else:
				person_type="rider"

			rides=db.execute("SELECT * FROM rides")

			computed_data=mapUsers(users, rides)
			if person_type=="rider":
				if user['id'] not in computed_data:
					return render_template('index.html', listed=True, info=None, user=user, finalised=False, person_type="rider")
				return render_template('index.html', listed=True, info=idDict[computed_data[user['id']]], person_type="rider", user=user, finalised=False)
			else:
				if user['id'] not in computed_data.values():
					return render_template('index.html', listed=True, info=None, person_type="giver", user=user, finalised=False)
				rows=[]
				for key in computed_data:
					if computed_data[key]==user['id']:
						rows.append(idDict[key])
				return render_template('index.html', listed=True, info=rows, person_type="giver", finalised=False, user=user)

@app.route("/withdraw", methods=["GET", "POST"])
@login_required
def withdraw():
	db.execute("DELETE FROM rides WHERE id=:id", id=user['id'])
	return redirect(url_for('index'))

@app.route("/complete", methods=["GET", "POST"])
@login_required
def complete():
	db.execute("DELETE FROM pools WHERE ownerId=:ownerId", ownerId=user['id'])
	return redirect(url_for('index'))

@app.route("/finalise", methods=["GET", "POST"])
@login_required
def finalise():
	db.execute("")
	users=db.execute("SELECT * FROM users")
	rides=db.execute("SELECT * FROM rides")
	computed_data=mapUsers(users, rides)
	for key in computed_data:
		if computed_data[key] == user['id']:
			db.execute("INSERT INTO pools (userid, ownerId) VALUES (:userid, :ownerId)", userid=key, ownerId=user['id'])
			db.execute("DELETE FROM rides WHERE id=:id", id=key)
	db.execute("DELETE FROM rides WHERE id=:id", id=user['id'])
	return redirect(url_for('index'))

@app.route('/login', methods=["GET", "POST"])
def login():
	session.clear()

	if request.method == "POST":
		rows = db.execute("SELECT * FROM users WHERE username=:username", username=request.form.get("username"))

		if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
			return render_template('login.html', errors="Invalid username/password")

		global user

		rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get('username'))
		session["user_id"] = rows[0]["id"]
		user = rows[0]

		return redirect(url_for('index'))

	else:
		return render_template('login.html')

@app.route('/register', methods=["GET", "POST"])
def register():
	session.clear()

	if (request.method == "POST"):

		password = pwd_context.hash(request.form.get('psw'))
		try:
			print(request.form.get("community"))
			lat, long=locationFromString(request.form.get("community"))
		except:
			return render_template("register.html", usererror="Please enter a valid location listed on Google Maps.")

		result = db.execute("INSERT INTO users (username, first, last, hash, contact, origin_lat, origin_long) VALUES (:username, :first, :last, :hash, :contact, :origin_lat, :origin_long)",
							username=request.form.get("username"), hash=password, first=request.form.get("name1"), last=request.form.get("name2"), contact=request.form.get("contact"), origin_lat=lat, origin_long=long)

		if not result:
			return render_template('register.html', usererror="Sorry, the username '" + str(
				request.form.get('username')) + "' has already been taken.")

		global user

		rows = db.execute("SELECT * FROM users WHERE username = :username", username=request.form.get('username'))
		session["user_id"] = rows[0]["id"]
		user = rows[0]

		loggedIn = True
		return redirect(url_for('index'))

	else:
		return render_template('register.html')

@app.route("/logout")
@login_required
def logout():
	session.clear()
	loggedIn=False
	return redirect(url_for('login'))

@app.route("/findride", methods=["GET", "POST"])
@login_required
def findride():
	if request.method=="GET":
		return render_template('findride.html', user=user)
	else:
		try:
			lat, long=locationFromString(request.form.get("destination"))
		except:
			return render_template("findride.html", errors="Please enter a valid location listed on Google Maps.", user=user)

		db.execute("INSERT INTO rides (id, carAvailable, carsize, destinationLat, destinationLong, timeOfArrival) VALUES (:id, :carAvailable, :carsize, :lat, :long, :TOA)", id=user['id'], carAvailable='N', carsize=0, lat=lat, long=long, TOA=request.form.get("TOA"))
		return redirect(url_for("index"))

@app.route("/giveride", methods=["GET", "POST"])
@login_required
def giveride():
	if request.method=="GET":
		return render_template('giveride.html', user=user)
	else:
		try:
			lat, long=locationFromString(request.form.get("destination"))
		except:
			return render_template("giveride.html", errors="Please enter a valid location listed on Google Maps.", user=user)

		size=request.form.get('size')
		for char in size:
			if not char.isdigit():
				return render_template("giveride.html", errors="Please enter a valid car capacity.", user=user)
		if int(size)>15:
			return render_template("giveride.html", errors="I'm pretty sure your car isn't that big.", user=user)

		db.execute("INSERT INTO rides (id, carAvailable, carsize, destinationLat, destinationLong, timeOfArrival) VALUES (:id, :carAvailable, :carsize, :lat, :long, :TOA)", id=user['id'], carAvailable='Y', carsize=int(size), lat=float(lat), long=float(long), TOA=request.form.get("TOA"))
		return redirect(url_for("index"))

if __name__ == "__main__":
	app.run()