from flask import render_template, redirect, request, url_for, flash
from flask.ext.login import login_user,login_required,logout_user,current_user
from . import auth
from ..models import User
from .forms import LoginForm,RegistrationForm
from ..mail import send_email
from .. import db

@auth.route('/login',methods=['GET','POST'])
def login():
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		if user is not None and user.verify_password(form.password.data):
			login_user(user,form.remember_me.data)
			return redirect(request.args.get('next') or url_for('main.index'))
		flash(u'账户或者用户名不正确')
	return render_template('auth/login.html',form=form)

@auth.route('/logout')
@login_required
def logout():
	logout_user()
	flash(u'成功登出')
	return redirect(url_for('main.index'))

@auth.route('/register',methods=['GET','POST'])
def register():
	form = RegistrationForm()
	if form.validate_on_submit():
		user = User(email=form.email.data,username=form.username.data,password=form.password.data)
		db.session.add(user)
		db.session.commit()
		token = user.generate_confirmation_token()
		send_email(user.email,u'确认你的账户','auth/email/confirm',user=user, token=token)
		flash(u'请前往邮箱确认注册邮件')
		return redirect('main.index')
	return render_template('auth/register.html',form=form)

@auth.route('/confirm/<token>')
@login_required
def confirm(token):
	if current_user.confirmed:
		return redirect(url_for('main.index'))
	if current_user.confirm(token):
		flash(u'你已经确认过该账户')
	else:
		flash(u'链接已失效')
	return redirect(url_for('main.index'))

@auth.before_app_request
def before_request():
	if current_user.is_authenticated:
		current_user.ping()
		if not current_user.confirmed and request.endpoint[:5] != 'auth.':
			return redirect(url_for('auth.unconfirmed'))
@auth.route('/unconfirmed')
def unconfirmed():
	if current_user.is_anonymous or current_user.confirmed:
		return redirect(url_for('main.index'))
	return render_template('auth/unconfirmed.html')

@auth.route('/confirm')
@login_required
def resend_confirmation():
	token = current_user.generate_confirmation_token()
	send_email(current_user.email, 'Confirm Your Account',
			'auth/email/confirm', user=current_user, token=token)
	flash('A new confirmation email has been sent to you by email.')
	return redirect(url_for('main.index'))