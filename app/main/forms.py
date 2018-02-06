#保存表单对象
from flask.ext.wtf import FlaskForm
from wtforms import StringField, SubmitField,TextAreaField,SelectField,BooleanField
from wtforms.validators import Required,Length,Email,Regexp
from ..models import User,Role
from flask.ext.pagedown.fields import PageDownField

class NameForm(FlaskForm):
    name=StringField('What is your name?',validators=[Required()])
    submit=SubmitField('Submit')
    
#普通用户资料编辑表单
class EditProfileForm(FlaskForm):
    name = StringField(u'真实姓名',validators=[Length(0,64)])
    location = StringField(u'地区',validators=[Length(0,64)])
    about_me = TextAreaField(u'个人简介')
    submit = SubmitField(u'提交')
    
#管理员资料编辑表单
class EditProfileAdminForm(FlaskForm):
    email = StringField(u'邮箱',validators=[Required(), Length(1, 64),Email()])
    username = StringField(u'用户名',validators=[Required(), Length(1, 64), Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
                                                                                u'用户名只能包含字母、数字、小数点和下划线')])
    confirmed = BooleanField(u'已通过邮件确认')
    role = SelectField(u'权限',coerce=int)
    name = StringField(u'昵称',validators=[Length(0,64)])
    location = StringField(u'地区',validators=[Length(0,64)])
    about_me = TextAreaField(u'个人简历')
    submit = SubmitField(u'提交')
    
    def __init__(self,user,*args,**Kwargs):
        super(EditProfileAdminForm,self).__init__(*args,**Kwargs)
        self.role.choices = [(role.id,role.name) for role in Role.query.order_by(Role.name).all()]
        self.user = user
    
    def validate_email(self,field):
        if field.data != self.user.email and User.query.filter_by(email=field.data).first():
            raise ValidationError(u'邮箱已注册')
        
    def validate_username(self,field):
        if field.data != self.username and User.query.filter_by(username=field.data).first():
            raise ValidationError(u'用户名已被使用')
        
class PostForm(FlaskForm):
    body = PageDownField(u"写点什么",validators=[Required()])
    submit = SubmitField(u'提交')
        