import os, io, zlib, json, smtplib, traceback
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image

app = Flask(__name__)
CORS(app, origins=["https://visionary-daifuku-f59ee5.netlify.app", "http://localhost"])

# ── Card & chip dimensions (mm) ───────────────────────────────────────────────
CARD_W, CARD_H, CORNER = 85.6, 53.98, 3.18
BLEED, CHIP_BLEED       = 1.0, 1.0
PAGE_W = CARD_W + BLEED*2   # 87.6
PAGE_H = CARD_H + BLEED*2   # 55.98

CHIPS = {
    'standard': dict(x=9.63-0.50-0.75, y=18.73-0.75,  w=11.52+1.50, h=8.54+1.50,  r=1.5),
    'large':    dict(x=9.04-0.30-0.875,y=18.20-1.875, w=13.04+1.75, h=11.92+1.75, r=1.5),
}

def pt(mm_val): return mm_val * 2.8346456693   # mm → PDF points

def rrect(x_mm, y_mm, w_mm, h_mm, r_mm):
    """PDF rounded rectangle path string. y is from bottom of page."""
    x,y,w,h,r = pt(x_mm),pt(y_mm),pt(w_mm),pt(h_mm),pt(r_mm)
    return (f"{x+r:.4f} {y:.4f} m "
            f"{x+w-r:.4f} {y:.4f} l {x+w:.4f} {y:.4f} {x+w:.4f} {y+r:.4f} v "
            f"{x+w:.4f} {y+h-r:.4f} l {x+w:.4f} {y+h:.4f} {x+w-r:.4f} {y+h:.4f} v "
            f"{x+r:.4f} {y+h:.4f} l {x:.4f} {y+h:.4f} {x:.4f} {y+h-r:.4f} v "
            f"{x:.4f} {y+r:.4f} l {x:.4f} {y:.4f} {x+r:.4f} {y:.4f} v h")

def generate_pdf(image_bytes, chip_type, order_info):
    """
    Generate print-ready PDF with proper /Separation spot colors:
    - PerfCutContour (green/cyan-magenta): outer page edge → full cut
    - CutContour (magenta): card edge + chip hole → kiss cut
    VersaWorks reads /Separation colorspace from the content stream.
    """
    chip = CHIPS.get(chip_type, CHIPS['standard'])
    PW, PH = pt(PAGE_W), pt(PAGE_H)

    # ── Prepare image ─────────────────────────────────────────────────────────
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    iw, ih = img.size
    img_raw  = img.tobytes()
    img_comp = zlib.compress(img_raw, 6)

    # Scale image to cover full page
    ia, ca = iw/ih, PAGE_W/PAGE_H
    if ia > ca: dh=PH; dw=PH*ia; dx=(PW-dw)/2; dy=0
    else:       dw=PW; dh=PW/ia; dx=0;          dy=(PH-dh)/2

    # ── Cut path positions ────────────────────────────────────────────────────
    INSET = 0.1   # tiny inset so PerfCut path is fully on page
    perf_path = rrect(INSET, INSET, PAGE_W-INSET*2, PAGE_H-INSET*2, CORNER+BLEED-INSET)
    card_path = rrect(BLEED, BLEED, CARD_W, CARD_H, CORNER)

    # Chip hole (with inward bleed, PDF y from bottom)
    cx  = BLEED + chip['x'] + CHIP_BLEED
    cy  = BLEED + CARD_H - chip['y'] - chip['h'] + CHIP_BLEED
    cw  = chip['w'] - CHIP_BLEED*2
    ch_ = chip['h'] - CHIP_BLEED*2
    cr  = max(0, chip['r'] - CHIP_BLEED)
    chip_path = rrect(cx, cy, cw, ch_, cr)

    # ── Page clip (rounded page edges) ───────────────────────────────────────
    page_clip = rrect(0, 0, PAGE_W, PAGE_H, CORNER+BLEED)

    # ── Content stream ────────────────────────────────────────────────────────
    # /Separation colorspace inline syntax:
    # [/Separation /Name /DeviceCMYK tintFunc] CS  → set colorspace
    # 1 SC                                          → stroke at tint=1.0
    stream = (
        # Draw image clipped to page shape
        f"q {page_clip} W n "
        f"{dw:.4f} 0 0 {dh:.4f} {dx:.4f} {dy:.4f} cm /Im1 Do Q\n"

        # PATH 1: PerfCutContour — outer page edge (full cut)
        f"[/Separation /PerfCutContour /DeviceCMYK "
        f"{{dup 1 mul exch dup 0 mul exch dup 1 mul exch 0 mul}}] CS\n"
        f"1 SC 0.001 w\n"
        f"{perf_path} S\n"

        # PATH 2: CutContour — card edge (kiss cut)
        f"[/Separation /CutContour /DeviceCMYK "
        f"{{dup 0 mul exch dup 1 mul exch dup 0 mul exch 0 mul}}] CS\n"
        f"1 SC 0.001 w\n"
        f"{card_path} S\n"

        # PATH 3: CutContour — chip hole (kiss cut)
        f"{chip_path} S\n"
    )
    stream_comp = zlib.compress(stream.encode(), 6)

    # ── Assemble PDF ──────────────────────────────────────────────────────────
    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")

    offsets = {}

    def write_obj(n, header, stream_data=None):
        offsets[n] = buf.tell()
        buf.write(f"{n} 0 obj\n".encode())
        buf.write(header.encode())
        if stream_data is not None:
            buf.write(b"\nstream\n")
            buf.write(stream_data)
            buf.write(b"\nendstream\n")
        buf.write(b"endobj\n")

    # Obj 1: Image XObject
    write_obj(1,
        f"<< /Type /XObject /Subtype /Image "
        f"/Width {iw} /Height {ih} "
        f"/ColorSpace /DeviceRGB /BitsPerComponent 8 "
        f"/Filter /FlateDecode /Length {len(img_comp)} >>",
        img_comp)

    # Obj 2: Content stream
    write_obj(2,
        f"<< /Length {len(stream_comp)} /Filter /FlateDecode >>",
        stream_comp)

    # Obj 3: Page
    write_obj(3,
        f"<< /Type /Page /Parent 4 0 R "
        f"/MediaBox [0 0 {PW:.4f} {PH:.4f}] "
        f"/Contents 2 0 R "
        f"/Resources << /XObject << /Im1 1 0 R >> >> >>")

    # Obj 4: Pages
    write_obj(4, "<< /Type /Pages /Kids [3 0 R] /Count 1 >>")

    # Obj 5: Catalog
    write_obj(5, "<< /Type /Catalog /Pages 4 0 R >>")

    # xref + trailer
    xref_pos = buf.tell()
    buf.write(b"xref\n0 6\n0000000000 65535 f \n")
    for i in range(1, 6):
        buf.write(f"{offsets[i]:010d} 00000 n \n".encode())
    buf.write(
        f"trailer\n<< /Size 6 /Root 5 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode()
    )

    return buf.getvalue()


def send_email(to_addr, subject, body, attachments):
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    if not smtp_user or not smtp_pass:
        print("WARNING: SMTP credentials not set")
        return False
    msg = MIMEMultipart()
    msg['From'] = smtp_user; msg['To'] = to_addr; msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    for fname, data in attachments:
        part = MIMEBase('application', 'pdf')
        part.set_payload(data)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{fname}"')
        msg.attach(part)
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as s:
            s.login(smtp_user, smtp_pass)
            s.sendmail(smtp_user, to_addr, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


@app.route('/', methods=['GET'])
def root():
    return jsonify({'status': 'ok', 'service': 'Dapper Threads PDF Generator'})

@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'Dapper Threads PDF Generator'})

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf_endpoint():
    try:
        order_info = {
            'first_name':   request.form.get('first_name', ''),
            'last_name':    request.form.get('last_name', ''),
            'email':        request.form.get('email', ''),
            'order_number': request.form.get('order_number', ''),
        }
        designs = json.loads(request.form.get('designs', '[]'))
        print(f"Order: {order_info['first_name']} {order_info['last_name']} #{order_info['order_number']}, {len(designs)} designs")

        attachments = []
        for i, design in enumerate(designs):
            file_key  = f'image_{i+1}'
            chip_type = design.get('chip_type', 'standard')
            quantity  = design.get('quantity', 1)
            d_index   = design.get('design_index', i+1)
            if file_key not in request.files:
                continue
            image_bytes = request.files[file_key].read()
            print(f"  Design {d_index}: {chip_type} chip, {len(image_bytes)} bytes")
            pdf_bytes = generate_pdf(image_bytes, chip_type, order_info)
            fname = (
                f"DapperThreads_{order_info['first_name']}{order_info['last_name']}"
                f"_Order{order_info['order_number']}"
                f"_Design{d_index}_{chip_type}chip_qty{quantity}_PRINT+CUT.pdf"
            )
            attachments.append((fname, pdf_bytes))
            print(f"  → PDF: {len(pdf_bytes)} bytes")

        if not attachments:
            return jsonify({'error': 'No valid images received'}), 400

        chip_labels = {'standard': 'Standard Chip', 'large': 'Large Chip'}
        design_lines = '\n'.join([
            f"  Design {d.get('design_index',i+1)}: {chip_labels.get(d.get('chip_type','standard'),'Standard Chip')}, Qty {d.get('quantity',1)}"
            for i, d in enumerate(designs)
        ])
        subject = f"New Card Skin Order — {order_info['first_name']} {order_info['last_name']} — Order #{order_info['order_number']}"
        body = f"""New card skin order received.

ORDER DETAILS
Name:          {order_info['first_name']} {order_info['last_name']}
Email:         {order_info['email']}
Order #:       {order_info['order_number']}
Total designs: {len(designs)}

DESIGNS
{design_lines}

FILES ATTACHED
{chr(10).join([f"  {f} ({len(d)//1024} KB)" for f,d in attachments])}

Each PDF contains proper /Separation spot colors:
  PerfCutContour — outer edge full cut
  CutContour     — card edge kiss cut + chip hole kiss cut

Drop directly into VersaWorks 6.
"""
        sent = send_email('erika@dapperthreadsus.com', subject, body, attachments)

        # Customer confirmation
        send_email(order_info['email'],
            f"Your Dapper Threads Order #{order_info['order_number']} — Design Received!",
            f"Hi {order_info['first_name']},\n\nThank you for your order! We've received your design(s) and will get started right away.\n\nOrder #: {order_info['order_number']}\nDesigns submitted: {len(designs)}\n\nYour order will ship within 10 business days.\n\nIf you have any questions, please email us at support@dapperthreadsus.com.\n\nThanks for choosing Dapper Threads!\n— The Dapper Threads Team\ndapperthreadsus.com",
            [])

        return jsonify({'status': 'success', 'designs': len(attachments), 'email_sent': sent})

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
