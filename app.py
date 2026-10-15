import os, csv, io, uuid, secrets, urllib.request, urllib.error, urllib.parse, calendar, zipfile, re, unicodedata
from collections import defaultdict
from datetime import timedelta
from datetime import datetime, timezone
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file, abort, Response
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func, text
from zoneinfo import ZoneInfo

app=Flask(__name__)
app.secret_key=os.environ.get('SECRET_KEY','dev-only-change-me')
app.config.update(SESSION_COOKIE_SECURE=os.environ.get('RENDER')=='true', SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Lax')
app.config['MAX_CONTENT_LENGTH']=15*1024*1024
base=os.environ.get('DATA_DIR',os.path.join(os.path.dirname(__file__),'data'))
os.makedirs(base,exist_ok=True)
url=os.environ.get('DATABASE_URL',f'sqlite:///{os.path.join(base,"ponto.db")}')
if os.environ.get('RENDER')=='true' and (not os.environ.get('DATABASE_URL') or not os.environ.get('SUPABASE_URL') or not os.environ.get('SUPABASE_SERVICE_ROLE_KEY')):
 raise RuntimeError('Configure DATABASE_URL, SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY no Render antes de iniciar.')
if url.startswith('postgres://'): url='postgresql://'+url[11:]
app.config['SQLALCHEMY_DATABASE_URI']=url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS']=False
db=SQLAlchemy(app)
TZ=ZoneInfo('America/Sao_Paulo')
class User(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 name=db.Column(db.String(160),nullable=False)
 username=db.Column(db.String(80),unique=True,nullable=False)
 password=db.Column(db.String(255),nullable=False)
 role=db.Column(db.String(20),default='employee',nullable=False)
 active=db.Column(db.Boolean,default=True)
 archived=db.Column(db.Boolean,default=False,nullable=False)
 failed_attempts=db.Column(db.Integer,default=0,nullable=False)
 locked_until=db.Column(db.DateTime(timezone=True),nullable=True)
 login_blocked=db.Column(db.Boolean,default=False,nullable=False)
class Punch(db.Model):
 id=db.Column(db.Integer,primary_key=True)
 user_id=db.Column(db.Integer,db.ForeignKey('user.id'),nullable=False,index=True)
 kind=db.Column(db.String(10),nullable=False)
 created_at=db.Column(db.DateTime(timezone=True),nullable=False,default=lambda:datetime.now(timezone.utc))
 lat=db.Column(db.Float,nullable=False)
 lng=db.Column(db.Float,nullable=False)
 accuracy=db.Column(db.Float,nullable=False)
 worksite=db.Column(db.String(160),nullable=False)
 machine=db.Column(db.String(160),nullable=False)
 face=db.Column(db.String(120),nullable=False)
 machine_photo=db.Column(db.String(120),nullable=False)
 user=db.relationship('User')
with app.app_context():
 # Migração não destrutiva para instalações existentes (PostgreSQL e SQLite).
 with db.engine.begin() as conn:
  columns={c['name'] for c in __import__('sqlalchemy').inspect(conn).get_columns('user')} if __import__('sqlalchemy').inspect(conn).has_table('user') else set()
  if columns and 'archived' not in columns:
   conn.execute(text('ALTER TABLE "user" ADD COLUMN archived BOOLEAN NOT NULL DEFAULT FALSE'))
 db.create_all()
 # Migração não destrutiva dos campos de segurança de login.
 with db.engine.begin() as conn:
  existing={c['name'] for c in __import__('sqlalchemy').inspect(conn).get_columns('user')}
  for col,ddl in [('failed_attempts','INTEGER NOT NULL DEFAULT 0'),('locked_until','TIMESTAMP NULL'),('login_blocked','BOOLEAN NOT NULL DEFAULT FALSE')]:
   if col not in existing:conn.execute(text('ALTER TABLE "user" ADD COLUMN '+col+' '+ddl))
 admin=os.environ.get('ADMIN_USER','admin')
 password=os.environ.get('ADMIN_PASSWORD')
 if password and not User.query.filter_by(username=admin).first():
  db.session.add(User(name='Administrador',username=admin,password=generate_password_hash(password),role='admin'));db.session.commit()

def auth(role=None):
 def deco(f):
  @wraps(f)
  def wrapper(*a,**kw):
   u=db.session.get(User,session.get('uid')) if session.get('uid') else None
   if not u or not u.active or u.archived:return redirect(url_for('login'))
   if role and u.role!=role:abort(403)
   return f(*a,**kw)
  return wrapper
 return deco
@app.context_processor
def globals_():
 return {'current_user':db.session.get(User,session['uid']) if session.get('uid') else None,'localtime':lambda dt:dt.replace(tzinfo=timezone.utc).astimezone(TZ).strftime('%d/%m/%Y %H:%M:%S') if dt else ''}
@app.before_request
def csrf_check():
 if request.method=='POST':
  if not session.get('csrf') or request.form.get('csrf')!=session.get('csrf'):abort(400,'Token de segurança inválido')
@app.route('/')
def index():return redirect(url_for('admin') if session.get('role')=='admin' else url_for('employee')) if session.get('uid') else redirect(url_for('login'))
@app.route('/login',methods=['GET','POST'])
def login():
 if request.method=='POST':
  username=request.form.get('username','').strip().lower()
  password=request.form.get('password','')
  u=User.query.filter(func.lower(User.username)==username).first()
  now=datetime.now(timezone.utc)
  if u and u.role=='employee' and u.login_blocked:
   flash('Conta bloqueada por tentativas incorretas. Solicite liberação ao administrador.','error')
  elif u and u.role=='employee' and u.locked_until and (u.locked_until.replace(tzinfo=timezone.utc) if u.locked_until.tzinfo is None else u.locked_until)>now:
   remaining=int(((u.locked_until.replace(tzinfo=timezone.utc) if u.locked_until.tzinfo is None else u.locked_until)-now).total_seconds())+1
   flash(f'Aguarde {remaining} segundos para tentar novamente.','error')
  elif u and u.active and not u.archived and check_password_hash(u.password,password):
   if u.role=='employee':
    u.failed_attempts=0;u.locked_until=None;db.session.commit()
   session.clear();session['uid']=u.id;session['role']=u.role;session['csrf']=secrets.token_urlsafe(32)
   return redirect(url_for('admin' if u.role=='admin' else 'employee'))
  else:
   if u and u.role=='employee' and u.active and not u.archived:
    u.failed_attempts=(u.failed_attempts or 0)+1
    attempts=u.failed_attempts
    if attempts==6:u.locked_until=now+timedelta(seconds=30)
    elif attempts==7:u.locked_until=now+timedelta(minutes=1)
    elif attempts==8:u.locked_until=now+timedelta(minutes=2)
    elif attempts>=9:u.login_blocked=True;u.locked_until=None
    db.session.commit()
    if u.login_blocked:flash('Conta bloqueada. Solicite liberação ao administrador.','error')
    elif attempts in (6,7,8):flash('Muitas tentativas incorretas. Aguarde '+str({6:30,7:60,8:120}[attempts])+' segundos.','error')
    else:flash('Usuário ou senha inválidos.','error')
   else:flash('Usuário ou senha inválidos.','error')
 if 'csrf' not in session:session['csrf']=secrets.token_urlsafe(32)
 return render_template('login.html')
@app.post('/logout')
def logout():session.clear();return redirect(url_for('login'))
@app.route('/funcionario')
@auth('employee')
def employee():
 last=Punch.query.filter_by(user_id=session['uid']).order_by(Punch.id.desc()).first()
 recent=Punch.query.filter_by(user_id=session['uid']).order_by(Punch.id.desc()).limit(20).all()
 return render_template('employee.html',last=last,recent=recent)
def storage_request(path, data=None, mimetype=None):
 root=os.environ.get('SUPABASE_URL','').rstrip('/')
 key=os.environ.get('SUPABASE_SERVICE_ROLE_KEY','')
 if not root or not key:raise ValueError('Armazenamento remoto não configurado.')
 headers={'apikey':key,'Authorization':'Bearer '+key}
 if mimetype:headers['Content-Type']=mimetype
 req=urllib.request.Request(root+'/storage/v1/object/'+path,data=data,headers=headers,method='POST' if data is not None else 'GET')
 try:
  with urllib.request.urlopen(req,timeout=30) as r:return r.read(),r.headers.get('Content-Type','application/octet-stream')
 except urllib.error.HTTPError as e:
  raise ValueError('Falha no armazenamento de fotos (HTTP %s). Confira o bucket privado e as credenciais.'%e.code)

def save_image(file,uid,kind):
 if not file or not file.filename:raise ValueError('As duas fotos são obrigatórias.')
 if file.mimetype not in ('image/jpeg','image/png','image/webp'):raise ValueError('Envie fotos JPG, PNG ou WebP.')
 data=file.read(8*1024*1024+1)
 if len(data)>8*1024*1024:raise ValueError('Cada foto deve ter até 8 MB.')
 if not (data.startswith(b'\xff\xd8\xff') or data.startswith(b'\x89PNG\r\n\x1a\n') or (data.startswith(b'RIFF') and data[8:12]==b'WEBP')):raise ValueError('Formato de imagem inválido.')
 ext={'image/jpeg':'jpg','image/png':'png','image/webp':'webp'}[file.mimetype]
 name=f'{uid}_{kind}_{uuid.uuid4().hex}.{ext}'
 bucket=os.environ.get('SUPABASE_BUCKET','ponto-fotos')
 storage_request(urllib.parse.quote(bucket)+'/'+urllib.parse.quote(name),data,file.mimetype)
 return name
@app.post('/marcar')
@auth('employee')
def punch():
 try:
  kind=request.form.get('kind')
  if kind not in ('entrada','saida'):raise ValueError('Tipo de ponto inválido.')
  last=Punch.query.filter_by(user_id=session['uid']).order_by(Punch.id.desc()).first()
  if (last and last.kind==kind) or (not last and kind!='entrada'):raise ValueError('Registre entrada e saída em sequência.')
  lat=float(request.form['lat']);lng=float(request.form['lng']);accuracy=float(request.form['accuracy'])
  if not (-90<=lat<=90 and -180<=lng<=180 and 0<=accuracy<=10000):raise ValueError('Localização inválida.')
  worksite=request.form.get('worksite','').strip()[:160];machine=request.form.get('machine','').strip()[:160]
  if not worksite or not machine:raise ValueError('Informe obra e máquina.')
  face=save_image(request.files.get('face'),session['uid'],'rosto')
  machine_photo=save_image(request.files.get('machine_photo'),session['uid'],'maquina')
  db.session.add(Punch(user_id=session['uid'],kind=kind,lat=lat,lng=lng,accuracy=accuracy,worksite=worksite,machine=machine,face=face,machine_photo=machine_photo));db.session.commit()
  flash('Ponto registrado e disponível ao administrador.','success')
 except (ValueError,KeyError) as e:flash(str(e),'error')
 return redirect(url_for('employee'))
@app.route('/admin')
@auth('admin')
def admin():
 month=request.args.get('mes',datetime.now(TZ).strftime('%Y-%m'))
 try:
  start=datetime.strptime(month+'-01','%Y-%m-%d');end=datetime(start.year+(start.month==12),start.month%12+1,1)
 except ValueError:abort(400)
 uid=request.args.get('funcionario',type=int)
 q=Punch.query.filter(Punch.created_at>=start.replace(tzinfo=TZ).astimezone(timezone.utc).replace(tzinfo=None),Punch.created_at<end.replace(tzinfo=TZ).astimezone(timezone.utc).replace(tzinfo=None))
 if uid:q=q.filter_by(user_id=uid)
 rows=q.order_by(Punch.created_at.desc()).all()
 users=User.query.filter_by(role='employee',archived=False).order_by(User.name).all()
 archived_users=User.query.filter_by(role='employee',archived=True).order_by(User.name).all()
 return render_template('admin.html',rows=rows,users=users,archived_users=archived_users,month=month,uid=uid)
@app.post('/admin/funcionarios')
@auth('admin')
def create_user():
 name=request.form.get('name','').strip();username=request.form.get('username','').strip().lower();pw=request.form.get('password','')
 if len(name)<2 or len(username)<3 or len(pw)<6:flash('Informe nome, usuário (mín. 3) e senha (mín. 6 caracteres).','error')
 elif User.query.filter(func.lower(User.username)==username).first():flash('Este usuário já existe.','error')
 else:
  db.session.add(User(name=name,username=username,password=generate_password_hash(pw),role='employee'));db.session.commit();flash('Funcionário cadastrado.','success')
 return redirect(url_for('admin'))
@app.post('/admin/funcionarios/<int:uid>/redefinir-senha')
@auth('admin')
def reset_employee_password(uid):
 u=db.session.get(User,uid)
 if not u or u.role!='employee' or u.archived:abort(404)
 pw=request.form.get('new_password','')
 if len(pw)<6 or len(pw)>128:
  flash('A nova senha deve ter de 6 a 128 caracteres.','error')
 else:
  u.password=generate_password_hash(pw)
  db.session.commit()
  flash('Senha de '+u.name+' redefinida com sucesso.','success')
 return redirect(url_for('admin'))


@app.post('/admin/funcionarios/<int:uid>/desbloquear-login')
@auth('admin')
def unlock_employee_login(uid):
 u=db.session.get(User,uid)
 if not u or u.role!='employee' or u.archived:abort(404)
 u.failed_attempts=0;u.locked_until=None;u.login_blocked=False
 db.session.commit()
 flash('Bloqueio de login removido para '+u.name+'.','success')
 return redirect(url_for('admin'))

@app.post('/admin/funcionarios/<int:uid>/status')
@auth('admin')
def toggle_user(uid):
 u=db.session.get(User,uid)
 if not u or u.role!='employee' or u.archived:abort(404)
 u.active=not u.active;db.session.commit();return redirect(url_for('admin'))
@app.post('/admin/funcionarios/<int:uid>/excluir')
@auth('admin')
def archive_user(uid):
 u=db.session.get(User,uid)
 if not u or u.role!='employee' or u.archived:abort(404)
 # Exclusão lógica: mantém os registros de ponto e fotos para auditoria.
 u.active=False
 u.archived=True
 db.session.commit()
 flash('Cadastro removido da lista ativa. Histórico de ponto preservado.','success')
 return redirect(url_for('admin'))

@app.post('/admin/funcionarios/<int:uid>/restaurar')
@auth('admin')
def restore_user(uid):
 u=db.session.get(User,uid)
 if not u or u.role!='employee' or not u.archived:abort(404)
 u.archived=False
 u.active=False  # Administração precisa ativar explicitamente depois.
 db.session.commit()
 flash('Cadastro restaurado como inativo. Ative-o quando necessário.','success')
 return redirect(url_for('admin'))

@app.route('/admin/foto/<int:pid>/<which>')
@auth('admin')
def photo(pid,which):
 p=db.session.get(Punch,pid)
 if not p or which not in ('face','machine_photo'):abort(404)
 name=getattr(p,which)
 data,mime=storage_request(urllib.parse.quote(os.environ.get('SUPABASE_BUCKET','ponto-fotos'))+'/'+urllib.parse.quote(name))
 return Response(data,mimetype=mime,headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'})
def monthly_daily_report(month, uid=None):
 try:
  year,mon=map(int,month.split('-'))
  if len(month)!=7 or not 1<=mon<=12:raise ValueError()
  start=datetime(year,mon,1,tzinfo=TZ)
  end=datetime(year+int(mon==12),mon%12+1,1,tzinfo=TZ)
 except (ValueError,TypeError):abort(400,'Mês inválido')
 users=User.query.filter_by(role='employee').order_by(User.name,User.id).all()
 if uid:users=[u for u in users if u.id==uid]
 if not users:return []
 ids=[u.id for u in users]
 punches=Punch.query.filter(Punch.user_id.in_(ids),Punch.created_at>=start.astimezone(timezone.utc).replace(tzinfo=None),Punch.created_at<end.astimezone(timezone.utc).replace(tzinfo=None)).order_by(Punch.user_id,Punch.created_at,Punch.id).all()
 grouped=defaultdict(list)
 for p in punches:grouped[p.user_id].append(p)
 result=[]
 for u in users:
  per_day=defaultdict(lambda:{'entradas':[],'saidas':[],'segundos':0,'observacoes':[]})
  # Entrada e saída são pareadas cronologicamente; intervalos sem saída não são somados.
  # Para turnos atravessando a meia-noite, distribui-se o tempo em cada dia local.
  all_punches=Punch.query.filter_by(user_id=u.id).filter(Punch.created_at<end.astimezone(timezone.utc).replace(tzinfo=None)).order_by(Punch.created_at,Punch.id).all()
  open_entry=None
  for p in all_punches:
   dt=p.created_at.replace(tzinfo=timezone.utc).astimezone(TZ) if p.created_at.tzinfo is None else p.created_at.astimezone(TZ)
   if start<=dt<end:
    if p.kind=='entrada':per_day[dt.date()]['entradas'].append(dt.strftime('%H:%M:%S'))
    else:per_day[dt.date()]['saidas'].append(dt.strftime('%H:%M:%S'))
   if p.kind=='entrada':open_entry=dt
   elif open_entry is not None and dt>=open_entry:
    cursor=max(open_entry,start)
    stop=min(dt,end)
    while cursor<stop:
     next_midnight=datetime(cursor.year,cursor.month,cursor.day,tzinfo=TZ)+timedelta(days=1)
     segment_end=min(stop,next_midnight)
     per_day[cursor.date()]['segundos']+=int((segment_end-cursor).total_seconds())
     cursor=segment_end
    open_entry=None
  for day in range(1,calendar.monthrange(year,mon)[1]+1):
   date=datetime(year,mon,day).date();d=per_day[date]
   note='Sem registro' if not d['entradas'] and not d['saidas'] and not d['segundos'] else ('Conferir marcações' if len(d['entradas'])!=len(d['saidas']) else '')
   result.append([u.name,u.username,date.strftime('%d/%m/%Y'),' | '.join(d['entradas']),' | '.join(d['saidas']),f"{d['segundos']//3600:02d}:{(d['segundos']%3600)//60:02d}:{d['segundos']%60:02d}",note])
 return result

def report_csv(rows):
 out=io.StringIO();writer=csv.writer(out,delimiter=';',lineterminator='\r\n')
 writer.writerow(['Funcionário','Usuário','Data','Entrada(s)','Saída(s)','Total de horas do dia','Observações'])
 for row in rows:
  # Proteção contra fórmula CSV no Excel/LibreOffice
  writer.writerow([("'"+str(v) if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v) for v in row])
 return ('\ufeff'+out.getvalue()).encode('utf-8')

@app.route('/admin/relatorio.csv')
@auth('admin')
def csv_report():
 month=request.args.get('mes',datetime.now(TZ).strftime('%Y-%m'))
 uid=request.args.get('funcionario',type=int)
 data=report_csv(monthly_daily_report(month,uid))
 return Response(data,mimetype='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename=ponto_diario_{month}.csv'})

@app.route('/admin/relatorios-por-funcionario.zip')
@auth('admin')
def csv_report_per_employee():
 month=request.args.get('mes',datetime.now(TZ).strftime('%Y-%m'))
 uid=request.args.get('funcionario',type=int)
 rows=monthly_daily_report(month,uid)
 groups=defaultdict(list)
 for r in rows:groups[(r[0],r[1])].append(r)
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:
  for (name,username),items in groups.items():
   safe=re.sub(r'[^a-zA-Z0-9_-]+','_',unicodedata.normalize('NFKD',name).encode('ascii','ignore').decode()).strip('_')[:50]
   z.writestr(f'{safe or "funcionario"}_{items[0][1]}_{month}.csv',report_csv(items))
 buf.seek(0)
 return send_file(buf,mimetype='application/zip',as_attachment=True,download_name=f'ponto_por_funcionario_{month}.zip')
if __name__=='__main__':app.run(debug=False)
