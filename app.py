import os, io, zlib, json, smtplib, traceback, struct
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image

app = Flask(__name__)
CORS(app, origins=["https://visionary-daifuku-f59ee5.netlify.app", "http://localhost"])

CARD_W, CARD_H, CORNER = 85.6, 53.98, 3.18
BLEED, CHIP_BLEED       = 1.0, 1.0
PAGE_W = CARD_W + BLEED*2
PAGE_H = CARD_H + BLEED*2

CHIPS = {
    'standard': dict(x=9.63-0.50-0.75, y=18.73-0.75,  w=11.52+1.50, h=8.54+1.50,  r=1.5),
    'large':    dict(x=9.04-0.30-0.875,y=18.20-1.875, w=13.04+1.75, h=11.92+1.75, r=1.5),
}

def pt(v): return v * 2.8346456693

def rrect(x, y, w, h, r):
    """Rounded rect PDF path. All args in mm, y from page bottom."""
    x,y,w,h,r = pt(x),pt(y),pt(w),pt(h),pt(r)
    return (f"{x+r:.4f} {y:.4f} m "
            f"{x+w-r:.4f} {y:.4f} l {x+w:.4f} {y:.4f} {x+w:.4f} {y+r:.4f} v "
            f"{x+w:.4f} {y+h-r:.4f} l {x+w:.4f} {y+h:.4f} {x+w-r:.4f} {y+h:.4f} v "
            f"{x+r:.4f} {y+h:.4f} l {x:.4f} {y+h:.4f} {x:.4f} {y+h-r:.4f} v "
            f"{x:.4f} {y+r:.4f} l {x:.4f} {y:.4f} {x+r:.4f} {y:.4f} v h")

def generate_pdf(image_bytes, chip_type, order_info):
    chip = CHIPS.get(chip_type, CHIPS['standard'])
    PW, PH = pt(PAGE_W), pt(PAGE_H)

    # Prepare image
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    iw, ih = img.size
    img_comp = zlib.compress(img.tobytes(), 6)

    # Image scale to cover full page
    ia, ca = iw/ih, PAGE_W/PAGE_H
    if ia > ca: dh=PH; dw=PH*ia; dx=(PW-dw)/2; dy=0
    else:       dw=PW; dh=PW/ia; dx=0;          dy=(PH-dh)/2

    # Cut paths
    INSET = 0.1
    perf_path = rrect(INSET, INSET, PAGE_W-INSET*2, PAGE_H-INSET*2, CORNER+BLEED-INSET)
    card_path = rrect(BLEED, BLEED, CARD_W, CARD_H, CORNER)
    cx  = BLEED + chip['x'] + CHIP_BLEED
    cy  = BLEED + CARD_H - chip['y'] - chip['h'] + CHIP_BLEED
    chip_path = rrect(cx, cy, chip['w']-CHIP_BLEED*2, chip['h']-CHIP_BLEED*2, max(0,chip['r']-CHIP_BLEED))

    page_clip = rrect(0, 0, PAGE_W, PAGE_H, CORNER+BLEED)

    # ── Build PDF objects ─────────────────────────────────────────────────────
    # We define spot colors as named resources in /ColorSpace dict on the page
    # so VersaWorks can find them as proper separations.
    # /CS1 = CutContour, /CS2 = PerfCutContour
    #
    # Tint functions:
    #   CutContour     → DeviceCMYK 0 1 0 0 (magenta)
    #   PerfCutContour → DeviceCMYK 1 0 1 0 (green)
    #
    # Each is: [/Separation /Name /DeviceCMYK tintFunc]
    # tintFunc is a PostScript function {t 0 t 0} etc.

    # Tint function objects
    # Function type 4 (PostScript calculator):
    # CutContour: input tint → output 0 t 0 0 (magenta channel)
    cut_func_str = b"{ 0 exch 1 exch sub 0 0 }"  # {t} → {0, 1-t, 0, 0} ... simplified
    # Use type 2 (exponential) for simplicity: just map tint directly
    # Actually simplest: type 4 with direct mapping
    cut_func_str  = b"{ dup 0 mul exch dup 1 mul exch dup 0 mul exch 0 mul }"
    perf_func_str = b"{ dup 1 mul exch dup 0 mul exch dup 1 mul exch 0 mul }"

    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}

    def wobj(n, header, stream=None):
        offsets[n] = buf.tell()
        buf.write(f"{n} 0 obj\n".encode())
        if stream is not None:
            h2 = header.rstrip()
            # inject /Length
            h2 = h2.rstrip('>').rstrip() + f" /Length {len(stream)} >>"
            buf.write(h2.encode())
            buf.write(b"\nstream\n")
            buf.write(stream)
            buf.write(b"\nendstream\n")
        else:
            buf.write(header.encode())
        buf.write(b"endobj\n")

    # Obj 1: CutContour tint function (PostScript type 4)
    wobj(1, f"<< /FunctionType 4 /Domain [0 1] /Range [0 1 0 1 0 1 0 1]>>",
         cut_func_str)

    # Obj 2: PerfCutContour tint function
    wobj(2, f"<< /FunctionType 4 /Domain [0 1] /Range [0 1 0 1 0 1 0 1]>>",
         perf_func_str)

    # Obj 3: CutContour colorspace array
    wobj(3, "[/Separation /CutContour /DeviceCMYK 1 0 R]\n")

    # Obj 4: PerfCutContour colorspace array
    wobj(4, "[/Separation /PerfCutContour /DeviceCMYK 2 0 R]\n")

    # Obj 5: Image XObject
    wobj(5,
        f"<< /Type /XObject /Subtype /Image "
        f"/Width {iw} /Height {ih} "
        f"/ColorSpace /DeviceRGB /BitsPerComponent 8 "
        f"/Filter /FlateDecode >>",
        zlib.compress(img.tobytes(), 6))

    # Obj 6: Content stream
    # Use named colorspace resources /CutCS and /PerfCS
    # cs = set non-stroking colorspace, CS = set stroking colorspace
    # sc/SC = set color
    stream = (
        # Draw image clipped to page shape
        f"q {page_clip} W n "
        f"{dw:.4f} 0 0 {dh:.4f} {dx:.4f} {dy:.4f} cm /Im1 Do Q\n"

        # PerfCutContour path — full cut outer edge
        # Select spot colorspace, set stroke to tint=1, no fill
        f"/PerfCS CS 1 SCN 0.001 w\n"
        f"{perf_path} S\n"

        # CutContour path — card edge kiss cut
        f"/CutCS CS 1 SCN 0.001 w\n"
        f"{card_path} S\n"

        # CutContour path — chip hole kiss cut (reuse same CS)
        f"{chip_path} S\n"
    )
    stream_comp = zlib.compress(stream.encode(), 6)
    wobj(6, f"<< /Filter /FlateDecode >>", stream_comp)

    # Obj 7: Page — with ColorSpace resource dict referencing spot color arrays
    wobj(7,
        f"<< /Type /Page /Parent 8 0 R "
        f"/MediaBox [0 0 {PW:.4f} {PH:.4f}] "
        f"/Contents 6 0 R "
        f"/Resources << "
        f"/XObject << /Im1 5 0 R >> "
        f"/ColorSpace << /CutCS 3 0 R /PerfCS 4 0 R >> "
        f">> >>\n")

    # Obj 8: Pages
    wobj(8, "<< /Type /Pages /Kids [7 0 R] /Count 1 >>\n")

    # Obj 9: Catalog
    wobj(9, "<< /Type /Catalog /Pages 8 0 R >>\n")

    xref_pos = buf.tell()
    buf.write(b"xref\n0 10\n0000000000 65535 f \n")
    for i in range(1, 10):
        buf.write(f"{offsets[i]:010d} 00000 n \n".encode())
    buf.write(f"trailer\n<< /Size 10 /Root 9 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode())

    return buf.getvalue()


def send_email(to_addr, subject, body, attachments):
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    if not smtp_user or not smtp_pass:
        print("WARNING: SMTP credentials not set"); return False
    msg = MIMEMultipart()
    msg['From']=smtp_user; msg['To']=to_addr; msg['Subject']=subject
    msg.attach(MIMEText(body,'plain'))
    for fname,data in attachments:
        part=MIMEBase('application','pdf'); part.set_payload(data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition',f'attachment; filename="{fname}"')
        msg.attach(part)
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com',465) as s:
            s.login(smtp_user,smtp_pass); s.sendmail(smtp_user,to_addr,msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}"); return False


@app.route('/', methods=['GET'])
def root(): return jsonify({'status':'ok','service':'Dapper Threads PDF Generator'})

@app.route('/health', methods=['GET'])
def health(): return jsonify({'status':'ok','service':'Dapper Threads PDF Generator'})

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf_endpoint():
    try:
        order_info = {k: request.form.get(k,'') for k in ['first_name','last_name','email','order_number']}
        designs = json.loads(request.form.get('designs','[]'))
        print(f"Order: {order_info['first_name']} {order_info['last_name']} #{order_info['order_number']}, {len(designs)} designs")

        attachments = []
        for i,design in enumerate(designs):
            fk = f'image_{i+1}'
            if fk not in request.files: continue
            chip  = design.get('chip_type','standard')
            qty   = design.get('quantity',1)
            didx  = design.get('design_index',i+1)
            img_b = request.files[fk].read()
            print(f"  Design {didx}: {chip} chip, {len(img_b)} bytes")
            pdf   = generate_pdf(img_b, chip, order_info)
            fname = (f"DapperThreads_{order_info['first_name']}{order_info['last_name']}"
                     f"_Order{order_info['order_number']}_Design{didx}_{chip}chip_qty{qty}_PRINT+CUT.pdf")
            attachments.append((fname,pdf))
            print(f"  → {len(pdf):,} bytes")

        if not attachments: return jsonify({'error':'No valid images'}),400

        chip_labels = {'standard':'Standard Chip','large':'Large Chip'}
        design_lines = '\n'.join([f"  Design {d.get('design_index',i+1)}: {chip_labels.get(d.get('chip_type','standard'))}, Qty {d.get('quantity',1)}" for i,d in enumerate(designs)])
        subject = f"New Card Skin Order — {order_info['first_name']} {order_info['last_name']} — Order #{order_info['order_number']}"
        body = f"New order received.\n\nName: {order_info['first_name']} {order_info['last_name']}\nEmail: {order_info['email']}\nOrder #: {order_info['order_number']}\nDesigns: {len(designs)}\n\n{design_lines}\n\nPDF files use proper /Separation spot colors — drop directly into VersaWorks 6.\n  CutContour = kiss cut (card edge + chip hole)\n  PerfCutContour = full cut (outer edge)\n"
        sent = send_email('erika@dapperthreadsus.com', subject, body, attachments)
        send_email(order_info['email'],
            f"Your Dapper Threads Order #{order_info['order_number']} — Design Received!",
            f"Hi {order_info['first_name']},\n\nThank you! We've received your design(s) and will get started right away.\n\nOrder #: {order_info['order_number']}\nDesigns: {len(designs)}\n\nYour order ships within 10 business days.\n\nQuestions? Email support@dapperthreadsus.com\n\n— The Dapper Threads Team", [])

        return jsonify({'status':'success','designs':len(attachments),'email_sent':sent})
    except Exception as e:
        traceback.print_exc(); return jsonify({'error':str(e)}),500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)), debug=False)
