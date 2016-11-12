from flask import Flask, render_template, redirect, \
    url_for, request, session, flash, g, make_response, send_file, send_from_directory

from wtforms import Form, BooleanField, TextField, PasswordField, validators
from wtforms.fields.html5 import EmailField
import psycopg2
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from passlib.hash import sha256_crypt
import gc



app = Flask(__name__)


########### These lines below is for submitting picture
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import os

UPLOAD_FOLDER='/Users/AnWang/Desktop/donggeyanshi/Project1/dbproject/static/picture/'
ALLOWED_EXTENSIONS=set(['txt','pdf','png','jpg','jpeg','gif'])

app.config['UPLOAD_FOLDER']=UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.',1)[1] in ALLOWED_EXTENSIONS

######################################################


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
    #email = TextField('Email Address', [validators.Length(max=50)])
    email = EmailField('Email address', [validators.DataRequired(), validators.Email()])
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
        if request.method == 'POST' and form.validate():    
            email = form.email.data 
            name = form.name.data
            password = sha256_crypt.encrypt((str(form.password.data)))
            conn, cur = connect()
            q = "select * from users where email = %s"
            cur.execute(q,(email,))
            x = cur.fetchone();

            print x

            if x is not None:
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
                #cur.close()
                #conn.close()
                #gc.collect()
                return redirect(url_for('homepage'))    

        gc.collect()
        return render_template('register.html', form=form)

    except Exception as e :
        return 'THIS IS EN EXCEPTION: ' + str(e)

######### add teardown_request ##################
@app.teardown_request
def teardown_request(exception):
	try:
		cur.close()
		conn.close()
		gc.collect()
	except Exception as e:
		pass
######### add teardown_request ##################

@app.route('/index/<string:type_chosen>/', methods=["GET","POST"])
def index2(type_chosen):
    try:
        print type_chosen
        conn, cur = connect() 
        cur.execute("SELECT name, theclass, price, iid, quantity, sellingstatus from items where theclass = '{}'".format(type_chosen))
        item_data = cur.fetchall()
        return render_template('index.html', item_data=item_data)

    except Exception as e :
        return 'THIS IS EN EXCEPTION: ' + str(e)

@app.route('/index/')
def index():
    try:
        conn, cur = connect() 
        cur.execute("SELECT name, theclass, price, iid, quantity, sellingstatus from items")
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
                #flash('Hello {}'.format(user_name))
                session['username'] = user_name
                #cur.execute("SELECT * from buyers where uid = {}".format(data[0]))
                q = "SELECT * from buyers where uid = %s"
                cur.execute(q,(data[0],))
                if cur.fetchone() is not None:
                    session['character'] = 'buyer'
                    return redirect(url_for("index"))
                else:
                    session['character'] = 'seller'
                    return redirect(url_for("mysell"))

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

        q = "SELECT * FROM users u, buyers b WHERE u.uid = b.uid AND u.uid = %s"
        cur.execute(q,(session['uid'],))
        isbuyer = not (cur.fetchone() is None)
        print isbuyer
        #cur.execute("SELECT u.name, c.content FROM comments AS c, users AS u WHERE u.uid = c.uid AND c.iid = {}".format(iid))
        q = """SELECT u.name, c.time, c.content, c.uid 
                FROM comments AS c, users AS u WHERE u.uid = c.uid AND c.iid = %s"""
        cur.execute(q,(iid,))
        comments = cur.fetchall()

        q = "SELECT image from pictures_belongs where iid = %s"
        cur.execute(q, (iid,))
        pictures = cur.fetchall()
        print "*********** pictures *******"
        print pictures
        for picture in pictures:
        	print picture[0]

        #print comments[5][1]
        return render_template('item.html', item_data=item_data, \
            seller_name=seller_name, comments=comments, likeit = likeIt, isbuyer = isbuyer, pictures=pictures)
    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 

@app.route('/purchase/', methods = ["GET","POST"])
def purchase():
    # tid | sellerid | buyerid | iid |        time         | totalprice 
    try:
        conn, cur = connect()
        if request.method == "POST":
            print "purchase/"
            buy_quantity = 1
            seller_id = request.form['seller_id']
            buyer_id = session['uid']
            item_id = request.form['item_id']
            price = request.form['price']
            cur.execute("SET timezone = 'EST' ")  # set to New York time.
            cur.execute("SELECT localtimestamp(0)")
            localtime = cur.fetchone()

            q = "SELECT sellingstatus FROM items WHERE iid = %s"
            cur.execute(q, (item_id,))
            isselling = cur.fetchone()
            if isselling[0]:
                q = "SELECT quantity FROM items WHERE iid = %s"
                cur.execute(q, (item_id,))
                real_quantity = cur.fetchone()
                if buy_quantity > real_quantity[0]:
                    left_quantity = 0
                else: left_quantity = real_quantity[0] - buy_quantity
                q = """INSERT INTO transactions (sellerid, buyerid, iid, time, totalprice) 
                    VALUES (%s, %s, %s, %s, %s)"""
                cur.execute(q,(seller_id, buyer_id, item_id, localtime, price))
                
                if left_quantity > 0:
                    q = "UPDATE items SET quantity = %s WHERE iid = %s"
                    cur.execute(q, (left_quantity, item_id))
                if left_quantity == 0:
                    q = "UPDATE items SET sellingstatus = FALSE WHERE iid = %s"
                    cur.execute(q, (item_id,))

                conn.commit()

        cur.close()
        conn.close()
        gc.collect()
        return redirect('/buy_history/')


    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 

@app.route('/cancel/', methods = ["GET","POST"])
def cancel():
    # tid | sellerid | buyerid | iid |        time         | totalprice 
    try:
        conn, cur = connect()
        if request.method == "POST":
            item_id = request.form['item_id']

            q = "UPDATE items SET cancelstatus = %s WHERE iid = %s"
            cur.execute(q, (True, item_id))
            q = "UPDATE items SET sellingstatus = %s WHERE iid = %s"
            cur.execute(q, (False, item_id))
     
            conn.commit()

        cur.close()
        conn.close()
        gc.collect()
        return redirect('/mysell/')


    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 


@app.route('/buy_history/', methods = ["GET","POST"])
def buy_history():
    try:
        conn, cur = connect()

        q = """SELECT i.iid, name, theclass, price, time FROM items AS i, transactions AS t
                  WHERE t.buyerid = %s AND t.iid = i.iid
                  ORDER BY time DESC"""
        cur.execute(q,(session['uid'],))
        item_data = cur.fetchall()

        cur.close()
        conn.close()
        gc.collect()
        return render_template('buy_history.html', item_data = item_data)

    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 



@app.route('/sell_history/', methods = ["GET","POST"])
def sell_history():
    try:
        conn, cur = connect()

        q = """SELECT i.iid, i.name, i.theclass, i.price, t.time, u.name  
                FROM users AS u, items AS i, transactions AS t
                WHERE t.sellerid = %s AND t.iid = i.iid AND u.uid = t.buyerid
                ORDER BY t.time DESC"""
        cur.execute(q,(session['uid'],))
        item_data = cur.fetchall()

        cur.close()
        conn.close()
        gc.collect()
        return render_template('sell_history.html', item_data = item_data)

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
            # print "receiver_id = ", receiver_id
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
        q = """SELECT u.uid, u.name, m.title, m.content, m.time 
                FROM users AS u, messages AS m 
                WHERE u.uid = m.uid1 AND m.uid2 = %s
                ORDER BY m.time DESC"""
        # print q
        cur.execute(q,(session['uid'],))
        received_messages = cur.fetchall()
        # print received_messages

        q = """SELECT u.uid, u.name, m.title, m.content, m.time 
                FROM users AS u, messages AS m 
                WHERE u.uid = m.uid2 AND m.uid1 = %s
                ORDER BY m.time DESC"""
        cur.execute(q,(session['uid'],))
        sent_messages = cur.fetchall()
        # print sent_messages
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
        q = """SELECT name, theclass, price, iid, sellingstatus, cancelstatus FROM items 
                WHERE sellerid = %s
                ORDER BY sellingstatus DESC, cancelstatus ASC"""
        cur.execute(q,(session['uid'],))
        selling_items = cur.fetchall()
        return render_template('mysell.html', selling_items=selling_items)

    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 



@app.route('/userfile/', methods = ["GET", "POST"])
def userfile():
    try:
        conn, cur = connect()        
        q = "SELECT * FROM users WHERE uid = %s"
        cur.execute(q,(session['uid'],))
        user_data = cur.fetchone()

        q = "SELECT * FROM creditcards WHERE uid = %s"
        cur.execute(q,(session['uid'],))
        card_data = cur.fetchall()

        cur.close()
        conn.close()
        gc.collect()
        # print "userfile", card_data, user_data
        return render_template('userfile.html', user_data = user_data, card_data = card_data)
        # return render_template('userfile.html')
    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e) 

@app.route('/add_phone/', methods = ["GET","POST"])
def add_phone():
    try:
        conn, cur = connect()
        if request.method == "POST":
            phone_number = request.form['phone']
            q = "UPDATE users SET phone = %s WHERE uid = %s"
            cur.execute(q,(phone_number, session['uid']))
            conn.commit()
            cur.close()
            conn.close()
            gc.collect()
            location = '/userfile/'
            return redirect(location)
        else: # method = "GET"
            return render_template('add_phone.html')
    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e)    





@app.route('/add_card/', methods = ["GET","POST"])
def add_card():
    try:
        conn, cur = connect()
        if request.method == "POST":
            card_number = request.form['card']
            card_holder = request.form['holder']
            q = "INSERT INTO creditcards (uid, cardnumber, ownername) VALUES (%s, %s, %s)"
            cur.execute(q,(session['uid'], card_number, card_holder))
            conn.commit()
            cur.close()
            conn.close()
            gc.collect()
            location = '/userfile/'
            return redirect(location)
        else: # method = "GET"
            return render_template('add_card.html')
    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e)    

@app.route('/delete_card/', methods = ["GET","POST"])
def delete_card():
    try:
        conn, cur = connect()
        if request.method == "POST":
            card_number = request.form['card_number']
            q = "DELETE FROM creditcards WHERE cardnumber = %s AND uid = %s"
            cur.execute(q,(card_number,session['uid']))
            conn.commit()
            cur.close()
            conn.close()
            gc.collect()
            location = '/userfile/'
            return redirect(location)

    except Exception as e:
        return 'THIS IS EN EXCEPTION: ' + str(e)    


@app.route('/upload_picture/',methods=['GET','POST'])
def upload_picture():
    if request.method=='POST':
        file=request.files['file']
        if file and allowed_file(file.filename):
        	item_id = request.form['item_id']
        	conn, cur = connect()
        	q = "SELECT count(*) from pictures_belongs where iid = %s"
        	cur.execute(q, (item_id,))
        	count = cur.fetchone()[0]
        	picture_name = str(item_id) + '_' + str(count + 1)
        	cur.execute("INSERT into pictures_belongs values (%s, %s)", (item_id, picture_name))
        	conn.commit()
           	file.save(os.path.join(app.config['UPLOAD_FOLDER'],picture_name))
           	return redirect(url_for('item', iid = item_id))
   	return redirect(url_for('homepage'))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'],filename)



if __name__ == "__main__":
    #app.run()

    import click

    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):
    # """
    # This function handles command line parameters.
    # Run the server using

    #     python server.py

    # Show the help text using

    #     python server.py --help

    # """

        HOST, PORT = host, port
        print "running on %s:%d" % (HOST, PORT)
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)


    run()
