﻿
from . import db,login_manager
from werkzeug.security import generate_password_hash,check_password_hash
from flask.ext.login import UserMixin,AnonymousUserMixin
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from flask import current_app,request,url_for
from datetime import datetime
import hashlib
from markdown import markdown
import bleach
from app.exceptions import ValidationError

#关注关联表的模型
class Follow(db.Model):
	__tablename__ = 'follows'
	follower_id = db.Column(db.Integer,db.ForeignKey('users.id'),primary_key=True)
	followed_id = db.Column(db.Integer,db.ForeignKey('users.id'),primary_key=True)
	timestamp = db.Column(db.DateTime,default=datetime.utcnow)

#权限常量
class Permission:
	FOLLOW = 0x01              #关注其他用户
	COMMENT = 0x02             #发表评论
	WRITE_ARTICLES = 0x04       #写文章
	MODERATE_COMMENTS = 0x08   #查处他人发表的不当评论
	ADMINISTER = 0x80          #管理网站

#角色模型
class Role(db.Model):
	__tablename__  = 'roles'
	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(64), unique=True)
	default = db.Column(db.Boolean,default = False, index = True)
	permissions = db.Column(db.Integer)
	users = db.relationship('User', backref='role', lazy = 'dynamic')
	
	@staticmethod
	def insert_roles():
		roles = {
			'User':(Permission.FOLLOW | Permission.COMMENT | Permission.WRITE_ARTICLES, True),
			'Moderator':(Permission.FOLLOW | Permission.COMMENT | Permission.WRITE_ARTICLES | 
						Permission.MODERATE_COMMENTS, False),
			'Administrator':(0xff,False)
			}
		for r in roles:
			role = Role.query.filter_by(name = r).first()
			if role is None:
				role = Role(name = r)
			role.permissions = roles[r][0]
			role.default = roles[r][1]
			db.session.add(role)
		db.session.commit()
	
	def __repr__(self):
		return '<Role %r>' %self.name

#用户模型
class User(UserMixin,db.Model):
	__tablename__ = 'users'
	id = db.Column(db.Integer, primary_key=True)
	email = db.Column(db.String(64), unique=True, index=True)
	username = db.Column(db.String(64), unique=True, index=True)
	role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
	password_hash = db.Column(db.String(128))
	confirmed = db.Column(db.Boolean,default=False)
	name = db.Column(db.String(64))
	location = db.Column(db.String(64))
	about_me = db.Column(db.Text())  #db.text()不需要指定最大长度
	member_since = db.Column(db.DateTime(), default=datetime.utcnow)
	last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
	avatar_hash = db.Column(db.String(32))
	posts = db.relationship('Post',backref='author',lazy='dynamic')
	followed = db.relationship('Follow',foreign_keys=[Follow.follower_id],
							backref=db.backref('follower',lazy='joined'),
							lazy='dynamic',cascade='all,delete-orphan')
	followers = db.relationship('Follow',foreign_keys=[Follow.followed_id],
							backref=db.backref('followed',lazy='joined'),
							lazy='dynamic',cascade='all,delete-orphan')
	
	def to_json(self):
		json_user ={
			'url':url_for('api.get_post',id=self.id,_external=True),
			'username': self.username,
			'member_since': self.member_since,
			'last_seen': self.last_seen,
			'posts': url_for('api.get_user_posts', id=self.id, _external=True),
			'followed_posts': url_for('api.get_user_followed_posts',id=self.id, _external=True),
			'post_count': self.posts.count()
			}
		return json_user
		
		
	
	def generate_auth_token(self,expiration):
		s = Serializer(current_app.config['SECRET_KEY'],expires_in=expiration)
		return s.dumps(({'id':self.id}))
	
	@staticmethod
	def verify_auth_token(token):
		s = Serializer(current_app.config['SECRET_KEY'])
		try:
			data = s.loads(token)
		except:
			return None
		return User.query.get(data['id'])
	
	#获取所关注用户的文章
	@property
	def followed_posts(self):
		return Post.query.join(Follow,Follow.followed_id == Post.author_id).filter(Follow.follower_id == self.id)
	
	#关注
	def follow(self,user):
		if not self.is_following(user):
			f = Follow(follower=self,followed=user)
			db.session.add(f)
	
	#取消关注		
	def unfollow(self,user):
		f = self.followed.filter_by(followed_id=user.id).first()
		if f:
			db.session.delete(f)
			
	def is_following(self,user):
		return self.followed.filter_by(followed_id=user.id).first() is not None
	
	def is_followed_by(self,user):
		return self.followers.filter_by(follower_id=user.id).first() is not None
	
	@staticmethod
	def generate_fake(count=100):
		from sqlalchemy.exc import IntegrityError
		from random import seed
		import forgery_py
		
		seed()
		for i in range(count):
			u = User(email=forgery_py.internet.email_address(),
					username=forgery_py.internet.user_name(),
					password=forgery_py.lorem_ipsum.word(),
					confirmed=True,
					name=forgery_py.name.full_name(),
					location=forgery_py.address.city(),
					about_me=forgery_py.lorem_ipsum.sentence(),
					member_since=forgery_py.date.date(True))
			db.session.add(u)
			try:
				db.session.commit()
			except IntegrityError:
				db.session.rollback()
	
	#更新已登录用户的访问时间
	def ping(self):
		self.last_seen = datetime.utcnow()
		db.session.add(self)
	
	#定义默认的用户角色
	def __init__(self,**kwargs):
		super(User,self).__init__(**kwargs)
		if self.role is None:
			if self.email == current_app.config['FLASKY_ADMIN']:
				self.role = Role.query.filter_by(permissions = 0xff).first()
			if self.role is None:
				self.role = Role.query.filter_by(default=True).first()
		if self.email is not None and self.avatar_hash is None:
			self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
			
	
				
	#生成 Gravatar URL
	def gravatar(self,size=100,default='identicon',rating='g'):
		if request.is_secure:
			url = 'https://secure.gravatar.com/avatar'
		else:
			url = 'http://www.gravatar.com/avatar'
		hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
		return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
			url=url,hash=hash,size=size,default=default,rating=rating)
	
	#检查用户是否有指定的权限
	def can(self,permissions):
		return self.role is not None and (self.role.permissions & permissions) == permissions
	
	def is_administrator(self):
		return self.can(Permission.ADMINISTER)
	
	def generate_confirmation_token(self,expiration=3600):
		s = Serializer(current_app.config['SECRET_KEY'],expiration)
		return s.dumps({'confirm':self.id})  #为指定的数据生成一个加密签名，然后对数据和签名进行序列化，生成令牌字符串
	
	def confirm(self,token):
		s = Serializer(current_app.config['SECRET_KEY'])
		try:
			data = s.loads(token)
		except:
			return False
		if data.get('confirm') != self.id:
			return False
		self.confirmed = True
		db.session.add(self)
		return True
	
	#更换邮箱
	def change_email(self,token):
		s = Serializer(current_app.config['SECRET_KEY'])
		try:
			data = s.loads(token.encode('utf-8'))
		except:
			return False
		if data.get('change_email') != self.id:
			return False
		new_email = data.get('new_email')
		if new_email is None:
			return False
		if self.query.filter_by(email=new_email).first() is not None:
			return False
		self.email = new_email
		self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
		db.session.add(self)
		return True
	
	@property
	def password(self):
		raise AttributeError('password is not a readable attribute')
	
	@password.setter
	def password(self,password):
		self.password_hash = generate_password_hash(password)
		
	def verify_password(self, password):
		return check_password_hash(self.password_hash, password)
	
	def __repr__(self):
		return '<User %r>' % self.username
	
class AnonymousUser(AnonymousUserMixin):
	def can(self,permissions):
		return False
	
	def is_administrator(self):
		return False
	
#博客模型
class Post(db.Model):
	__tablename__='posts'
	id = db.Column(db.Integer,primary_key=True)
	body = db.Column(db.Text)
	body_html = db.Column(db.Text)
	timestamp = db.Column(db.DateTime,index=True,default=datetime.utcnow)
	author_id = db.Column(db.Integer,db.ForeignKey('users.id'))
	
	@staticmethod
	def from_json(json_post):
		body = json_post.get('body')
		if body is None or body == '':
			raise ValidationError('post does not have a body')
		return Post(body=body)
	
	@staticmethod
	def on_change_body(target, value, oldvalue, initiator):
		allowed_tags = ['a', 'abbr', 'acronym', 'b', 'blockquote', 'code',
					'em', 'i', 'li', 'ol', 'pre', 'strong', 'ul',
					'h1', 'h2', 'h3', 'p']
		target.body_html = bleach.linkify(bleach.clean(markdown(value,output_format='html'),
													tags=allowed_tags,strip=True))
		db.event.listen(Post.body,'set',Post.on_change_body) 
	
	def to_json(self):
		json_post={
			'url':url_for('api.get_post',id=self.id,_external=True),
			'body':self.body,
			'body_html':self.body_html,
			'timestamp':self.timestamp,
			'author':url_for('api.get_user',id=self.author_id,_external=True)
			}
		return json_post
	
	@staticmethod
	def generate_fake(count=100):
		from random import seed,randint
		import forgery_py
		
		seed()
		user_count = User.query.count()
		for i in range(count):
			u = User.query.offset(randint(0,user_count -1)).first()
			p = Post(body=forgery_py.lorem_ipsum.sentences(randint(1,3)),
					timestamp=forgery_py.date.date(True),author=u)
			db.session.add(p)
			db.session.commit()
			

		
	
login_manager.anonymous_user = AnonymousUser

@login_manager.user_loader
def load_user(user_id):
	return User.query.get(int(user_id))