
from flask import Flask, render_template, redirect, url_for, request, flash, Response  
from flask_sqlalchemy import SQLAlchemy  
from flask_bcrypt import Bcrypt 
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user 
import cv2  
import os 
import face_recognition  
import time

app = Flask(__name__)  # Flask uygulaması oluşturulur
app.config['SECRET_KEY'] = 'supersecretkey' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'  # Veritabanı bağlantısı yapılandırılır
db = SQLAlchemy(app)  # SQLAlchemy veritabanı bağlantısı oluşturulur
bcrypt = Bcrypt(app)  
login_manager = LoginManager(app)  # LoginManager kullanıcı yönetimini sağlar
login_manager.login_view = 'login'  # Kullanıcı giriş sayfası belirtilir 

@login_manager.user_loader  # Kullanıcıyı yüklemek için gerekli fonksiyon
def load_user(user_id):  # Kullanıcı ID'siyle kullanıcıyı veritabanından alır
    return User.query.get(int(user_id))  # Veritabanından kullanıcıyı getirir

@app.route('/')  # Anasayfa URL'si
def home():  # Anasayfa fonksiyonu
    return render_template('index.html')  # 'index.html' şablonunu yükler

@app.route('/admin')  # Admin sayfası URL'si
@login_required  # Kullanıcı giriş yapmış olmalı
def admin():  # Admin sayfası fonksiyonu
    if not current_user.is_admin:  # Eğer kullanıcı admin değilse
        flash('Yetkiniz yok!', 'danger')  # Yetki hatası mesajı gösterilir
        return redirect(url_for('home'))  # Anasayfaya yönlendirilir
    users = User.query.all()  # Veritabanındaki tüm kullanıcılar çekilir
    return render_template('admin.html', users=users)  # Admin şablonuna kullanıcılar gönderilir

@app.route('/logout')  # Çıkış yapma URL'si
@login_required  # Kullanıcı giriş yapmış olmalı
def logout():  # Çıkış fonksiyonu
    logout_user()  # Kullanıcıyı çıkartır
    flash('Çıkış yapıldı.', 'info')  # Çıkış mesajı gösterilir
    return redirect(url_for('home'))  # Anasayfaya yönlendirilir

#-------------------------------------------------------------------------------------------
'''
GET isteği: /register URL'sine gidildiğinde, kayıt formunu görüntüler.
POST isteği: Formu doldurup gönderdikten sonra, bilgiler POST isteğiyle sunucuya gönderilir ve burada veritabanına kaydedilir.'
'''
# KULLANICIYI VERİTABANINA KAYDETMEK İÇİN KULLANICIDAN VERİLERİ TOPLAYAN KOD
@app.route('/register', methods=['GET', 'POST'])  
def register():  # Kayıt fonksiyonu
    if request.method == 'POST':  # Eğer kullanıcıdan POST isteği gelirse
        username = request.form['username']  # Kullanıcı adı alınır
        tc = request.form['tc']  # TC Kimlik Numarası alınır
        ad = request.form['ad']  
        soyad = request.form['soyad']  
        cinsiyet = request.form['cinsiyet']  
        dogum = request.form['dogum'] 
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')  # Şifre hashlenir
        is_admin = request.form.get('is_admin') == 'on'  # Admin olup olmadığı kontrol edilir
        user = User(username=username, tc=tc, ad=ad, soyad=soyad, cinsiyet=cinsiyet, dogum=dogum, password=password, is_admin=is_admin)  # Yeni kullanıcı oluşturulur
        db.session.add(user)  # Veritabanına eklenir
        db.session.commit()  # Değişiklikler kaydedilir
        capture_face(username)  # Yüz verisi kaydedilir
        flash('Kullanıcı oluşturuldu ve yüz verisi kaydedildi!', 'success')  # Başarı mesajı gösterilir
        return redirect(url_for('login'))  # Giriş sayfasına yönlendirilir
    return render_template('register.html')  # Kayıt şablonu render edilir


# Kullanıcı bilgilerini veritabanına aktaran kod
class User(db.Model, UserMixin):  # User sınıfı, SQLAlchemy modelini ve UserMixin'i miras alır
    id = db.Column(db.Integer, primary_key=True)  
    username = db.Column(db.String(150), unique=True, nullable=False)  # Kullanıcı adı, benzersiz ve boş olamaz
    password = db.Column(db.String(150), nullable=False)  # Şifre, boş olamaz
    is_admin = db.Column(db.Boolean, default=False)  # Admin olup olmadığını belirten bir alan
    tc = db.Column(db.String(11), unique=True, nullable=False)  # TC Kimlik Numarası, benzersiz ve boş olamaz
    ad = db.Column(db.String(100), nullable=False)  
    soyad = db.Column(db.String(100), nullable=False) 
    cinsiyet = db.Column(db.String(10), nullable=False)  
    dogum = db.Column(db.String(10), nullable=False) 

#---------------------------------------------------------------------------------------

# KULLANICI GÖRÜNTÜLERİNİN ALINMASI
def gen_video_stream():  # Video akışını oluşturma fonksiyonu
    video_capture = cv2.VideoCapture(0)  # Kamera açılır
    while True:  # Sonsuz döngü
        ret, frame = video_capture.read()  # Kamera görüntüsü alınır
        if not ret:  # Eğer görüntü alınamazsa
            break  # Döngüden çıkılır
        _, jpeg = cv2.imencode('.jpg', frame)  # Görüntü JPEG formatına dönüştürülür
        frame = jpeg.tobytes()  # JPEG verisi byte formatına dönüştürülür
        yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')  # video akışının web sayfasında açılması için kullanılır.
    video_capture.release()  # Kamera kapatılır

@app.route('/video_feed')  # kamera görüntüsü alınırken açılan uzantı
def video_feed():  # Video akışı fonksiyonu
    return Response(gen_video_stream(), mimetype='multipart/x-mixed-replace; boundary=frame')  # Video akışı başlatılır

@app.route('/login', methods=['GET', 'POST'])  # Giriş sayfası URL'si
def login():  # Giriş fonksiyonu
    if request.method == 'POST':  # Eğer POST isteği gelirse
        username = request.form['username']  # Kullanıcı adı alınır
        password = request.form['password']  # Şifre alınır
        user = User.query.filter_by(username=username).first()  # Kullanıcı veritabanından alınır

        if user and bcrypt.check_password_hash(user.password, password) and verify_face(username):  # Eğer kullanıcı adı ve şifre  ve yüz doğrulaması doğruysa
            login_user(user)  # Kullanıcı giriş yapar
            if user.is_admin:  # Eğer kullanıcı adminse
                return redirect(url_for('admin'))  # Admin sayfasına yönlendirilir
            else:  # Eğer kullanıcı admin değilse
                return redirect(url_for('user_dashboard'))  # Kullanıcı paneline yönlendirilir
        else:  # Hatalı giriş yapılırsa
            flash('Kullanıcı adı veya şifre hatalı.', 'danger')  # Hata mesajı gösterilir
    return render_template('login.html')  # Giriş ekranı açılır

def capture_face(face_id):  # Yüz verisi kaydetme fonksiyonu
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')  # Yüz tespiti için Haar Cascade kullanılır
    dataset_path = 'datasets'  # Yüz verisi dosya yolu belirlenir
    if not os.path.exists(dataset_path):  # Eğer dosya yoksa
        os.makedirs(dataset_path)  # Yeni bir dosya oluşturulur. os klasörler arası gemeyi sağlıyor
    count = 0  # Yüz verisi sayacı
    video_capture = cv2.VideoCapture(0)  # Kamera açılır
    while count < 1:  # 1 yüz kaydedilene kadar döngü devam eder
        ret, frame = video_capture.read()  # Kamera görüntüsü alınır
        if not ret:  # Eğer görüntü alınamazsa
            break  # Döngüden çıkılır
        faces = face_cascade.detectMultiScale(frame, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))  # Yüzler tespit edilir
        for (x, y, w, h) in faces:  # Tespit edilen her yüz için
            face = frame[y:y+h, x:x+w]  # Yüz bölgesi alınır
            if face.shape[0] < 30 or face.shape[1] < 30:  # Eğer yüz çok küçükse
                continue  # Bu yüz atlanır
            face_resized = cv2.resize(face, (400, 400))  # Yüz boyutu yeniden ayarlanır
            cv2.imwrite(os.path.join(dataset_path, f"face.{face_id}.jpg"), face_resized)  # Yüz kaydedilir
            count += 1  # Sayaç artırılır
    video_capture.release()  # Kamera serbest bırakılır

def verify_face(face_id):  # Yüz doğrulama fonksiyonu
    known_face_encodings = []  # Tanınan yüzlerin kodlamalarını saklamak için liste
    dataset_path = "datasets"  # Yüz verisi dizini
    image_path = os.path.join(dataset_path, f"face.{face_id}.jpg")  # Yüz verisi dosya yolu
    if os.path.exists(image_path):  # Eğer yüz verisi dosyası varsa
        image = face_recognition.load_image_file(image_path)  # Yüz verisi yüklenir
        face_encodings = face_recognition.face_encodings(image)  # Yüz kodlamaları alınır
        if len(face_encodings) > 0:  # Eğer yüz kodlaması bulunursa
            known_face_encodings.append(face_encodings[0])  # Yüz kodlaması eklenir

    start_time = time.time()  # Zaman sınırını başlatır

    video_capture = cv2.VideoCapture(0)  # Kamera açılır
    while True:  # Sonsuz döngü
        ret, frame = video_capture.read()  # Kamera görüntüsü alınır
        if not ret:  # Eğer görüntü alınamazsa
            return False  # Yüz doğrulama başarısız

        face_encodings = face_recognition.face_encodings(frame)  # Görüntüdeki yüzler kodlanır

        # Yüz tanıma işlemi
        for face_encoding in face_encodings:  # Her bir yüz için
            matches = face_recognition.compare_faces(known_face_encodings, face_encoding)  # Yüz karşılaştırması yapılır
            if True in matches:  # Eğer eşleşme bulunursa
                video_capture.release()  # Kamera serbest bırakılır
                return True  # Yüz doğrulama başarılı

        # 3 saniye bekleme işlemi
        if time.time() - start_time > 3:  # 3 saniye geçtiyse
            flash('Yüz tanınamadı.', 'danger')  # Yüz tanınamadı mesajı gösterilir
            video_capture.release()  # Kamera kapatılır
            break  # Döngüden çıkılır

    return False  # Yüz doğrulama başarısız
#-----------------------------------------------------------------------------------------------------------------------
@app.route('/user_dashboard')  # Kullanıcının giriş yaptığı ana ekran
@login_required  # Kullanıcı giriş yapmış olmalı
def user_dashboard():  # Kullanıcı sayfası
    user = current_user  # Mevcut kullanıcı alınır
    return render_template('user_dashboard.html', user=user)  # Kullanıcı paneli açılır

# Yeni route'lar ekliyoruz:
@app.route('/academic_calendar')  # Akademik takvim sayfası URL'si
def academic_calendar():  # Akademik takvim fonksiyonu
    return render_template('academic_calendar.html')  # Akademik takvim şablonu açılır

@app.route('/advisor_info')  # Danışman bilgisi sayfası URL'si
def advisor_info():  
    return render_template('advisor_info.html') 

@app.route('/course_schedule')  # Ders programı sayfası URL'si
def course_schedule():  
    return render_template('course_schedule.html') 


@app.route('/transcript')  # Transkript sayfası URL'si
def transcript(): 
    return render_template('transcript.html')  

@app.route('/exam_results')  # Sınav sonuçları sayfası URL'si
def exam_results():  
    return render_template('exam_results.html')  

@app.route('/attendance_report')  # Devamsızlık raporu sayfası URL'si
def attendance_report():  
    return render_template('attendance_report.html') 
#----------------------------------------------------------------------------------------------------------------------------

if __name__ == '__main__': # Flask çalışır
    with app.app_context():  
        db.create_all()  
    app.run(debug=True)  