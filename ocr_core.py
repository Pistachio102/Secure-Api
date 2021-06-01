import os

try:
    from PIL import Image
except ImportError:
    import Image
import pytesseract
import cv2
import csv
import pandas as pd
import pdf2image
import re

def parse_text(threshold_img):    
    # configuring parameters for tesseract
    tesseract_config = r'--oem 3 --psm 6'
    # now feeding image to tesseract
    details = pytesseract.image_to_data(threshold_img, output_type=pytesseract.Output.DICT,
                                        config=tesseract_config, lang='eng')
    return details


def format_text(details):
    """
    This function take one argument as
    input.This function will arrange
    resulted text into proper format.
    :param details: dictionary
    :return: list
    """
    parse_text = []
    word_list = []
    last_word = ''
    for word in details['text']:
        if word != '':
            word_list.append(word)
            last_word = word
        if (last_word != '' and word == '') or (word == details['text'][-1]):
            parse_text.append(word_list)
            word_list = []

    return parse_text


def write_text(formatted_text,file_path):
    """
    This function take one argument.
    it will write arranged text into
    a file.
    :param formatted_text: list
    :return: None
    """
    
    with open(file_path, 'w', newline="") as file:
        csv.writer(file, delimiter=" ").writerows(formatted_text)


def ocr_core(filename, ref_no):
    """
    This function will handle the core OCR processing of images.
    """
    os.makedirs('static/output/' + ref_no)
    filename = "." + filename
    filename1 = filename.replace('pdf', 'png').replace('uploads','/static/output')
    pages = pdf2image.convert_from_path(pdf_path=filename, dpi=200, size=(1654, 2340))
    for page_no, image in enumerate(pages):
        #image.save(f'result.png')
        image.save(filename1)
    image = cv2.imread('./' + filename1)

    parsed_data = parse_text(image)
    accuracy_threshold = 30
    #draw_boxes(image, parsed_data, accuracy_threshold)
    arranged_text = format_text(parsed_data)
    output_file=filename.replace('pdf', 'txt').replace('uploads','/static/output')
    write_text(arranged_text,output_file)
    df = pd.read_fwf(output_file, sep=" ", header=None)
    # The following is if there is a header
    errorL = '0'
    errorR = '0'
    a = '0'
    b = '0'
    c = '0'
    failure = False
    me="F"
    patient_id='not fetched'
    patient_name='not fetched'

    for line in range (len(df[0])):
        #print('line-idx '+ str(line) + ': ' + df[0][line])
        if df[0][line] == "Positive for vision-threatening diabetic retinopathy." or \
                df[0][line] == "Positive for referable diabetic retinopathy." or \
                df[0][line] == "Negative for vision-threatening diabetic retinopathy.":
            #index = 6
            meSrc = df[0][line + 1] + df[0][line + 2]
            pattern = ["macular", "DME"]
            for x in pattern:
                print('Looking for "%s" in "%s" -->' % (x, meSrc), end= ' ')
                if re.search(x, meSrc):
                    print ("Found DME or Macular Edema")
                    me = "T"
                else:
                    me = "F"

            print("Starting point is found on line " + str(line+1))
            failure = False
            a = df[0][line - 1] + ": " + df[0][line] + "\n"
            print(a)
            result = df[0][line + 1].split(":")
            result1 = result[1].split("Left Eye")
            b = result[0] + ": " + result1[0] + "\n"  # result[0] = Right Eye and result1[0]=result
            print(b)

            c = "Left Eye: " + result[2]
            print(c)
            if result[2] == 'Ungradable for DR':
                errorL = 'Ungradable for DR'
            if result1[0] == 'Ungradable for DR':
                errorR = 'Ungradable for DR'


    print(failure, a, b, c, errorL, errorR, me)
    failureString1 = "Ungradable due to technical error."
    failureString2 = "Ungradable (Reason: Images of sufficient quality not present for all required fields)."
    failureString3 = "Ungradable (Reason: Too few images for the specified protocol)."

    for line in range (len(df[0])):

        if df[0][line] == failureString1 or df[0][line] == failureString2 or df[0][line] == failureString3:
            failure = True
            a = "Ungradable due to technical error."
            b = "F"
            c = "F"
            me ="F"
            errorL = "T"
            errorR = "T"
            print("Error on line " + str(line))
            print(failure, a, b, c, errorL, errorR)


    chapters = {
        'val1': a,
        'val2': b,
        'val3': c,
        'me' : me,
        'errorL': errorL,
        'errorR': errorR,
        'failure': failure,
        'patient_id':getId(df),
        'patient_name':getName(df),
    }

    return chapters

def getName(et):
    name_line="not fetched"
    name="unknown"
    for line in et[0] :

        if line.find("Name:")>0:
            name_line=line

            array1 = name_line.split("Referring")            
            array2=array1[0].split(": ")            
            name=array2[1].strip()
            break
    return name

def getId(et):
    id_line="not fetched"
    id="unknown"
    for line in et[0] :

        if line.find("ID:")>0:
            id_line=line

            array1 = id_line.split("Referring")            
            array2=array1[0].split(": ")            
            id=array2[1].strip()
            break
    return id
""" def cleanSummary(source_summary):
    array1=source_summary.split(":")
    clean_summary=array1[len(array1)-1].strip()
    print (clean_summary)
    return clean_summary """