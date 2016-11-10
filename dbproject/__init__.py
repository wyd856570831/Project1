from flask import Flask, render_template, redirect, \
    url_for, request, session, flash, g, make_response, send_file

from wtforms import Form, BooleanField, TextField, PasswordField, validators
import psycopg2
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from passlib.hash import sha256_crypt
import gc

app = Flask(__name__)
#app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://localhost/db_project'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://aw3001:cy487@104.196.175.120/postgres'

app.config['SECRET_KEY'] = '123456'  
db = SQLAlchemy(app)

def connect():
    #conn = psycopg2.connect("dbname='db_project' user='wdmzjwa' host='localhost' password='wdmzjwa' ")
    conn = psycopg2.connect("dbname='postgres' user='aw3001' host='104.196.175.120' password='cy487' ")
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
    accept_tos = BooleanField('I accept the <a href="/about/tos" target="blank">agreement</a>', [validators.Required()])

@app.route('/register/', methods=['GET', 'POST'])
def register():
    try:
        form = RegistrationForm(request.form)
        if request.method == 'POST' and form.validate():    # where comes request?
            email = form.email.data 
            name = form.name.data
            password = sha256_crypt.encrypt((str(form.password.data)))
            conn, cur = connect()
            #print "email: "+email
            #print "name: "+name
            #print "password: "+password

            #cur.execute("select * from users where email = '{}'".format(email))
            q = "select * from users where email = %s"
            cur.execute(q,(email,))
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
                #cur.execute("INSERT INTO users (email, name, password) VALUES ('{}', '{}', '{}')".format(email, name, password))
                q = "INSERT INTO users (email, name, password) VALUES (%s,%s,%s);"
                cur.execute(q,(email,name,password))
                
                if request.form['character'] == 'buyer':
                    #cur.execute("SELECT uid FROM users WHERE email = '{}'".format(email))
                    q = "SELECT uid FROM users WHERE email = %s"
                    cur.execute(q,(email,))
                    uid = cur.fetchone()[0]
                    #cur.execute("INSERT INTO buyers values ({}, 2)".format(uid))  #insert level to buyers table
                    q = "INSERT INTO buyers values (%s, %s)"
                    cur.execute(q,(uid,2))
                elif request.form['character'] == 'seller':
                    #cur.execute("SELECT uid FROM users WHERE email = '{}'".format(email))
                    q = "SELECT uid FROM users WHERE email = %s"
                    cur.execute(q,(email,))
                    uid = cur.fetchone()[0]
                    #cur.execute("INSERT INTO sellers values ({}, 1)".format(uid))
                    q = "INSERT INTO sellers values (%s,%s)"
                    cur.execute(q,(uid,1))

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
        cur.execute("SELECT name, theclass, price, iid, quantity from items")
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
            #cur.execute("SELECT * FROM users WHERE email = '{}'".format(request.form['email']))  
            q = "SELECT * FROM users WHERE email = %s"
            cur.execute(q,(request.form['email'],))
            data = cur.fetchone()
            if data is None:
                error = "Invalid email, try again."
                gc.collect()
                return render_template("login.html", error=error)

            if sha256_crypt.verify(request.form['password'], data[2]):
                session['logged_in'] = True
                session['email'] = request.form['email']
                session['uid'] = data[0]
                #cur.execute("SELECT name from users where email = '{}'".format(request.form['email']))
                q = "SELECT name from users where email = %s"
                cur.execute(q,(request.form['email'],))
                user_name = cur.fetchone()[0]
                flash('Hello {}'.format(user_name))

                #cur.execute("SELECT * from buyers where uid = {}".format(data[0]))
                q = "SELECT * from buyers where uid = %s"
                cur.execute(q,(data[0],))
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
            #cur.execute("INSERT into comments (uid, iid, content) values ({}, {}, '{}')".format(session['uid'], iid, request.form['comment']))   
            cur.execute("SET timezone = 'EST' ")  # set to New York time.
            cur.execute("SELECT localtimestamp(0)")
            localtime = cur.fetchone()
            q = "INSERT into comments (uid, iid, time, content) values (%s,%s,%s,%s)"
            cur.execute(q,(session['uid'], iid, localtime, request.form['comment']))
            conn.commit()

        q = "SELECT * FROM likelist WHERE uid = %s AND iid = %s"
        cur.execute(q,(session['uid'],iid))
        likeIt = not (cur.fetchone() is None)
        #cur.execute("SELECT * from items where iid = {}".format(iid))
        q = "SELECT * from items where iid = %s"
        cur.execute(q,(iid,))
        item_data = cur.fetchone()
        #cur.execute("SELECT name from users where uid = {}".format(item_data[2]))
        q = "SELECT name from users where uid = %s"
        cur.execute(q,(item_data[2],))
        seller_name = cur.fetchone()
        #cur.execute("SELECT u.name, c.content FROM comments AS c, users AS u WHERE u.uid = c.uid AND c.iid = {}".format(iid))
        q = """SELECT u.name, c.time, c.content, c.uid 
                FROM comments AS c, users AS u WHERE u.uid = c.uid AND c.iid = %s"""
        cur.execute(q,(iid,))
        comments = cur.fetchall()
        #print comments[5][1]
        return render_template('item.html', item_data=item_data, seller_name=seller_name, comments=comments, likeit = likeIt)
    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 

@app.route('/new_message/', methods = ["GET","POST"])
def new_message():
    try:
        conn, cur = connect()
        if request.method == "POST":
            receiver_id = request.form['receiver_id']
            q = "SELECT name FROM users WHERE uid = %s"
            cur.execute(q,(session['uid'],))
            sender_name = cur.fetchone()
            q = "SELECT name FROM users WHERE uid = %s"
            cur.execute(q,(receiver_id,))
            receiver_name = cur.fetchone()
            cur.close()
            conn.close()
            gc.collect()
            return render_template('compose_message.html', sender_name = sender_name, \
                receiver_name = receiver_name, receiver_id = receiver_id)

    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 


@app.route('/compose_message/', methods = ["GET","POST"])
def compose_message():
    try:
        conn, cur = connect()
        if request.method == "POST":
            receiver_id = request.form['receiver_id']
            print "receiver_id = ", receiver_id
            sender_id = session['uid']
            cur.execute("SET timezone = 'EST' ")  # set to New York time.
            cur.execute("SELECT localtimestamp(0)")
            localtime = cur.fetchone()
            q = "INSERT into messages (uid1, uid2, time, title, content) values (%s,%s,%s,%s,%s)"
            cur.execute(q,(sender_id, receiver_id, localtime, request.form['title'], request.form['content']))
            conn.commit()
            cur.close()
            conn.close()
            gc.collect()
            return  redirect('/my_messages/')  #render_template('my_messages.html')

    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 

@app.route('/my_messages/', methods = ["GET","POST"])
def my_messages():
    try:
        conn, cur = connect()

        q = """SELECT u.name, m.title, m.content, m.time 
                FROM users AS u, messages AS m 
                WHERE u.uid = m.uid1 AND m.uid2 = %s
                ORDER BY m.time DESC"""
        cur.execute(q,(session['uid'],))
        received_messages = cur.fetchall()

        q = """SELECT u.name, m.title, m.content, m.time 
                FROM users AS u, messages AS m 
                WHERE u.uid = m.uid2 AND m.uid1 = %s
                ORDER BY m.time DESC"""
        cur.execute(q,(session['uid'],))
        sent_messages = cur.fetchall()

        conn.commit()
        cur.close()
        conn.close()
        gc.collect()
        return render_template('my_messages.html', received_messages = received_messages, \
            sent_messages = sent_messages)

    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e)    

@app.route('/add_likelist/', methods = ["GET","POST"])
def add_likelist():
    try:
        conn, cur = connect()
        if request.method == "POST":
            iid = request.form['item_id']
            q = "INSERT INTO likelist (uid, iid) VALUES (%s, %s)"
            cur.execute(q,(session['uid'], iid))
            conn.commit()
            cur.close()
            conn.close()
            gc.collect()
            location = '/item/' + iid
            return redirect(location)

    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 

@app.route('/buyers_likelist/', methods = ["GET","POST"])
def buyers_likelist():
    try:
        conn, cur = connect()
        q = """SELECT name, theclass, price, iid, quantity 
                FROM items WHERE iid IN (
                    SELECT iid FROM likelist WHERE uid = %s
                    )"""
        cur.execute(q, (session['uid'],))
        item_data = cur.fetchall()
        return render_template('buyers_likelist.html', item_data=item_data)

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
            quantity = request.form["quantity"]
            #cur.execute("INSERT into items (name, sellerid, theclass, description, price, sellingstatus, cancelstatus) values ('{}', {}, '{}', '{}', {}, True, False)".format(name,sellerid, request.form["type"], description, price))
            q = "INSERT into items (name, sellerid, theclass, description, price, quantity, sellingstatus, cancelstatus) values (%s,%s,%s,%s,%s,%s,%s,%s)"
            cur.execute(q,(name,sellerid, request.form["type"], description, price, quantity, True, False))
            conn.commit()

        #cur.execute("SELECT name, theclass, price FROM items WHERE sellerid = {}".format(session['uid']))
        q = "SELECT name, theclass, price FROM items WHERE sellerid = %s"
        cur.execute(q,(session['uid'],))
        selling_items = cur.fetchall()
        return render_template('mysell.html', selling_items=selling_items)

    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 

@app.route('/userfile/')
def userfile():
    try:
        conn, cur = connect()
        q = "SELECT * FROM users WHERE uid = %s"
        print q
        cur.execute(q,(session['uid'],))
        user_data = cur.fetchone()
        print "user_data"
        q = "SELECT * FROM creditcards WHERE uid = %s"
        cur.execute(q,(session['uid'],))
        card_data = cur.fetchone()
        
        print "test card_data"
        return render_template('userfile.html', user_data = user_data, card_data = card_data)

    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 








if __name__ == "__main__":
    app.run()
