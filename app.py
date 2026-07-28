import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'aiden_secret_portfolio_key'

UPLOAD_FOLDER = os.path.join('static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'glb'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Çoka-Çok İlişki Tablosu (Büyük Proje ile Tekil Portfolyo Öğelerini Bağlar)
project_items = db.Table('project_items',
    db.Column('major_project_id', db.Integer, db.ForeignKey('major_project.id'), primary_key=True),
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True)
)

# 1. Tekil Eser / Asset Tablosu (Eski Project)
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)
    tags = db.Column(db.String(100), nullable=True)
    image = db.Column(db.String(200), nullable=False)
    model_file = db.Column(db.String(200), nullable=True)
    youtube_url = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow) # YENİ: Eklenme Tarihi

    def get_tags_list(self):
        if self.tags:
            return [t.strip() for t in self.tags.split(',')]
        return []

# 2. YENİ: Büyük Proje Tablosu (Örn: Ormanlık Alan Konsepti)
class MajorProject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    image = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    items = db.relationship('Project', secondary=project_items, lazy='subquery',
                            backref=db.backref('major_projects', lazy=True))

    # Hatanın çözümü için bu fonksiyonu buraya da ekledik:
    def get_tags_list(self):
        return []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    # En son eklenen 1 veya 3 büyük projeyi çekiyoruz (LATEST PROJECTS için)
    latest_projects = MajorProject.query.order_by(MajorProject.id.desc()).limit(3).all()
    
    # En son eklenen tekil portfolyo öğelerini çekiyoruz (RECENT SKETCHES için)
    latest_sketches = Project.query.order_by(Project.id.desc()).limit(3).all()
    
    return render_template('index.html', latest_projects=latest_projects, latest_works=latest_sketches)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/portfolio')
def portfolio():
    projects = Project.query.order_by(Project.id.desc()).all()
    return render_template('portfolio.html', projects=projects)

# YENİ: Büyük Projeler Sayfası
@app.route('/projects')
def projects_page():
    major_projects = MajorProject.query.order_by(MajorProject.id.desc()).all()
    return render_template('projects.html', major_projects=major_projects)

# Tekil Eser Detay Sayfası
@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    return render_template('project_detail.html', project=project)

# YENİ: Büyük Proje Detay Sayfası (İçindeki tüm assetlerle beraber görünür)
@app.route('/major-project/<int:major_id>')
def major_project_detail(major_id):
    major = MajorProject.query.get_or_404(major_id)
    return render_template('major_project_detail.html', major=major)

ADMIN_PASSWORD = "aiden"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            return redirect(url_for('admin'))
        else:
            flash('Hatalı şifre!', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('home'))

# --- ADMIN PANELİ ---
@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        # 1. FORM: Tekil Portfolyo Öğesi Ekleme
        if form_type == 'portfolio_item':
            title = request.form.get('title')
            description = request.form.get('description')
            category = request.form.get('category')
            tags = request.form.get('tags')
            youtube_url = request.form.get('youtube_url')
            
            cover_file = request.files.get('image')
            glb_file = request.files.get('model_file')

            filename_cover = ""
            filename_glb = ""

            if cover_file and allowed_file(cover_file.filename):
                filename_cover = secure_filename(cover_file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                cover_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_cover))

            if glb_file and allowed_file(glb_file.filename):
                filename_glb = secure_filename(glb_file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                glb_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_glb))

            if filename_cover:
                new_item = Project(
                    title=title, description=description, category=category,
                    tags=tags, image=filename_cover,
                    model_file=filename_glb if filename_glb else None,
                    youtube_url=youtube_url if youtube_url else None
                )
                db.session.add(new_item)
                db.session.commit()
                flash('Portfolyo öğesi başarıyla eklendi!', 'success')

        # 2. FORM: Büyük Proje (Major Project) Oluşturma ve İçerik Seçme
        elif form_type == 'major_project':
            title = request.form.get('title')
            description = request.form.get('description')
            cover_file = request.files.get('image')
            selected_item_ids = request.form.getlist('selected_items') # Seçilen portfolyo öğeleri

            filename_cover = ""
            if cover_file and allowed_file(cover_file.filename):
                filename_cover = secure_filename(cover_file.filename)
                os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
                cover_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_cover))

            if filename_cover and title:
                new_major = MajorProject(
                    title=title,
                    description=description,
                    image=filename_cover
                )
                # Seçilen portfolyo öğelerini projeye bağlıyoruz
                for item_id in selected_item_ids:
                    item = Project.query.get(int(item_id))
                    if item:
                        new_major.items.append(item)

                db.session.add(new_major)
                db.session.commit()
                flash('Büyük Proje başarıyla oluşturuldu!', 'success')

        return redirect(url_for('admin'))

    projects = Project.query.order_by(Project.id.desc()).all()
    major_projects = MajorProject.query.order_by(MajorProject.id.desc()).all()
    return render_template('admin.html', projects=projects, major_projects=major_projects)

# --- DÜZENLEME ROTALARI ---
@app.route('/admin/edit/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    
    project = Project.query.get_or_404(project_id)
    
    if request.method == 'POST':
        project.title = request.form.get('title')
        project.description = request.form.get('description')
        project.category = request.form.get('category')
        project.tags = request.form.get('tags')
        project.youtube_url = request.form.get('youtube_url')
        
        cover_file = request.files.get('image')
        if cover_file and allowed_file(cover_file.filename):
            filename_cover = secure_filename(cover_file.filename)
            cover_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_cover))
            project.image = filename_cover
            
        glb_file = request.files.get('model_file')
        if glb_file and allowed_file(glb_file.filename):
            filename_glb = secure_filename(glb_file.filename)
            glb_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_glb))
            project.model_file = filename_glb

        db.session.commit()
        flash('Proje başarıyla güncellendi!', 'success')
        return redirect(url_for('admin'))
        
    return render_template('edit_project.html', project=project)

# --- SİLME ROTALARI ---
@app.route('/admin/delete/<int:project_id>')
def delete_project(project_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    project = Project.query.get_or_404(project_id)
    db.session.delete(project)
    db.session.commit()
    flash('Öğe silindi!', 'info')
    return redirect(url_for('admin'))

@app.route('/admin/delete-major/<int:major_id>')
def delete_major(major_id):
    if not session.get('admin_logged_in'):
        return redirect(url_for('login'))
    major = MajorProject.query.get_or_404(major_id)
    db.session.delete(major)
    db.session.commit()
    flash('Büyük proje silindi!', 'info')
    return redirect(url_for('admin'))

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)