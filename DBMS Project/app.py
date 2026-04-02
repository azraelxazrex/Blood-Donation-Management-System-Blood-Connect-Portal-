from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Database Models
# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    address = db.Column(db.Text)
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    zip_code = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    donor_profile = db.relationship('DonorProfile', backref='user', uselist=False, lazy=True)
    donations = db.relationship('DonationHistory', backref='donor', lazy=True)
    appointments = db.relationship('DonationAppointment', backref='donor', lazy=True)
    identity_proofs = db.relationship('IdentityProof', backref='user', lazy=True, foreign_keys='IdentityProof.user_id')

class DonorProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    blood_group = db.Column(db.String(5), nullable=False)
    weight = db.Column(db.Float)
    height = db.Column(db.Float)
    health_conditions = db.Column(db.Text)
    last_health_check = db.Column(db.Date)
    is_eligible = db.Column(db.Boolean, default=True)

class BloodInventory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    blood_group = db.Column(db.String(5), nullable=False)
    quantity_ml = db.Column(db.Integer, nullable=False)
    collected_date = db.Column(db.Date, nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    storage_location = db.Column(db.String(100))
    status = db.Column(db.String(20), default='available')
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DonationAppointment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    appointment_date = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='scheduled')
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class DonationHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    appointment_id = db.Column(db.Integer, db.ForeignKey('donation_appointment.id'))
    donation_date = db.Column(db.DateTime, nullable=False)
    blood_group = db.Column(db.String(5), nullable=False)
    quantity_ml = db.Column(db.Integer, nullable=False)
    hemoglobin_level = db.Column(db.Float)
    blood_pressure = db.Column(db.String(20))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class RecipientRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipient_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    patient_name = db.Column(db.String(200), nullable=False)
    required_blood_group = db.Column(db.String(5), nullable=False)
    quantity_ml = db.Column(db.Integer, nullable=False)
    urgency_level = db.Column(db.String(20), default='medium')
    hospital_name = db.Column(db.String(255))
    hospital_address = db.Column(db.Text)
    purpose = db.Column(db.Text)
    status = db.Column(db.String(20), default='pending')
    required_date = db.Column(db.Date)
    connected_donor_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    connected_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    connected_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# New Models for Identity Verification and Donor Alerts
class IdentityProof(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    document_type = db.Column(db.String(50), nullable=False)
    document_number = db.Column(db.String(100), nullable=False)
    document_image = db.Column(db.String(255))
    status = db.Column(db.String(20), default='pending')
    verified_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    verified_at = db.Column(db.DateTime)
    rejection_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship for the admin who verified
    verifier = db.relationship('User', foreign_keys=[verified_by], backref='verified_identities')

class DonorAlert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('recipient_request.id'), nullable=False)
    donor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    alert_type = db.Column(db.String(50), default='blood_request')
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='sent')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    request = db.relationship('RecipientRequest', backref='alerts')
    donor = db.relationship('User', foreign_keys=[donor_id], backref='alerts_received')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.context_processor
def inject_now():
    return {'now': datetime.utcnow()}

@app.context_processor
def utility_processor():
    return dict(zip=zip)

# Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin_dashboard'))
        else:
            return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email, is_active=True).first()
        
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user)
            next_page = request.args.get('next')
            if current_user.role == 'admin':
                return redirect(next_page) if next_page else redirect(url_for('admin_dashboard'))
            else:
                return redirect(next_page) if next_page else redirect(url_for('user_dashboard'))
        else:
            flash('Login failed. Check your email and password.', 'danger')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        phone = request.form.get('phone')
        blood_group = request.form.get('blood_group')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('register.html')
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        user = User(
            email=email,
            password_hash=hashed_password,
            role='donor',
            first_name=first_name,
            last_name=last_name,
            phone=phone
        )
        
        db.session.add(user)
        db.session.commit()
        
        donor_profile = DonorProfile(
            user_id=user.id,
            blood_group=blood_group
        )
        db.session.add(donor_profile)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Admin Routes
@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    
    total_donors = User.query.filter_by(role='donor', is_active=True).count()
    total_blood = db.session.query(db.func.sum(BloodInventory.quantity_ml)).filter_by(status='available').scalar() or 0
    pending_requests = RecipientRequest.query.filter_by(status='pending').count()
    scheduled_appointments = DonationAppointment.query.filter_by(status='scheduled').count()
    
    return render_template('admin/dashboard.html', 
                         total_donors=total_donors,
                         total_blood=total_blood,
                         pending_requests=pending_requests,
                         scheduled_appointments=scheduled_appointments)

@app.route('/admin/donors')
@login_required
def admin_donors():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    
    donors = User.query.filter_by(role='donor', is_active=True).all()
    return render_template('admin/donors.html', donors=donors)

@app.route('/admin/inventory')
@login_required
def admin_inventory():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    
    inventory = BloodInventory.query.filter_by(status='available').all()
    return render_template('admin/inventory.html', inventory=inventory)

@app.route('/admin/requests')
@login_required
def admin_requests():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    
    requests = RecipientRequest.query.all()
    return render_template('admin/requests.html', requests=requests)

@app.route('/admin/analytics')
@login_required
def admin_analytics():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    
    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    inventory_data = []
    for bg in blood_groups:
        total = db.session.query(db.func.sum(BloodInventory.quantity_ml)).filter_by(
            blood_group=bg, status='available'
        ).scalar() or 0
        inventory_data.append(total)
    
    blood_inventory_pairs = list(zip(blood_groups, inventory_data))
    
    return render_template('admin/analytics.html', 
                         blood_groups=blood_groups,
                         inventory_data=inventory_data,
                         blood_inventory_pairs=blood_inventory_pairs)

# NEW ROUTE - Identity Verification
@app.route('/admin/identity-verification')
@login_required
def admin_identity_verification():
    if current_user.role != 'admin':
        return redirect(url_for('user_dashboard'))
    
    pending_proofs = IdentityProof.query.filter_by(status='pending').all()
    return render_template('admin/identity-verification.html', pending_proofs=pending_proofs)

# User Routes
@app.route('/user/dashboard')
@login_required
def user_dashboard():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    donations = DonationHistory.query.filter_by(donor_id=current_user.id).count()
    appointments = DonationAppointment.query.filter_by(donor_id=current_user.id, status='scheduled').count()
    
    return render_template('user/dashboard.html', 
                         donations=donations,
                         appointments=appointments)

@app.route('/user/profile')
@login_required
def user_profile():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    return render_template('user/profile.html')

@app.route('/user/donations')
@login_required
def user_donations():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    donations = DonationHistory.query.filter_by(donor_id=current_user.id).all()
    return render_template('user/donations.html', donations=donations)

@app.route('/user/appointments')
@login_required
def user_appointments():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    appointments = DonationAppointment.query.filter_by(donor_id=current_user.id).all()
    return render_template('user/appointments.html', appointments=appointments)

@app.route('/user/request-blood')
@login_required
def user_request_blood():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    
    return render_template('user/request_blood.html')

# NEW ROUTE - User Identity Verification
@app.route('/user/identity')
@login_required
def user_identity():
    if current_user.role == 'admin':
        return redirect(url_for('admin_dashboard'))
    return render_template('user/identity.html')

# API Routes
@app.route('/api/schedule-appointment', methods=['POST'])
@login_required
def schedule_appointment():
    if current_user.role == 'admin':
        return jsonify({'error': 'Admins cannot schedule appointments'}), 403
    
    data = request.get_json()
    appointment = DonationAppointment(
        donor_id=current_user.id,
        appointment_date=datetime.strptime(data['date'], '%Y-%m-%dT%H:%M'),
        location=data['location'],
        notes=data.get('notes', '')
    )
    
    db.session.add(appointment)
    db.session.commit()
    
    return jsonify({'message': 'Appointment scheduled successfully'})

@app.route('/api/request-blood', methods=['POST'])
@login_required
def request_blood():
    if current_user.role == 'admin':
        return jsonify({'error': 'Admins cannot request blood'}), 403
    
    data = request.get_json()
    blood_request = RecipientRequest(
        recipient_id=current_user.id,
        patient_name=data['patient_name'],
        required_blood_group=data['blood_group'],
        quantity_ml=data['quantity'],
        urgency_level=data['urgency'],
        hospital_name=data.get('hospital'),
        purpose=data.get('purpose')
    )
    
    db.session.add(blood_request)
    db.session.commit()
    
    return jsonify({'message': 'Blood request submitted successfully'})

# New API Routes for Admin Functionality
@app.route('/api/admin/add-donor', methods=['POST'])
@login_required
def add_donor():
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'Email already registered'}), 400
    
    hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
    user = User(
        email=data['email'],
        password_hash=hashed_password,
        role='donor',
        first_name=data['first_name'],
        last_name=data['last_name'],
        phone=data.get('phone')
    )
    
    db.session.add(user)
    db.session.commit()
    
    donor_profile = DonorProfile(
        user_id=user.id,
        blood_group=data['blood_group']
    )
    db.session.add(donor_profile)
    db.session.commit()
    
    return jsonify({'message': 'Donor added successfully', 'donor_id': user.id})

@app.route('/api/admin/update-donor/<int:donor_id>', methods=['PUT'])
@login_required
def update_donor(donor_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    donor = User.query.filter_by(id=donor_id, role='donor').first()
    
    if not donor:
        return jsonify({'error': 'Donor not found'}), 404
    
    if 'first_name' in data:
        donor.first_name = data['first_name']
    if 'last_name' in data:
        donor.last_name = data['last_name']
    if 'email' in data:
        donor.email = data['email']
    if 'phone' in data:
        donor.phone = data['phone']
    
    if donor.donor_profile:
        if 'blood_group' in data:
            donor.donor_profile.blood_group = data['blood_group']
        if 'is_eligible' in data:
            donor.donor_profile.is_eligible = data['is_eligible']
    
    db.session.commit()
    
    return jsonify({'message': 'Donor updated successfully'})

@app.route('/api/admin/approve-request/<int:request_id>', methods=['POST'])
@login_required
def approve_request(request_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    blood_request = RecipientRequest.query.get(request_id)
    
    if not blood_request:
        return jsonify({'error': 'Request not found'}), 404
    
    blood_request.status = 'approved'
    db.session.commit()
    
    return jsonify({'message': 'Request approved successfully'})

@app.route('/api/admin/reject-request/<int:request_id>', methods=['POST'])
@login_required
def reject_request(request_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    blood_request = RecipientRequest.query.get(request_id)
    
    if not blood_request:
        return jsonify({'error': 'Request not found'}), 404
    
    blood_request.status = 'rejected'
    db.session.commit()
    
    return jsonify({'message': 'Request rejected successfully'})

@app.route('/api/admin/get-donor/<int:donor_id>', methods=['GET'])
@login_required
def get_donor(donor_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    donor = User.query.filter_by(id=donor_id, role='donor').first()
    
    if not donor:
        return jsonify({'error': 'Donor not found'}), 404
    
    donor_data = {
        'id': donor.id,
        'first_name': donor.first_name,
        'last_name': donor.last_name,
        'email': donor.email,
        'phone': donor.phone,
        'blood_group': donor.donor_profile.blood_group if donor.donor_profile else None,
        'is_eligible': donor.donor_profile.is_eligible if donor.donor_profile else True
    }
    
    return jsonify(donor_data)

# Identity Proof Routes
@app.route('/api/upload-identity', methods=['POST'])
@login_required
def upload_identity():
    if current_user.role == 'admin':
        return jsonify({'error': 'Admins cannot upload identity proofs'}), 403
    
    data = request.get_json()
    
    existing_proof = IdentityProof.query.filter_by(user_id=current_user.id).first()
    if existing_proof and existing_proof.status in ['pending', 'verified']:
        return jsonify({'error': 'You already have an identity proof submission'}), 400
    
    identity_proof = IdentityProof(
        user_id=current_user.id,
        document_type=data['document_type'],
        document_number=data['document_number'],
        document_image=data.get('document_image'),
        status='pending'
    )
    
    db.session.add(identity_proof)
    db.session.commit()
    
    return jsonify({'message': 'Identity proof uploaded successfully'})

@app.route('/api/admin/verify-identity/<int:proof_id>', methods=['POST'])
@login_required
def verify_identity(proof_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    identity_proof = IdentityProof.query.get(proof_id)
    
    if not identity_proof:
        return jsonify({'error': 'Identity proof not found'}), 404
    
    if data['action'] == 'verify':
        identity_proof.status = 'verified'
        identity_proof.verified_by = current_user.id
        identity_proof.verified_at = datetime.utcnow()
    else:
        identity_proof.status = 'rejected'
        identity_proof.rejection_reason = data.get('rejection_reason', 'No reason provided')
    
    db.session.commit()
    
    action = 'verified' if data['action'] == 'verify' else 'rejected'
    return jsonify({'message': f'Identity proof {action} successfully'})

# Donor Matching and Alert Routes
@app.route('/api/admin/find-matching-donors/<int:request_id>', methods=['GET'])
@login_required
def find_matching_donors(request_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    blood_request = RecipientRequest.query.get(request_id)
    if not blood_request:
        return jsonify({'error': 'Blood request not found'}), 404
    
    matching_donors = User.query.join(DonorProfile).filter(
        User.role == 'donor',
        User.is_active == True,
        DonorProfile.blood_group == blood_request.required_blood_group,
        DonorProfile.is_eligible == True
    ).all()
    
    donors_data = []
    for donor in matching_donors:
        identity_verified = IdentityProof.query.filter_by(
            user_id=donor.id, 
            status='verified'
        ).first() is not None
        
        donors_data.append({
            'id': donor.id,
            'name': f'{donor.first_name} {donor.last_name}',
            'email': donor.email,
            'phone': donor.phone,
            'blood_group': donor.donor_profile.blood_group,
            'identity_verified': identity_verified
        })
    
    return jsonify({
        'request_id': request_id,
        'required_blood_group': blood_request.required_blood_group,
        'matching_donors': donors_data
    })

@app.route('/api/admin/alert-donor', methods=['POST'])
@login_required
def alert_donor():
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    
    donor_alert = DonorAlert(
        request_id=data['request_id'],
        donor_id=data['donor_id'],
        message=data['message']
    )
    
    db.session.add(donor_alert)
    db.session.commit()
    
    return jsonify({'message': 'Alert sent to donor successfully'})

@app.route('/api/admin/connect-request/<int:request_id>', methods=['POST'])
@login_required
def connect_request(request_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    blood_request = RecipientRequest.query.get(request_id)
    
    if not blood_request:
        return jsonify({'error': 'Blood request not found'}), 404
    
    blood_request.status = 'connected'
    blood_request.connected_donor_id = data.get('donor_id')
    blood_request.connected_by = current_user.id
    blood_request.connected_at = datetime.utcnow()
    
    db.session.commit()
    
    return jsonify({'message': 'Request connected to donor successfully'})

# User Routes for Identity and Alerts
@app.route('/api/user/identity-status', methods=['GET'])
@login_required
def get_identity_status():
    if current_user.role == 'admin':
        return jsonify({'error': 'Admins cannot have identity proofs'}), 403
    
    identity_proof = IdentityProof.query.filter_by(user_id=current_user.id).first()
    
    if not identity_proof:
        return jsonify({'status': 'not_uploaded'})
    
    return jsonify({
        'status': identity_proof.status,
        'document_type': identity_proof.document_type,
        'document_number': identity_proof.document_number,
        'verified_at': identity_proof.verified_at.isoformat() if identity_proof.verified_at else None,
        'rejection_reason': identity_proof.rejection_reason
    })

@app.route('/api/user/alerts', methods=['GET'])
@login_required
def get_user_alerts():
    alerts = DonorAlert.query.filter_by(donor_id=current_user.id).order_by(DonorAlert.created_at.desc()).all()
    
    alerts_data = []
    for alert in alerts:
        request = RecipientRequest.query.get(alert.request_id)
        alerts_data.append({
            'id': alert.id,
            'message': alert.message,
            'status': alert.status,
            'blood_group': request.required_blood_group if request else 'Unknown',
            'created_at': alert.created_at.isoformat()
        })
    
    return jsonify({'alerts': alerts_data})
# User Profile and Health API Routes
@app.route('/api/user/update-profile', methods=['POST'])
@login_required
def update_user_profile():
    if current_user.role == 'admin':
        return jsonify({'error': 'Admins cannot update donor profiles'}), 403
    
    data = request.get_json()
    
    # Update user fields
    if 'first_name' in data:
        current_user.first_name = data['first_name']
    if 'last_name' in data:
        current_user.last_name = data['last_name']
    if 'phone' in data:
        current_user.phone = data['phone']
    if 'date_of_birth' in data:
        current_user.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
    if 'address' in data:
        current_user.address = data['address']
    
    db.session.commit()
    
    return jsonify({'message': 'Profile updated successfully'})

@app.route('/api/user/health-info', methods=['GET'])
@login_required
def get_health_info():
    if current_user.role == 'admin':
        return jsonify({'error': 'Admins cannot access health info'}), 403
    
    donor_profile = DonorProfile.query.filter_by(user_id=current_user.id).first()
    
    if not donor_profile:
        return jsonify({
            'weight': None,
            'height': None,
            'health_conditions': None,
            'last_health_check': None
        })
    
    return jsonify({
        'weight': donor_profile.weight,
        'height': donor_profile.height,
        'health_conditions': donor_profile.health_conditions,
        'last_health_check': donor_profile.last_health_check.isoformat() if donor_profile.last_health_check else None
    })

@app.route('/api/user/update-health', methods=['POST'])
@login_required
def update_health_info():
    if current_user.role == 'admin':
        return jsonify({'error': 'Admins cannot update health info'}), 403
    
    data = request.get_json()
    
    donor_profile = DonorProfile.query.filter_by(user_id=current_user.id).first()
    
    if not donor_profile:
        donor_profile = DonorProfile(user_id=current_user.id, blood_group='O+')
        db.session.add(donor_profile)
    
    # Update health fields
    if 'weight' in data:
        donor_profile.weight = float(data['weight']) if data['weight'] else None
    if 'height' in data:
        donor_profile.height = float(data['height']) if data['height'] else None
    if 'health_conditions' in data:
        donor_profile.health_conditions = data['health_conditions']
    if 'last_health_check' in data and data['last_health_check']:
        donor_profile.last_health_check = datetime.strptime(data['last_health_check'], '%Y-%m-%d').date()
    
    db.session.commit()
    
    return jsonify({'message': 'Health information updated successfully'})

# Admin Inventory API Routes
@app.route('/api/admin/add-blood-unit', methods=['POST'])
@login_required
def add_blood_unit():
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    data = request.get_json()
    
    blood_unit = BloodInventory(
        blood_group=data['blood_group'],
        quantity_ml=data['quantity_ml'],
        collected_date=datetime.strptime(data['collected_date'], '%Y-%m-%d').date(),
        expiry_date=datetime.strptime(data['expiry_date'], '%Y-%m-%d').date(),
        storage_location=data['storage_location'],
        donor_id=data.get('donor_id')
    )
    
    db.session.add(blood_unit)
    db.session.commit()
    
    return jsonify({'message': 'Blood unit added successfully', 'unit_id': blood_unit.id})

@app.route('/api/admin/get-blood-unit/<int:unit_id>', methods=['GET'])
@login_required
def get_blood_unit(unit_id):
    if current_user.role != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    blood_unit = BloodInventory.query.get(unit_id)
    
    if not blood_unit:
        return jsonify({'error': 'Blood unit not found'}), 404
    
    unit_data = {
        'id': blood_unit.id,
        'blood_group': blood_unit.blood_group,
        'quantity_ml': blood_unit.quantity_ml,
        'collected_date': blood_unit.collected_date.isoformat(),
        'expiry_date': blood_unit.expiry_date.isoformat(),
        'storage_location': blood_unit.storage_location,
        'donor_id': blood_unit.donor_id
    }
    
    return jsonify(unit_data)
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        admin = User.query.filter_by(email='admin@bloodbank.com').first()
        if not admin:
            hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
            admin = User(
                email='admin@bloodbank.com',
                password_hash=hashed_password,
                role='admin',
                first_name='System',
                last_name='Administrator'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin user created: admin@bloodbank.com / admin123")
    
    app.run(debug=True)