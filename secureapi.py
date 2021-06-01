import datetime
import json
import os
import re

import shutil
import filetype
from flask import Flask, render_template, request, Markup
from flask import jsonify
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_weasyprint import HTML

from ocr_core import ocr_core

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'

# Setup the Flask-JWT-Simple extension
app.config['JWT_SECRET_KEY'] = 'super_secret_for_generating_jwt'  # Change this!
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
app.config.from_object('config')

jwt = JWTManager(app)
db = SQLAlchemy(app)

USER = 'eyenuk'
PASSWD = 'eyenuk'

# ALLOWED_EXTENSIONS = set(['txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'])
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}


# noinspection PyRedeclaration
class User(UserMixin, db.Model):
    # Definition User model
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True)
    password = db.Column(db.String(128))

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)

    def __init__(self, username, password):
        self.username = username
        self.password = password


# noinspection PyRedeclaration
class ImageInfo(db.Model):
    __tablename__ = 'imageInfo'
    # id = db.Column(db.Integer)
    reference_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64))
    time_stamp = db.Column(db.String(64))
    folder_path = db.Column(db.String(128))
    dr_value_left = db.Column(db.Float)
    dr_value_right = db.Column(db.Float)
    dr_level = db.Column(db.String(32))
    summery_E = db.Column(db.String(256))
    summery_A = db.Column(db.String(256))
    fu_E = db.Column(db.String(256))
    fu_A = db.Column(db.String(256))

    def __init__(self, **kwargs):
        super(ImageInfo, self).__init__(**kwargs)

    def __init__(self, reference_id_1, username_1, time_stamp_1, folder_path_1, dr_value_left_1, dr_value_right_1,
                 dr_level_1, summery_e_1, summery_a_1, fu_e_1, fu_a_1):
        self.reference_id = reference_id_1
        self.username = username_1
        self.time_stamp = time_stamp_1
        self.folder_path = folder_path_1
        self.dr_value_left = dr_value_left_1
        self.dr_value_right = dr_value_right_1
        self.dr_level = dr_level_1
        self.summery_E = summery_e_1
        self.summery_A = summery_a_1
        self.fu_E = fu_e_1
        self.fu_A = fu_a_1


def encrypt(plaintext):
    return plaintext[::-1]


def decrypt(ciphertext):
    return ciphertext[::-1]


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Provide a method to create access tokens. The create_jwt()
# function is used to actually generate the token

def check_files_and_types(filepath_list_1):
    number_of_image_files = left_eye_files = right_eye_files = pdf_files = 0
    for filepath in filepath_list_1:
        kind = filetype.guess(filepath)
        if 'image/jpeg' in kind.mime or 'image/png' in kind.mime or 'application/pdf' in kind.mime:
            if 'image/' in kind.mime:
                number_of_image_files += 1
                if 'L_0' in os.path.basename(filepath):
                    left_eye_files += 1
                elif 'R_0' in os.path.basename(filepath):
                    right_eye_files += 1
            else:
                pdf_files += 1
        else:
            return False

    return number_of_image_files == 4 and left_eye_files == 2 and right_eye_files == 2 and pdf_files == 1


@app.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    params = request.get_json()
    username = params.get('username', None)
    password = params.get('password', None)

    if not username:
        return jsonify({"msg": "Missing username parameter"}), 400
    if not password:
        return jsonify({"msg": "Missing password parameter"}), 400

    if username != USER or password != PASSWD:
        return jsonify({"msg": "Bad username or password"}), 401

    # Identity can be any data that is json serializable
    access_token = {'jwt': create_access_token(identity=username), 'username': username}
    return jsonify(access_token), 200


# Protect a view with jwt_required, which requires a valid jwt
# to be present in the headers.

@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    # Access the identity of the current user with get_jwt_identity
    return jsonify({'user': get_jwt_identity()}), 200


# noinspection PyUnresolvedReferences
@app.route("/upload", methods=["POST"])
@jwt_required()
def upload():
    ref_no = request.form['ref_no']
    uploaded_files = request.files.getlist('file[]')
    username = request.form['username']
    print("username: " + username)
    filepath_list = []
    success = False
    files_created = False
    local_upload_folder = ''

    if len(uploaded_files) == 5 and ref_no is not None:
        local_upload_folder = os.path.join(app.config['UPLOAD_FOLDER'], ref_no)
        if not os.path.exists(local_upload_folder):
            os.makedirs(local_upload_folder)
            for file in uploaded_files:
                path = os.path.join(local_upload_folder, file.filename)
                file.save(path)
                filepath_list.append(path)

                files_created = True
                success = check_files_and_types(filepath_list)

    if success:
        pdf_filepath = ''
        for filepath in filepath_list:
            mime_type = filetype.guess(filepath)
            if 'application/pdf' in mime_type.mime:
                pdf_filepath = filepath
                print(pdf_filepath)
                break
        # --------------Translation of eyenuk pdf--------------#

        with open('bilingual_msg.json') as f:
            bilingual_msg = json.load(f)
        path_logo_right = os.path.abspath(os.getcwd()) + "/static/images/logo-full-text.png"
        path_logo_left = os.path.abspath(os.getcwd()) + "/static/images/logo.png"
        general_info = bilingual_msg["general_msg"][
            "english"]  # "As per International Diabetes Federation Eye Health:
        # A guide for health care professionals emphasize the importance of controlling blood glucose,
        # blood lipids and blood pressure as well the importance of regular eye exams regardless of
        # whether visual symptoms are present or absent"
        general_info_arabic = bilingual_msg["general_msg"][
            "arabic"]  # "وفقًا للاتحاد الدولي السكري لصحة
        # العين: يؤكد الدليل لأخصائي الرعاية الصحية على أهمية التحكم في نسبة السكري في
        # الدم ونسبه الدهون في الدم والتحكم في ضغط الدم بالإضافة إلى أهمية الفحص
        # الدوري للعين بغض النظر إذا كانت الأعراض البصرية موجودة أو غائبة"
        # Alert color for summary and followup
        color_alert = ""
        color_gen_info = ""
        print_pdf = True
        new_address = pdf_filepath
        epdf = '/' + new_address
        print('epdf: ' + epdf)
        print('new address: ' + new_address)
        # copyfile(new_address, new_address.replace('uploads/' + ref_no, 'static/eyenukreport'))
        extracted_text = ocr_core(epdf, ref_no)
        print('extracted text :' + str(extracted_text))
        p = '[\d]+[.,\d]+|[\d]*[.][\d]+|[\d]+'
        # I am using Regular Expression to find the level values i.e. 0.0, 1.0, 1.1...

        summary = extracted_text['val1']
        right_eye_result = extracted_text['val2']
        left_eye_result = extracted_text['val3']
        error_left_eye_result = extracted_text['errorL']
        error_right_eye_result = extracted_text['errorR']
        failure_result = extracted_text['failure']
        me_result = extracted_text['me']
        patient_id = extracted_text['patient_id']
        patient_name = extracted_text['patient_name']
        lvalue = rvalue = -1.0
        fu = fu_arabic = category = summary_arabic = ''
        print("Summary: " + summary, "Right Eye Result" + right_eye_result, "Left Eye Result" + left_eye_result,
              error_left_eye_result, error_right_eye_result, failure_result)

        if summary != "Ungradable due to technical error." and right_eye_result != "F" and left_eye_result != "F":
            print(extracted_text['val2'])
            if re.search(p, right_eye_result) is not None and error_right_eye_result != 'Ungradable for DR':

                for rightValue in re.finditer(p, right_eye_result):
                    print(rightValue[0])  # we got level value for the right eye
                    rvalue = rightValue[0]

            else:

                rvalue = float(0)
                # print("2222")
                # print(rvalue)

            if re.search(p, left_eye_result) is not None and error_left_eye_result != 'Ungradable for DR':
                for leftValue in re.finditer(p, left_eye_result):
                    # print(leftValue[0])  # we got level value for the left eye
                    lvalue = leftValue[0]
                    # print("3333")
                    # print(lvalue)
            else:
                lvalue = float(0)

            maximum = max(float(rvalue), float(lvalue))
            print(maximum)
            print("Right Eye Value: " + str(rvalue) + " , Left Eye Value: " + str(lvalue))

            if 0.0 <= float(maximum) <= 0.9:
                fu = Markup(bilingual_msg["negative"]["follow_up"]["common_eng"] + ':<br>' +
                            bilingual_msg["negative"]["follow_up"]["m_12"][
                                "english"])  # "Return for retinal imaging within 12 months"
                fu_arabic = Markup(bilingual_msg["negative"]["follow_up"]["common_arabic"] + ':<br>' +
                                   bilingual_msg["negative"]["follow_up"]["m_12"][
                                       "arabic"])  # "العودة لتصوير الشبكية بعد ١٢ شهرًا"
                category = "No DR"
                # color_alert="#ACEC89"
                # color_gen_info="#ACEC89"
            if 1.0 <= float(maximum) <= 1.9:
                # fu = "Return for retinal imaging within 9 months"
                # fu_arabic="العودة لتصوير الشبكية بعد ٩ شهرًا"
                fu = Markup(bilingual_msg["negative"]["follow_up"]["common_eng"] + ':<br>' +
                            bilingual_msg["negative"]["follow_up"]["m_09"]["english"])
                fu_arabic = Markup(bilingual_msg["negative"]["follow_up"]["common_arabic"] + ':<br>' +
                                   bilingual_msg["negative"]["follow_up"]["m_09"]["arabic"])
                category = "Mild DR"
                # color_alert="#FF9292"
                # color_gen_info="#FF9292"
            if 2.0 <= float(maximum) <= 2.5:
                # fu = "Return for retinal imaging within 6 months"
                # fu_arabic="العودة لتصوير الشبكية بعد ٦ شهرًا"
                fu = Markup(bilingual_msg["negative"]["follow_up"]["common_eng"] + ':<br>' +
                            bilingual_msg["negative"]["follow_up"]["m_06"]["english"])
                fu_arabic = Markup(bilingual_msg["negative"]["follow_up"]["common_arabic"] + ':<br>' +
                                   bilingual_msg["negative"]["follow_up"]["m_06"]["arabic"])
                category = "Moderate DR"
                # color_alert="#FF9292"
                # color_gen_info="#FF9292"
            if 2.6 <= float(maximum) <= 2.9:
                fu = Markup(bilingual_msg["negative"]["follow_up"]["common_eng"] + ':<br>' +
                            bilingual_msg["negative"]["follow_up"]["m_03"]["english"])
                fu_arabic = Markup(bilingual_msg["negative"]["follow_up"]["common_arabic"] + ':<br>' +
                                   bilingual_msg["negative"]["follow_up"]["m_03"]["arabic"])
                category = "Moderate/Severe DR"
                # color_alert="#ACEC89"
                # color_gen_info="#ACEC89"
            if 2.0 <= float(maximum) <= 2.9 and me_result == "T":
                # fu = "Urgent referral to an Eye care professional for evaluation of
                # vision threatening diabetic retinopathy per ICO guidelines for Diabetic Eye Care"
                # fu_arabic="إحالة عاجلة إلى طبيب العيون المختص لتقييم اعتلال الشبكية السكري الذي يهدد الرؤية وفقًا
                # لإرشادات المجلس الدولي لطب العيون للعناية بسكري العين"
                fu = bilingual_msg["positive"]["followup_eng"]
                fu_arabic = bilingual_msg["positive"]["followup_arabic"]
                category = "Moderate NPDR with DME"
                # color_alert="#FF9292"
                # color_gen_info="#FF9292"
            if 3.0 <= float(maximum) <= 3.9:
                # fu = "Urgent referral to an Eye care professional for
                # evaluation of vision threatening diabetic retinopathy per
                # ICO guidelines for Diabetic Eye Care"
                # fu_arabic="إحالة عاجلة إلى طبيب العيون المختص لتقييم
                # اعتلال الشبكية السكري الذي يهدد الرؤية وفقًا لإرشادات
                # المجلس الدولي لطب العيون للعناية بسكري العين"
                fu = bilingual_msg["positive"]["followup_eng"]
                fu_arabic = bilingual_msg["positive"]["followup_arabic"]
                category = "Severe DR"
                # color_alert="#FF9292"
                # color_gen_info="#FF9292"
            if 4.0 <= float(maximum):
                # fu = "Urgent referral to an Eye care professional for
                # evaluation of vision threatening diabetic retinopathy per ICO
                # guidelines for Diabetic Eye Care"
                # fu_arabic="إحالة عاجلة إلى طبيب العيون المختص لتقييم
                # اعتلال الشبكية السكري الذي يهدد الرؤية وفقًا لإرشادات المجلس
                # الدولي لطب العيون للعناية بسكري العين"
                fu = bilingual_msg["positive"]["followup_eng"]
                fu_arabic = bilingual_msg["positive"]["followup_arabic"]
                category = "proliferative DR"
                # color_alert="#FF9292"
                # color_gen_info="#FF9292"

            # print("extracted text : " + summary)

            if summary.find("Positive") > 0:
                print("in positive")
                summary_arabic = bilingual_msg["positive"][
                    "summary_arabic"]  # "إيجابي لتهديد الرؤيه بسبب إعتلال الشبكية السكري"
                summary = bilingual_msg["positive"][
                    "summary_eng"]  # "Positive for vision-threatening diabetic retinopathy"
                color_alert = "#FF9292"
                color_gen_info = "#FF9292"

            # Negative for vision-threatening diabetic retinopathy
            if summary.find("Negative") > 0:
                print("in negative")
                summary_arabic = bilingual_msg["negative"][
                    "summary_arabic"]  # "سلبي لتهديد الرؤيه بسبب إعتلال الشبكية السكري"
                summary = bilingual_msg["negative"][
                    "summary_eng"]  # "Negative for vision-threatening diabetic retinopathy"
                color_alert = "#ACEC89"
                color_gen_info = "#ACEC89"
            # goriginal_name = file.filename
            # guploaded_path = epdf
            timestmp = str(datetime.datetime.now()).replace(' ', '_')
            goutput = epdf  # epdf.replace('uploads/' + ref_no, 'static/translatedoutput')
            goutput_path = '/uploads/' + ref_no + '/' + timestmp + '_translated' + goutput.replace(
                '/uploads/' + ref_no + '/', '_')
            print("goutput_path: " + goutput_path)

            # update_log()

            # create simple-crypt output path of pad
            crypt_name = encrypt(goutput_path.replace('/uploads/' + ref_no + '/', ''))
            print('encrypted filename : ' + crypt_name)

            # Output PDF
            """ crypt_qr=file_name_encrypted.decode(),
            general_info=general_info,general_info_arabic=general_info_arabic,
            color_alert=color_alert,color_gen_info=color_gen_info,left_eye_result=left_eye_result,
            patientId=patient_id,patientName=patient_name,img_src=filepath.replace('pdf', 'png'),
            pdf=print_pdf,logoLeft=path_logo_left, logoRight=path_logo_right) """
            html = render_template('report.html',
                                   msg='Successfully processed',
                                   fu=fu, fuArabic=fu_arabic, category=category, leftEyeValue=lvalue,
                                   rightEyeValue=rvalue, me=me_result,
                                   extracted_text=extracted_text, summary=summary, summaryArabic=summary_arabic,
                                   rightEyeResult=right_eye_result,
                                   crypt_qr=crypt_name, general_info=general_info,
                                   general_info_arabic=general_info_arabic, colorAlert=color_alert,
                                   colorGenInfo=color_gen_info, leftEyeResult=left_eye_result, patientId=patient_id,
                                   patientName=patient_name, img_src=epdf.replace('pdf', 'png'),
                                   pdf=print_pdf, logoLeft=path_logo_left, logoRight=path_logo_right)
            HTML(string=html).write_pdf(os.getcwd() + goutput_path)

        else:
            color_alert = "#6aa5e5"
            color_gen_info = "#FF9292"
            summary = bilingual_msg["ungradable"][
                "summary_eng"]  # "Referral to an Eye care professional for evaluation due to ungradable images"
            summary_arabic = bilingual_msg["ungradable"][
                "summary_arabic"]  # "الاحالة الى طبيب العيون المختص بسبب عدم القدرة لتقيم الصور"
            fu = bilingual_msg["ungradable"]["followup_eng"]
            fu_arabic = bilingual_msg["ungradable"]["followup_arabic"]

            timestmp = str(datetime.datetime.now()).replace(' ', '_')
            goutput = epdf  # epdf.replace('uploads/' + ref_no, 'static/translatedoutput')
            goutput_path = '/uploads/' + ref_no + '/' + timestmp + '_translated' + goutput.replace(
                '/uploads/' + ref_no + '/', '')
            print("goutput_path: " + goutput_path)
            crypt_name = encrypt(goutput_path.replace('/uploads/' + ref_no + '/', ''))
            print('encrypted filename : ' + crypt_name)

            html = render_template('report.html',
                                   msg='Successfully processed',
                                   fu=fu, fuArabic=fu_arabic, summary=summary, summaryArabic=summary_arabic,
                                   crypt_qr=crypt_name, general_info=general_info,
                                   general_info_arabic=general_info_arabic, colorAlert=color_alert,
                                   colorGenInfo=color_gen_info, patientId=patient_id, patientName=patient_name,
                                   img_src=epdf.replace('pdf', 'png'), pdf=print_pdf,
                                   logoLeft=path_logo_left, logoRight=path_logo_right)
            # return render_pdf(HTML(string=html))

            HTML(string=html).write_pdf(os.getcwd() + goutput_path)

        try:
            database_entry = ImageInfo(ref_no, username, timestmp, local_upload_folder, lvalue, rvalue, category,
                                       summary,
                                       summary_arabic, fu, fu_arabic)
            db.session.add(database_entry)
            db.session.commit()
        except Exception as e:
            print(e)
            success = False

    if files_created and not success:
        shutil.rmtree(local_upload_folder)
        if os.path.exists(os.path.join('static', 'output', ref_no)):
            shutil.rmtree(os.path.join('static', 'output', ref_no))

    return jsonify({'success': success, 'ref_no': ref_no}), 200


if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
