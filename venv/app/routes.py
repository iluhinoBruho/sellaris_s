# -*- coding: utf-8 -*-
from app import app
from app import db
import os
from datetime import datetime
from flask import Flask, url_for, render_template, flash, redirect, request
from app.forms import LoginForm, RegistrationForm, UploadForm
from flask_login import login_required, logout_user, current_user, login_user, login_required
from app.models import User, Offer, Image
from app.errors import not_found_error, internal_error
from werkzeug.urls import url_parse
from werkzeug.utils import secure_filename
from flask import send_from_directory
import requests
from sqlalchemy import asc, desc
import imghdr


ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
#BOT_ID="504321663"
BOT_ID="-1001704610673"

@app.route('/')
@app.route('/index')
@login_required
def index():
    return render_template("index.html", title='Home Page')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/user/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    my_offers_list = []
    for offer in Offer.query.filter_by(author_id=current_user.id):
        my_offers_list.append(offer)  #(Offer.query.get(Offer.id))
    return render_template('user.html', user=user, my_offers=my_offers_list)


def validate_image(stream):
    header = stream.read(512)
    stream.seek(0)
    format = imghdr.what(None, header)
    if not format:
        return None
    return '.' + (format if format != 'jpeg' else 'jpg')


def allowed_file(file):
    filename = secure_filename(file.filename)
    file_ext = os.path.splitext(filename)[1]
    if file_ext not in app.config['UPLOAD_EXTENSIONS'] or file_ext != validate_image(file.stream):
        return False 
    return True


@app.route('/create_offer', methods=['POST', 'GET'])
@login_required
def create_offer():
    if request.method == 'POST':
        item_name = request.form['item_name']
        price = request.form['price']
        descr = request.form['descr']        
        author_id = current_user.id   
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        #flash(allowed_file(file))
        if file and allowed_file(file):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            #---------------------------------------------------------------------------------------------------------------------------------------------------------------
            try:
                offer = Offer(item_name=item_name, price=price, descr=descr, author_id=author_id) #photo_id=photo.id
                db.session.add(offer)
                db.session.commit()
                img = Image(file_name=filename, offer_id=offer.id)
                db.session.add(img)
                db.session.commit()
                flash(f"Uploaded file {file.filename}")
                flash(f"Your offer posted")
                text_link = url_for('offers', _external=True)
                bot_message_lazy(text_link)
            except:
                return internal_error("An error occured while uploading your photo")            
            #---------------------------------------------------------------------------------------------------------------------------------------------------------------
            return redirect(url_for("offers"))
        return iternal_error("Please upload only jpg, jpeg, png or gif")
    else:
        #photo = UploadForm()
        return render_template("create_offer.html")     


@app.route('/offers/<int:id>')
@login_required
def offer_detail(id):
    try:
        user = current_user.id
        offer = Offer.query.get(id)
        author_id = offer.author_id
        author = User.query.get(author_id)
        images = Image.query.filter_by(offer_id=offer.id)
        main_image = ''
        for img in images:
            main_image = img
            flash(img.file_name)
        timestamp = str(offer.timestamp)[:16]
        return render_template("offer_detail.html", offer=offer, main_image=main_image, user=user, author=author, timestamp=timestamp, images=images)
    except:
        return internal_error("Problem with reaching this offer")
    
    

@app.route('/offers/<int:id>/delete')
@login_required
def offer_delete(id):
    offer = Offer.query.get_or_404(id)
    try:
        images = Image.query.filter_by(offer_id=id)
        for el in images:         
            db.session.delete(el)
            try:
                filename = el.file_name           
                path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                os.remove(path)  
            except:
                continue
        db.session.delete(offer)
        db.session.commit()
        return redirect('/offers')
    except:
        return internal_error("Problem with deleting offer")
    
    
    
@app.route('/offers/<int:id>/update', methods=['POST', 'GET'])
@login_required
def offer_update(id):
    offer = Offer.query.get(id)
    if request.method == "POST":
        offer.item_name = request.form['item_name']
        offer.price = request.form['price']
        offer.descr = request.form['descr']
        #offer.timestamp = datetime.utcnow
        #flash(datetime.utcnow)
        try:
            db.session.commit()
            return redirect('/offers')
        except:
            return internal_error("An error occured while changing")
    else:
        return render_template("offer_update.html", offer=offer, id=id)


@app.route('/offers/<int:id>/upload_images', methods=['POST', 'GET'])
@login_required
def upload_images(id):
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        #flash(allowed_file(file))
        if file and allowed_file(file):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            #---------------------------------------------------------------------------------------------------------------------------------------------------------------
            try:
                flash(id)
                img = Image(file_name=filename, offer_id=id)
                db.session.add(img)
                db.session.commit()
                flash(f"Uploaded file {file.filename}")
            except:
                return internal_error("An error occured while uploading your photo")            
            #---------------------------------------------------------------------------------------------------------------------------------------------------------------
            return redirect(url_for("offers"))
        return iternal_error("Please upload only jpg, jpeg, png or gif")        
           
    return render_template("upload_images.html", id=id)
        
    
      
@app.route('/offers')
def offers():
    offers = Offer.query.order_by(desc(Offer.id))
    images = Image.query.order_by(Image.id)
    offers_img = {}
    for img in images:
        offer_id = img.offer_id
        offers_img[offer_id] = img.file_name
    
    offers_pack = []
    idx = 0
    for offer in offers:
        if idx % 3 == 0:
            offers_pack.append([])
        offers_pack[-1].append(offer)
        idx += 1
        
    return render_template("offers.html", offers=offers, offers_img=offers_img, offers_pack=offers_pack)

@app.route('/uploads/<filename>')
def single_img(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)



def bot_message_lazy(textlink, chat_id=BOT_ID):
    '''
    TODO 
    move every constant to cnfg
    '''
    flash("working  " + textlink)
    method = "sendMessage"
    token = "5482849148:AAGqg2JLMvQDD-wW7TAZApSaPZyUebYTZFQ"
    url = f"https://api.telegram.org/bot{token}/{method}"
    my_chat = "https://t.me/i_i_evdokimov"
    msg = f"New update on sellaris site!\n{current_user.username} posted:\n{textlink}"
    data = {"chat_id": chat_id, "text": msg}
    requests.post(url, data=data)
    return True


'''
<div class="alert alert-info">   
        {% for img in images %}
        <img src="{{ url_for('single_img', filename=img.file_name) }}" style="height: 256px">
        <p>{{ "#comment" }}</p>
        {% endfor %}
        </div>
'''