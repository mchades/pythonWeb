#路由
from datetime import datetime
from flask import render_template, session, redirect, url_for,flash,request,current_app,make_response
from flask.ext.login import login_required,current_user
from . import main
from .forms import NameForm,EditProfileForm,EditProfileAdminForm,PostForm
from .. import db
from ..decorators import admin_required,permission_required
from ..models import User,Permission,Post
from ..mail import send_email



@main.route('/',methods=['GET','POST'])
def index():
        form=PostForm()
        if current_user.can(Permission.WRITE_ARTICLES) and form.validate_on_submit():
            post = Post(body=form.body.data,author=current_user._get_current_object())
            db.session.add(post)
            return redirect(url_for('.index'))        
        page = request.args.get('page',1,type=int)
        show_followed = False
        if current_user.is_authenticated:
            show_followed = bool(request.cookies.get('show_followed',''))
        if show_followed:
            query = current_user.followed_posts
        else:
            query = Post.query
        pagination = query.order_by(Post.timestamp.desc()).paginate(
            page,per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
            error_out=False)                 #paginate() 方法的返回值是一个Pagination 类对象
        posts = pagination.items
        return render_template('index.html',form=form,posts=posts,
                               show_followed=show_followed,pagination=pagination)
        
        
@main.route('/user/<username>')
def user(username):
    user = User.query.filter_by(username = username).first()
    if user is None:
        abort(404)
    page = request.args.get('page',1,type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page,per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)                 #paginate() 方法的返回值是一个Pagination 类对象
    posts = pagination.items
    return render_template('user.html',user=user,posts=posts,pagination=pagination)

@main.route('/edit-profile',methods=['GET','POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name = form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        db.session.add(current_user)
        flash(u'保存成功')
        return redirect(url_for('.user',username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)

@main.route('/edit-profile/<int:id>',methods=['GET','POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    # Flask-SQLAlchemy 提供的 get_or_404() 函数，如果提供的 id不正确，则会返回 404 错误。
    user = User.query.get_or_404(id)  
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash(u'保存成功')
        return redirect(url_for('.user',username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form, user=user)

#博客链接
@main.route('/post/<int:id>')
def post(id):
    post = Post.query.get_or_404(id)
    return render_template('post.html',posts=[post])

@main.route('/edit/<int:id>',methods=['GET','POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and not current_user.can(Permission.ADMINISTER):
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.body = form.body.data
        db.session.add(post)
        flash(u'博客已保存')
        return redirect(url_for('.post',id=post.id))
    form.body.data = post.body
    return render_template('edit_post.html',form=form)

#关注路由
@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(u'非法用户')
        return redirect(url_for('.index'))
    if current_user.is_following(user):
        falsh(u'已关注')
        return redirect(url_for('.user',username=username))
    current_user.follow(user)
    flash(u'成功关注 %s' %username)
    return redirect(url_for('.user',username=username))

#取消关注路由
@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(u'非法用户')
        return redirect(url_for('.index'))
    if not current_user.is_following(user):
        flash(u'还未关注')
        return redirect(url_for('.user', username=username))
    current_user.unfollow(user)
    db.session.commit()
    flash(u'已经取消对  %s 的关注' % username)
    return redirect(url_for('.user', username=username))

#关注的人路由
@main.route('/followers/<username>')
def followers(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash(u'非法用户')
        return redirect(url_for('.index'))
    page = request.args.get('page',1,type=int)
    pagination = user.followers.paginate(page,per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],error_out=False)
    follows = [{'user':item.follower,'timestamp':item.timestamp} for item in pagination.items]
    return render_template('followers.html',user=user,title=u"我关注的人",
                           endpoint='.followers',pagination=pagination,follows=follows)
    
#粉丝路由
@main.route('/followed_by/<username>')
def followed_by(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        falsh(u'非法用户')
        return redirect(url_for('.index'))
    page = request.args.get('page',1,type=int)
    pagination = user.followed.paginate(page,per_page=current_app.config['FLASKY_FOLLOWERS_PER_PAGE'],error_out=False)
    follows = [{'user':item.followed,'timestamp':item.timestamp} for item in pagination.items]
    return render_template('followers.html',user=user,title=u"被关注",endpoint='.followed_by',
                           pagination=pagination,follows=follows)
    
@main.route('/all')
@login_required
def show_all():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed','',max_age=30*24*60*60)  #coockie只能在响应对象中设置
    return resp

@main.route('/followed')
@login_required
def show_followed():
    resp = make_response(redirect(url_for('.index')))
    resp.set_cookie('show_followed','1',max_age=30*24*60*60) #(cookie名，值，过期时间)
    return resp




