from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import csv
import io
import os

app = Flask(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, 'audits.db')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///{}'.format(db_path)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Lab(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    location = db.Column(db.String, nullable=True)
    audits = db.relationship('Audit', backref='lab', lazy=True)

class Audit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.Integer, db.ForeignKey('lab.id'), nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text, nullable=True)
    items = db.relationship('Item', backref='audit', lazy=True)

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    audit_id = db.Column(db.Integer, db.ForeignKey('audit.id'), nullable=False)
    code = db.Column(db.String, nullable=False, index=True)
    name = db.Column(db.String, nullable=True, index=True)
    system_qty = db.Column(db.Integer, nullable=True)
    physical_qty = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String, nullable=True, index=True)

# Create DB
with app.app_context():
    db.create_all()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/lab/<int:lab_id>')
def view_lab(lab_id):
    lab = Lab.query.get_or_404(lab_id)
    return render_template('lab.html', lab=lab)

# API: list labs
@app.route('/api/labs')
def api_labs():
    labs = Lab.query.order_by(Lab.name).all()
    return jsonify([{'id': l.id, 'name': l.name, 'location': l.location} for l in labs])

# API: search items with filters
@app.route('/api/search')
def api_search():
    q = request.args.get('q', type=str)
    lab_id = request.args.get('lab_id', type=int)
    status = request.args.get('status', type=str)
    date_from = request.args.get('date_from', type=str)
    date_to = request.args.get('date_to', type=str)

    query = Item.query.join(Audit)
    if lab_id:
        query = query.filter(Audit.lab_id == lab_id)
    if status:
        query = query.filter(Item.status.ilike(f'%{status}%'))
    if q:
        q_like = f'%{q}%'
        query = query.filter((Item.code.ilike(q_like)) | (Item.name.ilike(q_like)))
    if date_from:
        try:
            dtf = datetime.fromisoformat(date_from)
            query = query.filter(Audit.date >= dtf)
        except:
            pass
    if date_to:
        try:
            dtt = datetime.fromisoformat(date_to)
            query = query.filter(Audit.date <= dtt)
        except:
            pass

    items = query.order_by(Audit.date.desc()).limit(500).all()
    result = []
    for it in items:
        result.append({
            'id': it.id,
            'audit_id': it.audit_id,
            'lab_id': it.audit.lab_id,
            'lab_name': it.audit.lab.name,
            'audit_date': it.audit.date.isoformat(),
            'code': it.code,
            'name': it.name,
            'system_qty': it.system_qty,
            'physical_qty': it.physical_qty,
            'status': it.status
        })
    return jsonify(result)

# API: import CSV to create a new audit
@app.route('/api/import_csv', methods=['POST'])
def api_import_csv():
    lab_name = request.form.get('lab_name')
    notes = request.form.get('notes', '')
    date_str = request.form.get('date', '')
    file = request.files.get('file')
    if not lab_name or not file:
        return jsonify({'error': 'lab_name and file required'}), 400

    lab = Lab.query.filter_by(name=lab_name).first()
    if not lab:
        lab = Lab(name=lab_name)
        db.session.add(lab)
        db.session.commit()

    # parse date if provided
    audit_date = datetime.utcnow()
    if date_str:
        try:
            audit_date = datetime.fromisoformat(date_str)
        except:
            pass

    audit = Audit(lab_id=lab.id, date=audit_date, notes=notes)
    db.session.add(audit)
    db.session.flush()

    stream = io.StringIO(file.stream.read().decode('utf-8-sig'))
    reader = csv.DictReader(stream)
    for row in reader:
        code = row.get('code') or row.get('codigo') or ''
        name = row.get('name') or row.get('descricao') or ''
        try:
            system_qty = int(row.get('system_qty') or row.get('sistema') or 0)
        except:
            system_qty = None
        try:
            physical_qty = int(row.get('physical_qty') or row.get('fisico') or 0)
        except:
            physical_qty = None
        status = row.get('status') or row.get('situacao') or ''
        item = Item(audit_id=audit.id, code=code.strip(), name=name.strip(),
                    system_qty=system_qty, physical_qty=physical_qty, status=status.strip())
        db.session.add(item)

    db.session.commit()
    return jsonify({'ok': True, 'audit_id': audit.id})

if __name__ == '__main__':
    app.run(debug=True)
