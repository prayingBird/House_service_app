from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime
from flask_migrate import Migrate
import click

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///household_services.db'
app.config['SECRET_KEY'] = 'super_secret_key'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# user ka class maine yaha pr create kra  , so  ki user ko table ban jaye aur fir usme se i can extract data or create fir or function ko banne me retrieve krunga
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(50), nullable=False)  
    status = db.Column(db.String(50), default='Inactive')
    address = db.Column(db.String(200), nullable=True)
    feedbacks = db.relationship('Feedback', backref='professional', lazy=True)

    # service request ke saath relationship define kra maine so i can get all service request of user.
    customer_requests = db.relationship(
        'ServiceRequest',
        backref='customer',
        lazy=True,
        foreign_keys='ServiceRequest.customer_id'
    )
    # professional ka list bnaya or same service request ka logic yaha bhi use ho rha hai bhai 
    professional_requests = db.relationship(
        'ServiceRequest',
        backref='professional',
        lazy=True,
        foreign_keys='ServiceRequest.professional_id'
    )

   # srvice classs se maine yaha relation define kiya hai fir or mai aage abhi class service functionality ke hisaaab se bnaunga 
    offered_services = db.relationship('Service', back_populates='provider', lazy=True)

  #   pending_services  bhi mai apne code me add krunga or pending service ki class banaa second step hai after creating service ka class
    pending_services_list = db.relationship('PendingService', back_populates='provider', lazy=True)

    def __repr__(self):
        return f"<User {self.username}, Role: {self.role}>"

#this is service class , i created from scratch by trial and error ,  or jaise jaise more data create hoga wasie i will edit here and add those coloms . 
class Service(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    time_required = db.Column(db.String(50), nullable=True)
    professional_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    requests = db.relationship('ServiceRequest', backref='service', lazy=True, cascade="all, delete-orphan")

   
    provider = db.relationship('User', back_populates='offered_services', lazy=True)

# same service class jaisa structure hai , isme bhi relation or zarurat ke hisaab se define krunga 
class PendingService(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    price = db.Column(db.Float, nullable=False)
    time_required = db.Column(db.String(50), nullable=True)
    professional_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), default='Pending')

    
    provider = db.relationship('User', back_populates='pending_services_list', lazy=True)

#feedback dena ka classs to basic hai , or core functionality me bhi aata hai so i will define it here
class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    professional_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_request_id = db.Column(db.Integer, db.ForeignKey('service_request.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # later defined Relationships
    service_request = db.relationship('ServiceRequest', backref='feedbacks', lazy=True)

# service request class bhi to define krni hai as per the requirement , and hope fulls while building it from scracth i will add more coloms jaisa need hoga.
class ServiceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)  
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  
    professional_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) 
    status = db.Column(db.String(50), default='Requested')
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    completion_date = db.Column(db.DateTime, nullable=True)
    remarks = db.Column(db.Text, nullable=True)
    completed_by = db.Column(db.String(100), nullable=True) 

# ab from down here , route define krna start hoga 
# there will be i guss basic of 12 routes but if i need to add more and add more relationship in the routes to make the functionality work to dekhenge or 
def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session or session.get('role') != role:
                flash("Access denied.", "danger")
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
# ye home hai , index page dega or user ko register auur login krne ka 
@app.route('/')
def home():
    return render_template('index.html')

#ab home pr gye to therr are 2 option login and register , to lets define register route. 
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        address = request.form['address']
        role = request.form['role']
        #basic upar tak hogya hai now neche ab user ka model use karna hai
        
        service_type = request.form.get('service_type', None)
        description = request.form.get('description', None)
        price = request.form.get('price', None)  

        # ab criteria and check krna define hai neeche me , jaise ki email validation , password validation ,
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email is already registered. Please use a different email.", "danger")
            return redirect(url_for('register'))

        # ab role ka agar error aata hai to ye condition register me check krega 
        if role not in ['customer', 'professional']:
            flash("Invalid role.", "danger")
            return redirect(url_for('register'))

        # ab password validation check krega 
        password_hash = generate_password_hash(password)        
        # ab status check hoga yaha pr , or role check hoga yaha pr 
        status = 'Pending' if role == 'professional' else 'Active'

        
        new_user = User(username=username, email=email,
                        password_hash=password_hash,
                        role=role,
                        status=status,
                        address=address)

        db.session.add(new_user)
        db.session.commit()
        # ab role proffesional hai to addition requirement ayenge  ,jaise service kaisa dega or service ka price kya hoga , or service ka time required kya hoga
        # or description bhi , hope full itna he add krna hoga.
        if role == 'professional':
            if not service_type or not description or not price:
                flash("Service type, description, and price are required for professionals.", "danger")
                return redirect(url_for('register'))

            # ab price validation check krtey hai 
            try:
                price = float(price)
                if price <= 0:
                    flash("Price must be a positive number.", "danger")
                    return redirect(url_for('register'))
            #invalid price check krenge . jaise hoga price string me aata hai to error aayega
            except ValueError:
                flash("Invalid price format. Please enter a valid number.", "danger")
                return redirect(url_for('register'))
            
            new_service = PendingService(
                name=service_type,
                description=description,
                price=price,  
                time_required='',  
                professional_id=new_user.id
            )
            db.session.add(new_service)
            db.session.commit()
            flash("Registration successful. Please wait for admin approval.", "success")
        else:
            flash("Registration successful. Please login.", "success")
        
        return redirect(url_for('login'))

    return render_template('register.html')
# ajao login route define krne me 
#login route me hume check krna hai ki user admin hai ya professional hai , ya custoomer hai , fir uske basis pe we will redirect them to different page , jo bhi hoga jiase customer_dashboard
#or proffeional _dashboard # or admin_dashboard

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # hardcore krtey hai admin ka email and password so it will be more secure and protected 
        if email == 'admin@example.com' and password == 'admin123':
            session['user_id'] = 1  # Admin user_id
            session['role'] = 'admin'
            return redirect(url_for('admin_dashboard'))

        user = User.query.filter_by(email=email).first()
        #ab conditon lgate hai , block ka ya unregister ka user hai ya pending kaaa. 
        if user:
            if user.status == 'Blocked':
                flash("Your account has been blocked. Please contact support.", "danger")
                return redirect(url_for('blocked'))

            if user.status == 'Pending':
                flash("Your account is pending approval. Please wait for admin approval.", "warning")
                return redirect(url_for('login'))

            if check_password_hash(user.password_hash, password):
                session['user_id'] = user.id
                session['role'] = user.role

                if user.role == 'admin':
                    return redirect(url_for('admin_dashboard'))
                elif user.role == 'customer':
                    return redirect(url_for('customer_dashboard'))
                elif user.role == 'professional':
                    return redirect(url_for('professional_dashboard'))

        flash("Invalid credentials.", "danger")
        return redirect(url_for('login'))

    return render_template('login.html')

#login ka route zada simple nhi tha lekin hopefull logout simple hoga. 
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for('login'))
# block to kaafi simple hai 
@app.route('/blocked')
def blocked():
    return render_template('blocked.html')

#customer ka dashboard , to follow the guideline and requirment us hissab se logic built krtey hai , tough hai bhai 
@app.route('/customer/dashboard')
@role_required('customer')
def customer_dashboard():
    # ye service jitne available hai vo customer ko show krenga uske dash board pr 
    services = Service.query.all()
    
    # ye vo jo customer request krga usko proffesional dashboard me show jayega 
    completed_requests = ServiceRequest.query.filter_by(customer_id=session['user_id'], status='Completed').all()
    
    # there are three status of request requested ongoing and declined
    for request in completed_requests:
        request.has_feedback = Feedback.query.filter_by(service_request_id=request.id).first() is not None

    
    active_requests = ServiceRequest.query.filter(
        ServiceRequest.customer_id == session['user_id'],
        ServiceRequest.status.in_(['Requested', 'Ongoing', 'Declined'])
    ).all()

    
    requested_service_ids = [request.service_id for request in active_requests]
    
    # yaha render krenge logic defineee krne ke baaad chezo ko , logic was tough to define
    return render_template('customer_dashboard.html', services=services,
                           completed_requests=completed_requests,
                           active_requests=active_requests,
                           requested_service_ids=requested_service_ids)

# chlo lets work on proffesional dashbaord , logic will be tough here god give me strenght to define this logic with trial and very less error ,

@app.route('/professional/dashboard')
@role_required('professional')
def professional_dashboard():
    # ye professional ko uske assign ho ga user_id ke hisab se 
    all_requests = ServiceRequest.query.filter_by(professional_id=session['user_id']).all()
    
    
    completed_requests = [request for request in all_requests if request.status == 'Completed']
    new_requests = [request for request in all_requests if request.status != 'Completed']
    # template render krenge , logic define krne ke baad , lets see ki more logic define krna hoga ya nhi , but basic to define krhe di hai maine  
    return render_template('professional_dashboard.html', 
                           completed_requests=completed_requests, 
                           new_requests=new_requests)
# proffesiona ko decline krne ka option dena , logic yaha hai 
@app.route('/service/decline/<int:request_id>', methods=['POST'])
@role_required('professional')
def decline_service_request(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)
    
    # ye ensure krenge ki sahi professional ko assing ho user_id ko use krke. 
    if service_request.professional_id != session['user_id']:
        flash("You are not authorized to decline this service request.", "danger")
        return redirect(url_for('professional_dashboard'))
    # agar service requested hai to decline ka option bhi hoga , or accept ka bhi so decline ka logic yaha hai 
    if service_request.status == 'Requested':
        service_request.status = 'Declined'
        db.session.commit()
        flash("Service request declined successfully.", "success")
    # service process me agye to decline ko unavailable krdenge
    else:
        flash("Service request cannot be declined.", "danger")
    
    return redirect(url_for('professional_dashboard'))

# phle service professional ka service create krna check krte hai , this is addition functionality if required i will use it for my real world work but this is redundent as of now 
@app.route('/professional/service/create', methods=['GET', 'POST'])
@role_required('professional')
def create_professional_service():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        time_required = request.form['time_required']

       
        try:
            price = float(price)
            if price <= 0:
                flash("Price must be a positive number.", "danger")
                return redirect(url_for('create_professional_service'))
        except ValueError:
            flash("Invalid price format. Please enter a valid number.", "danger")
            return redirect(url_for('create_professional_service'))

       
        new_service = PendingService(
            name=name,
            description=description,
            price=price,
            time_required=time_required,
            professional_id=session['user_id']
        )

        try:
            db.session.add(new_service)
            db.session.commit()
            flash("Service created and pending approval.", "success")
            return redirect(url_for('professional_dashboard'))
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while creating the service: {str(e)}", "danger")

    return render_template('create_professional_service.html')

# service accept krne ke baad ka logic define krteyt hai
@app.route('/service/update/<int:request_id>', methods=['POST'])
@role_required('professional')
def update_service_request(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)
    try:
        if service_request.status == 'Requested':
            service_request.status = 'Ongoing'
            flash("Service request accepted and marked as ongoing.", "success")
        elif service_request.status == 'Ongoing':
            service_request.status = 'Completed'
            service_request.completion_date = datetime.datetime.now()
            flash("Service request marked as completed.", "success")
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while updating the service request: {str(e)}", "danger")
    return redirect(url_for('professional_dashboard'))
# lets move on to admin bhai , lets define admin dashboard and connect the functionality with other dashboard later .
@app.route('/admin/service/create', methods=['GET', 'POST'])
@role_required('admin')
# authority denge service create krne ki 
def create_service():
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        time_required = request.form['time_required']
        professional_id = request.form['professional_id']

        #price ka error check 
        try:
            price = float(price)
            if price <= 0:
                flash("Price must be a positive number.", "danger")
                return redirect(url_for('create_service'))
        except ValueError:
            flash("Invalid price format. Please enter a valid number.", "danger")
            return redirect(url_for('create_service'))

        #new service admin bna sakta hai as per functionality 
        new_service = Service(
            name=name,
            description=description,
            price=price,
            time_required=time_required,
            professional_id=professional_id
        )
        #service ko add krenge database me  
        try:
            db.session.add(new_service)
            db.session.commit()
            flash("Service created successfully.", "success")
            return redirect(url_for('admin_dashboard'))
        # just in case ek error define krdete hai. hehe smart work bhai 
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred while creating the service: {str(e)}", "danger")
    #professiona show hoga while creating the service  , admin jisko chahhe assing kre 
    professionals = User.query.filter_by(role='professional').all()
    return render_template('create_service.html', professionals=professionals)

# ab service banke database me toh admin dashboard me show krna hai
@app.route('/service/request/<int:service_id>', methods=['POST'])
@role_required('customer')
def create_service_request(service_id):
    service = Service.query.get_or_404(service_id)
    new_request = ServiceRequest(
        service_id=service.id,
        customer_id=session['user_id'],
        professional_id=service.professional_id,  
        status='Requested'
    )
    #feeding the data in the database
    db.session.add(new_request)
    db.session.commit()
    flash("Service request created successfully.", "success")
    return redirect(url_for('customer_dashboard'))
# ab customer kasie apne dashboard se feedback dega we need to check code that , 
@app.route('/service/feedback/<int:request_id>', methods=['POST'])
@role_required('customer')
def submit_feedback(request_id):
    service_request = ServiceRequest.query.get_or_404(request_id)
    # feedback option tabhi available hoga jab service complete hojayegai
    
    if service_request.status != 'Completed':
        flash("Feedback can only be submitted for completed services.", "danger")
        return redirect(url_for('customer_dashboard'))
    # data feed back ka jo push back kregne vo show present hona chaihiye if empty it will give a warning 
    feedback_content = request.form.get('feedback')
    if not feedback_content:
        flash("Feedback content cannot be empty.", "danger")
        return redirect(url_for('customer_dashboard'))
    # feedback will go to professional id dashboard
    feedback = Feedback(
        professional_id=service_request.professional_id,
        service_request_id=service_request.id,
        content=feedback_content
    )
    # comitting the data in the database
    try:
        db.session.add(feedback)
        db.session.commit()
        flash("Feedback submitted successfully.", "success")
    # exception define krke
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while submitting feedback: {str(e)}", "danger")

    return redirect(url_for('customer_dashboard'))

# ab admin dashboard me professional ne jo service request register ke waqt bheji hai uska approval or decline fucntion bhai 
@app.route('/admin/dashboard')
@role_required('admin')
def admin_dashboard():
    services = Service.query.all()  
    pending_services = PendingService.query.all()  
    professionals = User.query.filter_by(role='professional').all()
    customers = User.query.filter_by(role='customer').all()
    feedbacks = Feedback.query.all()

   
    pending_professionals = User.query.filter_by(role='professional', status='Pending').all()

    return render_template('admin_dashboard.html', services=services,
                           pending_services=pending_services,
                           professionals=professionals, customers=customers,
                           feedbacks=feedbacks, pending_professionals=pending_professionals)

# manage service in admin_dashboard me edit krne ka option which makes the admin update the service also 
@app.route('/admin/service/edit/<int:service_id>', methods=['GET', 'POST'])
@role_required('admin')
def edit_service(service_id):
    service = Service.query.get_or_404(service_id)
    if request.method == 'POST':
        service.name = request.form['name']
        service.description = request.form['description']
        service.price = request.form['price']
        service.time_required = request.form['time_required']
        try:
            db.session.commit()
            flash("Service updated successfully.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"An error occurred: {str(e)}", "danger")
        return redirect(url_for('admin_dashboard'))
    return render_template('edit_service.html', service=service)

# admin_dashobrd me customer ko manage krna 
@app.route('/admin/manage/customers')
@role_required('admin')
def admin_manage_customers():
    customers = User.query.filter_by(role='customer').all()
    return render_template('admin_manage_customers.html', customers=customers)
# admin dashboard me professional ko manage krna
@app.route('/admin/manage/professionals')
@role_required('admin')
def admin_manage_professionals():
    professionals = User.query.filter_by(role='professional').all()
    return render_template('admin_manage_professionals.html', professionals=professionals)
# # admin me delete krna 
# existing servie 
# and fir sql database se delete krna ka function 
@app.route('/admin/service/delete/<int:service_id>', methods=['POST'])
@role_required('admin')
def delete_service(service_id):
    service = Service.query.get_or_404(service_id)
    try:
        # Delete all related service requests and their feedbacks
        for request in service.requests:
            Feedback.query.filter_by(service_request_id=request.id).delete()
            db.session.delete(request)

        db.session.delete(service)
        db.session.commit()
        flash("Service and all related requests and feedbacks deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while deleting the service: {str(e)}", "danger")
    return redirect(url_for('admin_dashboard'))

# admin block and unblock kr paye user ko vo function yaha define hai , 
@app.route('/admin/block_user/<int:user_id>', methods=['POST'])
@role_required('admin')
def admin_block_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        user.status = 'Blocked'
        db.session.commit()
        flash(f"User {user.username} has been blocked.", "success")
        # adding exception is a good thing just in case kuch masla hoajye 
    except Exception as e:
        db.session.rollback()



        flash(f"An error occurred while blocking the user: {str(e)}", "danger")
    return redirect(request.referrer or url_for('admin_manage_customers'))





# admin ko unblock krne ki shakti dena , XD
@app.route('/admin/unblock_user/<int:user_id>', methods=['POST'])
@role_required('admin')
def admin_unblock_user(user_id):
    user = User.query.get_or_404(user_id)
    try:
        user.status = 'Active'  
        db.session.commit()
        flash(f"User {user.username} has been unblocked.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while unblocking the user: {str(e)}", "danger")
    return redirect(request.referrer or url_for('admin_manage_customers'))



# admin ko professional ko he delete krne ke shakti dena if he is not vibing with him 
@app.route('/admin/professional/delete/<int:professional_id>', methods=['POST'])
@role_required('admin')
def delete_professional(professional_id):
    professional = User.query.get_or_404(professional_id)
    try:
        db.session.delete(professional)
        db.session.commit()
        flash("Professional deleted successfully.", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while deleting the professional: {str(e)}", "danger")
    return redirect(url_for('admin_dashboard'))




#admin ko pending service ko delete krne ya later approve krne ke shakti pradan krna 
@app.route('/admin/service/decline/<int:pending_service_id>', methods=['POST'])
@role_required('admin')
def delete_pending_service(pending_service_id):
    pending_service = PendingService.query.get_or_404(pending_service_id)
    professional = pending_service.provider  

    try:
       
        db.session.delete(pending_service)

        
        if not professional.pending_services_list:
            professional.status = 'Declined'  

        db.session.commit()
        flash("Pending service declined successfully.", "success")
    except Exception as e:
        # exception dena zruri hai , error aata hai to smjh aata hai , exceptions are my best friend
        db.session.rollback()
        flash(f"An error occurred while declining the service: {str(e)}", "danger")
    return redirect(url_for('admin_dashboard'))


# admin ko professional ko job dene ki shakti dena , by approving them , dam admin ke paas bht authority hai 
@app.route('/admin/service/approve/<int:pending_service_id>', methods=['POST'])
@role_required('admin')
def approve_service(pending_service_id):
    pending_service = PendingService.query.get_or_404(pending_service_id)
    professional = pending_service.provider  

    service = Service(
        name=pending_service.name,
        description=pending_service.description,
        price=pending_service.price,
        time_required=pending_service.time_required,
        professional_id=pending_service.professional_id
    )
    try:
       
        db.session.delete(pending_service)
        db.session.add(service)

        
        if professional.status == 'Pending':
            professional.status = 'Active'

        db.session.commit()
        flash("Service approved and added. Professional is now active.", "success")

        # exception to bnta hai 
    except Exception as e:
        db.session.rollback()
        flash(f"An error occurred while approving the service: {str(e)}", "danger")
    return redirect(url_for('admin_dashboard'))

# sql deta me agar redundent data ya faltu user ajatey hai to unko delete krne ke liye pura database ko gayab krna 
@app.cli.command("reset-db")
@click.confirmation_option(prompt='Are you sure you want to reset the database? This will delete all data.')
def reset_db():
    """Reset the database."""
    click.echo("Dropping all tables...")
    db.drop_all()
    click.echo("Creating all tables...")
    db.create_all()
    click.echo("Database has been reset.")

    # and admin generate krna , warna koi login he nhi kr payega sir customer apna account bana payengi lol ..
    admin_email = 'admin@example.com'
    admin_password = 'admin123'
    existing_admin = User.query.filter_by(email=admin_email).first()
    if not existing_admin:
        admin_user = User(
            username='admin',
            email=admin_email,
            password_hash=generate_password_hash(admin_password),
            role='admin',
            status='Active'
        )
        db.session.add(admin_user)
        db.session.commit()
        click.echo("Admin user created.")

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        admin_email = 'admin@example.com'
        admin_password = 'admin123'
        existing_admin = User.query.filter_by(email=admin_email).first()
        if not existing_admin:
            admin_user = User(
                username='admin',
                email=admin_email,
                password_hash=generate_password_hash(admin_password),
                role='admin',
                status='Active'
            )
            db.session.add(admin_user)
            db.session.commit()

    app.run(debug=True)




# doneeeeeeeeeeeeeeeeeeeeeeeee 