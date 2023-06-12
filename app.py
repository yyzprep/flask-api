from flask import Flask, request, make_response
import pymysql
from flask_cors import CORS, cross_origin
import json
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io, qrcode
import urllib
from PyPDF2 import PdfFileWriter, PdfFileReader
import requests
import code128
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from datetime import datetime
import pandas as pd

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'


def generate_serial_number():
    last_serial_number = runQuery_uplink('SELECT MAX(PKEY) AS PKEY from QR_DB')[0]['PKEY']
    new_serial_number = last_serial_number + 1
    return new_serial_number



@app.route('/generate_qr_label', methods=['GET', 'POST'])
@cross_origin()
def generate_qr_label():
    data = request.get_json()
    #print(data)
    text, id, titles, created, employee = data['text'], data['id'], data['titles'], data['created'], data['employee']
    condition = 'New'

    # Create a QR code instance
    qr = qrcode.QRCode()#version=1, box_size=10, border=4)
    # Add the data to the QR code
    print(created)

    CREATED_AT = datetime.strptime(created, '%Y-%m-%d %H:%M:%S.%f')
    PKEY = generate_serial_number()#str(id) + "_" + str(datetime.datetime.now())
    DATA = text
    qr.add_data(PKEY)
    SCALE = 2

    label_width = 2.25  * SCALE
    label_height = 1.25 * SCALE
    # Make the QR code
    # qr.make(fit=True)
    # # Create an image from the QR code
    # img = qr.make_image(fill_color="black", back_color="white")

    ppi = 72
    # # Resize the image to the desired height and DPI
    # height_inches = 0.75
    # height_px = int(height_inches * ppi) # 1 inch at 203dpi
    # img_resized = img.resize((height_px, height_px), resample=Image.BOX)

    # Create a new image with the desired label size
    label_size = (int(label_width * ppi), int(label_height * ppi)) # convert inches to pixels at 203dpi
    label_img = Image.new('RGB', label_size, color='white')

    barcode_url = f"http://bwipjs-api.metafloor.com/?bcid=code128&text={PKEY}&height=5&rotate=R"
    response = requests.get(barcode_url)
    barcode_image = Image.open(io.BytesIO(response.content)).convert('RGBA')
    height_inches = 1 * SCALE
    height_px = int(height_inches * ppi) # 1 inch at 203dpi
    barcode_image_resized = barcode_image.resize((height_px, height_px), resample=Image.BOX)

    # Paste the QR code onto the center of the label image
    x = int((label_width * ppi - height_px) / 2) - 70
    y = int((label_height * ppi - height_px) / 2)
    label_img.paste(barcode_image_resized, (x, y), mask=barcode_image_resized)

    # Add the id variable as text on the right side of the QR code image
    draw = ImageDraw.Draw(label_img)
    font = ImageFont.truetype('hel.ttf', 12 * SCALE, encoding="unic")
    font_small = ImageFont.truetype('hel.ttf', 10 * SCALE, encoding="unic")
    id_width, id_height = draw.textsize(f"{id} {remove_vowels(employee)}", font=font)
    title_width, title_height = draw.textsize(f"{titles}", font=font_small)

    # Draw ID text
    draw.text((x + height_px + 7 * SCALE, y + int((height_px - id_height - title_height) / 2)), f"{id} {remove_vowels(employee)}", font=font, fill="black")

    # Draw title text
    draw.text((x + height_px + 7 * SCALE, y + int((height_px - id_height - title_height) / 2) + id_height), f"{titles}", font=font_small, fill="black")

    # font = ImageFont.truetype('hel.ttf', 16, encoding="unic")
    # font_small = ImageFont.truetype('hel.ttf', 12, encoding="unic")
    # text_width, text_height = draw.textsize(f"YYZ\n{id}\n{titles}", font=font_small)
    # draw.text((x + height_px + 7, y + int((height_px - text_height) / 2)), f"{id}\n{titles}", font=font_small, fill="black")

    # Convert the label image to bytes
    with io.BytesIO() as output:
        label_img.save(output, format='PNG')
        contents = output.getvalue()
        label_img.seek(0)
        # Create a PDF document and add the QR code image to it
        pdf_buffer = io.BytesIO()
        c = canvas.Canvas(pdf_buffer, pagesize=label_size)
        c.drawImage(ImageReader(label_img), 0, 0)
        c.showPage()
        c.save()

    response = make_response(pdf_buffer.getvalue())

    # Set the content type of the response to 'application/pdf'
    response.headers.set('Content-Type', 'application/pdf')
    return response

def remove_vowels(employee):
    if len(employee) <= 2:
        # If the name is two characters or less, there are no vowels to remove
        return employee
    else:
        # Remove vowels from the name
        new_name = employee[0]  # keep the first character
        for i in range(1, len(employee) - 1):
            if employee[i] not in 'aeiouAEIOU':
                new_name += employee[i]
        new_name += employee[-1]  # keep the last character
        return new_name


@app.route('/generate_fnsku_label', methods=['GET', 'POST'])
@cross_origin()
def generate_fnsku_label():
    amount_of_labels = int(request.args.get('amount').replace("/inbound-shipment-expected-item?api_token=Yh7l5CUTaZ1nIgAueWglafvm616hchHFFZxRjKjPHNBjB19b2jTDgGoCSpeq", ""))
    expiry_date = request.args.get('expiry_date')
    fnsku = request.args.get('fnsku')
    condition="New"
    text = request.args.get('title')
    if len(text) > 35:
        text = text[:18] + "..." + text[-19:]

    # Set up label dimensions and font sizes
    label_width, label_height = 544, 304
    font_size_fnsku = 35
    font_size_text = 26


    # Retrieve barcode image from URL
    barcode_url = f"http://bwipjs-api.metafloor.com/?bcid=code128&text={fnsku}&scale=2&height=30&rotate=N"
    response = requests.get(barcode_url)
    barcode_image = Image.open(io.BytesIO(response.content)).convert('RGBA')
    barcode_image = ImageOps.crop(barcode_image, (0, 80, 0 ,0))

    # Create label image and draw object
    label_image = Image.new('RGB', (label_width, label_height), color='white')
    draw = ImageDraw.Draw(label_image)

    # Draw barcode image onto label
    barcode_scale = min(label_width / barcode_image.width, label_height / barcode_image.height, 2) *.85
    barcode_width = barcode_scale * barcode_image.width
    barcode_height = barcode_scale * barcode_image.height
    barcode_x = (label_width - barcode_width) / 2
    barcode_y = (label_height - barcode_height) / 2 - 50
    barcode_resized = barcode_image.resize((int(barcode_width), int(barcode_height)), Image.ANTIALIAS)
    label_image.paste(barcode_resized, (int(barcode_x), int(barcode_y)), mask=barcode_resized)

    # Draw FNSKU text onto label
    fnsku_font = ImageFont.truetype('hel.ttf', font_size_fnsku, encoding="unic")
    fnsku_width, fnsku_height = draw.textsize(fnsku, font=fnsku_font)
    fnsku_x = (label_width - fnsku_width) / 2
    fnsku_y = barcode_y + barcode_height + 15
    draw.text((fnsku_x, fnsku_y), fnsku, font=fnsku_font, fill='black')

    # Draw product text onto label
    text_font = ImageFont.truetype('hel.ttf', font_size_text, encoding="unic")
    text_width, text_height = draw.textsize(text, font=text_font)
    text_x = (label_width - text_width) / 2
    text_y = fnsku_y + fnsku_height + 6
    if len(text) > 50:
        chunks = [text[i:i+50] for i in range(0, len(text), 50)][:1]
        for x, i in enumerate(chunks):
            draw.text((text_x, text_y + x * font_size_text), i, font=text_font, fill='black')
        text_y += len(chunks) * font_size_text
    else:
        draw.text((text_x, text_y), text, font=text_font, fill='black')

    # Draw expiry date and condition text onto label
    if expiry_date:
        exp_cond_text = f"{condition}, expires {expiry_date}"
    else:
        exp_cond_text = f"{condition}"

    exp_cond_font = ImageFont.truetype('hel.ttf', font_size_text, encoding="unic")
    exp_cond_width, exp_cond_height = draw.textsize(exp_cond_text, font=exp_cond_font)
    exp_cond_x = (label_width - exp_cond_width) / 2
    exp_cond_y = text_y + text_height + 6
    draw.text((exp_cond_x, exp_cond_y), exp_cond_text, font=exp_cond_font, fill='black')

    img = label_image
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PDF')

    # Create a PdfFileWriter object
    pdf_writer = PdfFileWriter()

    # Add the image to the PDF multiple times
    for i in range(amount_of_labels):
        # Reset the BytesIO object to the beginning
        img_bytes.seek(0)

        # Create a PdfFileReader object from the BytesIO object
        img_pdf_reader = PdfFileReader(img_bytes)

        # Add the image to the PdfFileWriter object
        pdf_writer.addPage(img_pdf_reader.getPage(0))

    pdf_output = io.BytesIO()
    pdf_writer.write(pdf_output)
    pdf_output.seek(0)
    # Create a response object with the PDF bytes
    response = make_response(pdf_output.getvalue())

    # Set the content type of the response to 'application/pdf'
    response.headers.set('Content-Type', 'application/pdf')
    return response

@app.route('/generate_2d_label', methods=['POST'])
@cross_origin()
def generate_2d_label():
    data = request.get_json()
    x = data['data']
    #urllib.request.urlretrieve("https://www.pythonanywhere.com/user/thisbeali/files/home/thisbeali/TEMPLATE", "TEMPLATE")
    #truetype_url = "https://www.pythonanywhere.com/user/thisbeali/files/home/thisbeali/arial.ttf"

    font = ImageFont.truetype("arial.ttf", 12, encoding="unic")
    large_font = ImageFont.truetype("arial.ttf", 20, encoding="unic")
    larger_font = ImageFont.truetype("arial.ttf", 30, encoding="unic")
    largest_font = ImageFont.truetype("arial.ttf", 50, encoding="unic")
    original = Image.open("/home/thisbeali/mysite/template2.png")
    template = original.copy()
    fba_id = x['FBA_ID']
    box_number = x['BOX_NUMBER']
    FC_ID = x['FC_ID']
    FC_ADDRESS = x['FC_ADDRESS']
    _2d_text = x['BOX_STRING']
    shipment_id = x['SHIPMENT_ID']

    # Create QR code image
    qr = qrcode.QRCode(
        version=12,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=2,
        border=8
    )
    qr.add_data(_2d_text)
    qr.make()
    box_image = qr.make_image()

    # Create code128 barcode image

    fba_id_with_box = f"{fba_id}{str(box_number).zfill(6)}"
    barcode_url = f"http://bwipjs-api.metafloor.com/?bcid=code128&text={fba_id_with_box}&scale=1.75&height=20"
    response = requests.get(barcode_url)
    item_image = Image.open(io.BytesIO(response.content)).convert('RGBA')
    #item_image = code128.image(fba_id_with_box, height=100)
    #item_image.save("barcode.jpeg", format='JPEG')

    # Resize images and paste onto template
    box_image.thumbnail((165, 165), Image.ANTIALIAS)
    #new_width = 470
    #new_height = new_width * item_image.height / item_image.width
    #item_image.thumbnail((new_width, new_height), Image.ANTIALIAS)
    template.paste(item_image, (52, 190), mask=item_image)
    template.paste(box_image, (388, 200))
    # Draw text onto template
    draw = ImageDraw.Draw(template)
    draw.text((488, 17), str(box_number), (0, 0, 0), font=larger_font)
    draw.text((70, 260), str(fba_id_with_box), (0, 0, 0), font=large_font)
    #print(FC_ADDRESS)
    #formatted_address = FC_ADDRESS.replace(",", ",\n")
    formatted_address = f"{FC_ADDRESS['name']}\n{FC_ADDRESS['address_line_1']}\n{FC_ADDRESS['city']}, {FC_ADDRESS['state_or_province_code']}\n{FC_ADDRESS['postal_code']} {FC_ADDRESS['country_code']}"
    draw.text((313, 82), formatted_address, (0, 0, 0), font=font)

    # Draw rectangular border around "BOX #x" text
    x, y = (70, 300)
    text = f'BOX #{box_number}'
    text_width, text_height = draw.textsize(text, font=largest_font)
    padding = 10
    rectangle_x = x - padding
    rectangle_y = y - padding
    rectangle_width = text_width + 2 * padding
    rectangle_height = text_height + 2 * padding
    draw.rectangle((rectangle_x, rectangle_y + 5, rectangle_x + rectangle_width, rectangle_y + rectangle_height),
                   outline=(0, 0, 0), width=5)
    draw.text((x, y), text, fill=(0, 0, 0), font=largest_font)

    # Save the template image to a BytesIO object
    image_data = io.BytesIO()
    template.save(image_data, format='pdf')
    response = make_response(image_data.getvalue())
    response.headers.set("Content-Disposition", "attachment", filename=f"{shipment_id}-BOX_{box_number}.pdf")
    response.headers.set("Content-Type", "application/pdf")
    return response




@app.route('/execute_many', methods=['GET', 'POST'])
@cross_origin()
def run_execute_many():

    data = request.get_json()
   # print(data)
    return json.dumps({"successful":execute_many(data['query'], data['arr'])})

def execute_many(q, arr):
    conn = pymysql.connect(
    host='yyzprep-cluster-do-user-10220084-0.b.db.ondigitalocean.com',
    port=25060,
    user='Ali',
    passwd='DjIH53dF23iCTpy3',
    db='YYZPREP'
        )
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cur:
            print(f"Arr is: {arr}")
            for x in arr:
                print (x)
            print(f"Q is {q}")
            cur.executemany(q, arr)
            conn.commit()
            #print("Done executemany")
            return list(cur.fetchall())
    except Exception as e:
        print(e)
        return False
    return False


def runQuery_uplink(query, update=False):
    conn = pymysql.connect(
    host='yyzprep-cluster-do-user-10220084-0.b.db.ondigitalocean.com',
    port=25060,
    user='Ali',
    passwd='DjIH53dF23iCTpy3',
    db='YYZPREP'
)
    #print(query)
    with conn.cursor(pymysql.cursors.DictCursor) as cur:
        cur.execute(f"{query}")
        if update == True:
            conn.commit()
            return
        return list(cur.fetchall())



@app.route('/runQuery', methods=['GET', 'POST'])
@cross_origin()
def runQuery():
    data = request.get_json()
    query = data['query']
    update = data['update']
    #print(f"Query received is: {query}")
    if query:
        query = query.replace("/inbound-shipment-expected-item?api_token=Yh7l5CUTaZ1nIgAueWglafvm616hchHFFZxRjKjPHNBjB19b2jTDgGoCSpeq", "")
        result = runQuery_uplink(query, update)
        return json.dumps(result, indent=4, sort_keys=True, default=str)


@app.route('/runQueryEXCEL')
@cross_origin()
def runQueryEXCEL():
    query = request.args.get('q')
    print(f"Query received is: {query}")
    if query:
        query = query.replace("/inbound-shipment-expected-item?api_token=Yh7l5CUTaZ1nIgAueWglafvm616hchHFFZxRjKjPHNBjB19b2jTDgGoCSpeq", "")
        result = runQuery_uplink(query)
        df = pd.DataFrame(result)
        csv_data = df.to_csv(index=False)
        response = make_response(csv_data)
        response.headers['Content-Disposition'] = 'attachment; filename=data.csv'
        response.headers['Content-type'] = 'text/csv'

        return response
    else:
        return None



@app.route('/daily_shipment_report')
@cross_origin()
def daily_shipment_report():
    date = request.args.get('date')
    if date:
        date = date.replace("/inbound-shipment-expected-item?api_token=Yh7l5CUTaZ1nIgAueWglafvm616hchHFFZxRjKjPHNBjB19b2jTDgGoCSpeq", "")
        q = f"""SELECT SUM(NEW_UNITS) AS UNITS, name AS CLIENT_NAME, EMPLOYEE, DATE(SCAN_TIME) AS DATE
                FROM (
                SELECT c.name, a.* FROM UNITS_SCANNED_LOG a LEFT JOIN OUTBOUNDS b ON b.ID = a.OUTBOUND_ID LEFT JOIN CLIENTS c ON c.id = b.TEAM_ID
                ) z
                  WHERE NEW_UNITS > 0 AND DATE(SCAN_TIME) = '{date}'
                  GROUP BY EMPLOYEE, name, DATE(SCAN_TIME)
                """
        result = runQuery_uplink(q, False)
        df = pd.DataFrame(result)
        csv_data = df.to_csv(index=False)
        response = make_response(csv_data)
        response.headers['Content-Disposition'] = f'attachment; filename={date} Daily Shipment Report.csv'
        response.headers['Content-type'] = 'text/csv'

        return response
    else:
        return None






@app.route('/shifts')
@cross_origin()
def shifts():
    month = request.args.get('month')
    if month:
        month = month.replace("/inbound-shipment-expected-item?api_token=Yh7l5CUTaZ1nIgAueWglafvm616hchHFFZxRjKjPHNBjB19b2jTDgGoCSpeq", "")
        result = get_employee_cost(int(month))
        df = pd.DataFrame(result)
        csv_data = df.to_csv(index=False)
        response = make_response(csv_data)
        response.headers['Content-Disposition'] = 'attachment; filename=data.csv'
        response.headers['Content-type'] = 'text/csv'

        return response
    else:
        return None

@app.route('/shifts_day')
@cross_origin()
def shifts_day():
    month = request.args.get('month')
    day = request.args.get('day')
    if month and day:
        month = month.replace("/inbound-shipment-expected-item?api_token=Yh7l5CUTaZ1nIgAueWglafvm616hchHFFZxRjKjPHNBjB19b2jTDgGoCSpeq", "")
        day = month.replace("/inbound-shipment-expected-item?api_token=Yh7l5CUTaZ1nIgAueWglafvm616hchHFFZxRjKjPHNBjB19b2jTDgGoCSpeq", "")
        result = get_employee_cost(int(month), int(day))
        df = pd.DataFrame(result)
        csv_data = df.to_csv(index=False)
        response = make_response(csv_data)
        response.headers['Content-Disposition'] = 'attachment; filename=data.csv'
        response.headers['Content-type'] = 'text/csv'

        return response
    else:
        return None



def get_employee_cost(month, day=None):
    import requests
    from datetime import datetime
    import calendar

    # Request headers
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    # Request data
    data = {
        "email": "hello@yyzprep.ca",
        "password": "Ali440134@"
    }
    url = "https://api.getsling.com/v1/account/login"
    # Make a POST request with headers and data
    response = requests.post(url, headers=headers, json=data)

    # Print the response
    print(response.text)
    print(response.headers)
    auth = response.headers['Authorization']
    print(auth)
    org_id = response.json()['org']['id']


    url = "https://api.getsling.com/v1/users/"
    # Request headers
    headers = {
        "Accept": "application/json",
        "Authorization" : auth
    }
    # Make a POST request with headers and data
    response = requests.get(url, headers=headers)
    user_info = response.json()
    print(user_info)

    import calendar
   # month = 5
    # Get the current year
    current_year = datetime.now().year

    if day:
        first_day_str = f"{current_year:04d}-{month:02d}-{day:02d}T00%3A00%3A00Z"
        last_day_str = f"{current_year:04d}-{month:02d}-{day:02d}T23%3A59%3A59Z"
    else:

        # Get the first and last day of the month
        _, last_day = calendar.monthrange(current_year, month)

        # Format the first and last day as URL parameters
        first_day_str = f"{current_year:04d}-{month:02d}-01T00%3A00%3A00Z"
        last_day_str = f"{current_year:04d}-{month:02d}-{last_day:02d}T23%3A59%3A59Z"

    # Request headers
    headers = {
        "Accept": "application/json",
        "Authorization" : auth
    }


    url = f"https://api.getsling.com/v1/calendar/484075/users/10093490?dates={first_day_str}%2F{last_day_str}&user-fields=id&nonce=1686333608946"

    response = requests.get(url, headers=headers)
    unique_user_ids = {item['user']['id'] for item in response.json()}
    print(unique_user_ids)

    for user_id in unique_user_ids:
        url = f"https://api.getsling.com/v1/users/{user_id}/description"
        response = requests.get(url, headers=headers)
        rate = response.json()['description']
        print(response.json())
        for x in user_info:
            if x['id'] == user_id:
                x['rate'] = rate




    url = f"https://api.getsling.com/v1/calendar/484075/users/10093490?dates={first_day_str}%2F{last_day_str}&user-fields=id&nonce=1686333608946"

    response = requests.get(url, headers=headers)
    #print(response.json())
    shift_data = []
    for shift in response.json():
        # Convert date strings to datetime objects
        start = datetime.fromisoformat(shift['dtstart'])
        end = datetime.fromisoformat(shift['dtend'])

        # Calculate the difference in hours
        hours = (end - start).total_seconds() / 3600
        #print(hours)
        print([x['name'] for x in user_info if x['id'] == shift['user']['id']][0])
        shift_data.append({
            "date": shift['dtstart'].split("T")[0],
            "employee" : [x['name'] for x in user_info if x['id'] == shift['user']['id']][0],
            "rate": float([x['rate'] for x in user_info if x['id'] == shift['user']['id']][0]),
            "hours": float(hours),
            "total_owed": float(hours) * float([x['rate'] for x in user_info if x['id'] == shift['user']['id']][0])
        })

    print(json.dumps(shift_data))
    employee_data = {}

    # Iterate over each dictionary in the data array
    for entry in shift_data:
        employee = entry['employee']
        hours = entry['hours']
        total_owed = entry['total_owed']

        # Check if the employee already exists in the employee_data dictionary
        if employee in employee_data:
            # If the employee exists, add the hours and total_owed to the existing values
            employee_data[employee]['hours'] += hours
            employee_data[employee]['total_owed'] += total_owed
        else:
            # If the employee doesn't exist, create a new dictionary entry with the employee, hours, and total_owed
            employee_data[employee] = {'employee': employee, 'hours': hours, 'total_owed': total_owed}

    # Extract the values from the employee_data dictionary to get the final list of dictionaries
    result = list(employee_data.values())
    return result

if __name__ == '__main__':
    app.run()
