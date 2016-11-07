from flask import Flask, render_template, redirect, \
    url_for, request, session, flash, g, make_response, send_file

from wtforms import Form, BooleanField, TextField, PasswordField, validators
import psycopg2
from flask.ext.sqlalchemy import SQLAlchemy
from passlib.hash import sha256_crypt
import gc

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/db_project'
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://aw3001:cy487@104.196.175.120/postgres'

app.config['SECRET_KEY'] = '123456'  
db = SQLAlchemy(app)

def connect():
    conn = psycopg2.connect("dbname='db_project' user='wdmzjwa' host='localhost' password='wdmzjwa' ")
    #conn = psycopg2.connect("dbname='postgres' user='aw3001' host='104.196.175.120' password='cy487' ")
    cur = conn.cursor()
    return conn, cur

@app.route("/")
def homepage():
    try:
        return render_template('homepage.html')
    except Exception as e :
        return str(e)

class RegistrationForm(Form):
    email = TextField('Email Address', [validators.Length(max=50)])
    name = TextField('name', [validators.Length(max=20)])
    password = PasswordField('New Password', [
        validators.Required(),
        validators.EqualTo('confirm', message='Passwords must match')
    ])
    confirm = PasswordField('Repeat Password')
    accept_tos = BooleanField('I accept the <a href="/about/tos" target="blank">something</a>', [validators.Required()])

@app.route('/register/', methods=['GET', 'POST'])
def register():
    try:
        form = RegistrationForm(request.form)
        if request.method == 'POST' and form.validate():
            email = form.email.data 
            name = form.name.data
            password = sha256_crypt.encrypt((str(form.password.data)))
            conn, cur = connect()
            #print "email: "+email
            #print "name: "+name
            #print "password: "+password

            cur.execute("select * from users where email = '{}'".format(email))
            x = cur.fetchone();

            print x

            if x is not None:
                #print x
                #print "*** x IS NOT NONE ***"
                flash("That email is already taken, please choose another.")
                #print "That email is already taken, please choose another."
                return render_template("register.html", form=form)

            else:
                #print "INSERT INTO users (email, name, password) VALUES ('{}', '{}', '{}')".format(email, name, password)
                cur.execute("INSERT INTO users (email, name, password) VALUES ('{}', '{}', '{}')".format(email, name, password))
                if request.form['character'] == 'buyer':
                    cur.execute("SELECT uid FROM users WHERE email = '{}'".format(email))
                    uid = cur.fetchone()[0]
                    cur.execute("INSERT INTO buyers values ({}, 2)".format(uid))
                elif request.form['character'] == 'seller':
                    cur.execute("SELECT uid FROM users WHERE email = '{}'".format(email))
                    uid = cur.fetchone()[0]
                    cur.execute("INSERT INTO sellers values ({}, 1)".format(uid))

                conn.commit()
                flash('Thanks for registering')
                cur.close()
                conn.close()
                gc.collect()
                session['logged_in'] = True
                session['email'] = email
                return redirect(url_for('homepage'))    

        gc.collect()
        return render_template('register.html', form=form)

    except Exception as e :
        return 'THIS IS EN EXCEPTION: ' + str(e)

@app.route('/index/')
def index():
    try:
        conn, cur = connect()
        cur.execute("SELECT name, class, price, iid from items")
        item_data = cur.fetchall()
        return render_template('index.html', item_data=item_data)
    except Exception as e :
        return 'THIS IS EN EXCEPTION: ' + str(e)

@app.route('/login/', methods=["GET","POST"])
def login():
    error = ''
    try:
        conn, cur = connect()
        if request.method == "POST":
            cur.execute("SELECT * FROM users WHERE email = '{}'".format(request.form['email']))            
            data = cur.fetchone()
            if data is None:
                error = "Invalid email, try again."
                gc.collect()
                return render_template("login.html", error=error)

            if sha256_crypt.verify(request.form['password'], data[3]):
                session['logged_in'] = True
                session['email'] = request.form['email']
                session['uid'] = data[0]
                cur.execute("SELECT name from users where email = '{}'".format(request.form['email']))
                user_name = cur.fetchone()[0]
                flash('Hello {}'.format(user_name))

                cur.execute("SELECT * from buyers where uid = {}".format(data[0]))
                if cur.fetchone() is not None:
                    session['character'] = 'buyer'
                    return redirect(url_for("index"))
                else:
                    session['character'] = 'seller'
                    return redirect(url_for("sell"))

            else:
                error = "Invalid password, try again."

        gc.collect()
        return render_template("login.html", error=error)

    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 

@app.route('/logout/')
def logout():
    session.pop('logged_in', None)
    session.clear()
    print 'You have been logged out.'
    gc.collect()
    return redirect(url_for('homepage'))

@app.route('/item/<int:iid>/', methods=["GET","POST"])
def item(iid):
    try:
        conn, cur = connect()
        if request.method == "POST":
            #print "*****************************"
            #print session['uid']
            #print iid 
            #print request.form['comment']
            cur.execute("INSERT into comments (uid, iid, content) values ({}, {}, '{}')".format(session['uid'], iid, request.form['comment']))   
            #print "INSERT into comments (uid, iid, content) values ({}, {}, '{}')".format(session['uid'], iid, request.form['comment'])
            conn.commit()

        cur.execute("SELECT * from items where iid = {}".format(iid))
        item_data = cur.fetchone()
        cur.execute("SELECT name from users where uid = {}".format(item_data[2]))
        seller_name = cur.fetchone()
        cur.execute("SELECT u.name, c.content FROM comments AS c, users AS u WHERE u.uid = c.uid AND c.iid = {}".format(iid))
        comments = cur.fetchall()
        return render_template('item.html', item_data=item_data, seller_name=seller_name, comments=comments)

    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 

@app.route('/sell/')
def sell():
    try:
        return render_template('sell.html')

    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 

@app.route('/mysell/', methods=["GET", "POST"])
def mysell():
    try:
        conn, cur = connect()
        if request.method == "POST":
            sellerid = session["uid"]
            description = request.form["description"]
            name = request.form["name"]
            price = request.form["price"]
            cur.execute("INSERT into items (name, sellerid, class, description, price, sellingstatus, cancelstatus) values ('{}', {}, '{}', '{}', {}, True, False)".format(name,sellerid, request.form["type"], description, price))
            conn.commit()

        cur.execute("SELECT name, class, price FROM items WHERE sellerid = {}".format(session['uid']))
        selling_items = cur.fetchall()
        return render_template('mysell.html', selling_items=selling_items)

    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 

@app.route('/userfile/')
def userfile():
    try:

        return render_template('userfile.html')

    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 








if __name__ == "__main__":
    app.run()