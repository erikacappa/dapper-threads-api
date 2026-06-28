import os
import io
import base64
import smtplib
import json
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from flask import Flask, request, jsonify
from flask_cors import CORS
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import CMYKColor, Color, white
from PIL import Image

app = Flask(__name__)
CORS(app, origins=["https://visionary-daifuku-f59ee5.netlify.app", "http://localhost"])

# ── Spot colors ───────────────────────────────────────────────────────────────
CUT_CONTOUR  = CMYKColor(0, 1, 0, 0, spotName='CutContour',     density=1.0)
PERF_CONTOUR = CMYKColor(1, 0, 1, 0, spotName='PerfCutContour', density=1.0)

# ── Card dimensions ───────────────────────────────────────────────────────────
CARD_W_MM  = 85.6
CARD_H_MM  = 53.98
CORNER_MM  = 3.18
CHIP_R_MM  = 1.5
BLEED_MM   = 1.0
CHIP_BLEED = 1.0   # inward bleed on chip hole

PAGE_W_MM  = CARD_W_MM + BLEED_MM * 2   # 87.6mm
PAGE_H_MM  = CARD_H_MM + BLEED_MM * 2   # 55.98mm

# ── Calibrated chip specs (locked from physical test prints) ──────────────────
CHIPS = {
    'standard': {
        'x': 9.63 - 0.50 - 1.50/2,
        'y': 18.73 + 0.00 - 1.50/2,
        'w': 11.52 + 1.50,
        'h':  8.54 + 1.50,
        'label': 'Standard Chip'
    },
    'large': {
        'x': 9.04 - 0.30 - 1.75/2,
        'y': 18.20 - 1.00 - 1.75/2,
        'w': 13.04 + 1.75,
        'h': 11.92 + 1.75,
        'label': 'Large Chip'
    }
}

def generate_card_pdf(image_bytes, chip_type, order_info):
    """
    Generate a print-ready PDF with:
    - Customer photo filling full bleed area
    - PerfCutContour at outer page edge (full cut)
    - CutContour at card edge/bleed boundary (kiss cut)
    - CutContour at chip hole (kiss cut)
    """
    chip = CHIPS.get(chip_type, CHIPS['standard'])
    buf  = io.BytesIO()

    pw = PAGE_W_MM * mm
    ph = PAGE_H_MM * mm

    c = rl_canvas.Canvas(buf, pagesize=(pw, ph))
    c.setTitle(
        f"Dapper Threads — {order_info.get('first_name','')} {order_info.get('last_name','')} "
        f"— Order {order_info.get('order_number','')} — {chip['label']}"
    )

    # Card position (inset 1mm bleed from page edge)
    card_x = BLEED_MM * mm
    card_y = BLEED_MM * mm
    card_w = CARD_W_MM * mm
    card_h = CARD_H_MM * mm
    card_r = CORNER_MM * mm

    # Chip hole position (PDF y is bottom-up)
    # With inward bleed applied
    chip_x  = (BLEED_MM + chip['x'] + CHIP_BLEED) * mm
    chip_y  = (BLEED_MM + CARD_H_MM - chip['y'] - chip['h'] + CHIP_BLEED) * mm
    chip_w  = (chip['w'] - CHIP_BLEED * 2) * mm
    chip_h  = (chip['h'] - CHIP_BLEED * 2) * mm
    chip_r  = max(0, (CHIP_R_MM - CHIP_BLEED)) * mm

    # ── LAYER 1: Customer photo (full bleed) ──────────────────────────────────
    # The frontend has already rendered the image to a canvas with all transforms
    # applied, so image_bytes is a pre-composited PNG at the right size.
    # We just need to draw it filling the full page.
    try:
        from reportlab.lib.utils import ImageReader

        img = Image.open(io.BytesIO(image_bytes)).convert('RGBA')
        img_w, img_h = img.size

        # Scale to cover full page
        page_aspect = PAGE_W_MM / PAGE_H_MM
        img_aspect  = img_w / img_h

        if img_aspect > page_aspect:
            draw_h = ph
            draw_w = ph * img_aspect
        else:
            draw_w = pw
            draw_h = pw / img_aspect

        x_off = (pw - draw_w) / 2
        y_off = (ph - draw_h) / 2

        # Convert RGBA to RGB with white background for PDF compatibility
        bg = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'RGBA':
            bg.paste(img, mask=img.split()[3])
        else:
            bg = img.convert('RGB')

        img_buf = io.BytesIO()
        bg.save(img_buf, format='PNG', optimize=False)
        img_buf.seek(0)

        img_reader = ImageReader(img_buf)

        # Draw image filling full page (bleed area)
        c.drawImage(img_reader, x_off, y_off, draw_w, draw_h,
                    preserveAspectRatio=False)

    except Exception as e:
        print(f"Image draw error: {e}")
        import traceback; traceback.print_exc()
        # Fallback: light grey background
        c.setFillColor(Color(0.9, 0.9, 0.9))
        c.rect(0, 0, pw, ph, fill=1, stroke=0)

    # ── LAYER 2: White chip hole (knocks out photo under chip) ───────────────
    c.saveState()
    c.setFillColor(white)
    c.setStrokeColor(Color(0, 0, 0, 0))
    c.roundRect(chip_x, chip_y, chip_w, chip_h, chip_r, fill=1, stroke=0)
    c.restoreState()

    # ── LAYER 3: PerfCutContour — outer page edge (full cut through) ─────────
    inset = 0.1 * mm
    perf_r = (CORNER_MM + BLEED_MM) * mm
    c.saveState()
    c.setStrokeColor(PERF_CONTOUR)
    c.setFillColor(Color(0, 0, 0, 0))
    c.setLineWidth(0.25)
    c.roundRect(inset, inset, pw - inset*2, ph - inset*2, perf_r, fill=0, stroke=1)
    c.restoreState()

    # ── LAYER 4: CutContour — card edge / bleed boundary (kiss cut) ──────────
    c.saveState()
    c.setStrokeColor(CUT_CONTOUR)
    c.setFillColor(Color(0, 0, 0, 0))
    c.setLineWidth(0.25)
    c.roundRect(card_x, card_y, card_w, card_h, card_r, fill=0, stroke=1)
    c.restoreState()

    # ── LAYER 5: CutContour — chip hole (kiss cut) ────────────────────────────
    c.saveState()
    c.setStrokeColor(CUT_CONTOUR)
    c.setFillColor(Color(0, 0, 0, 0))
    c.setLineWidth(0.25)
    c.roundRect(chip_x, chip_y, chip_w, chip_h, chip_r, fill=0, stroke=1)
    c.restoreState()

    c.save()
    buf.seek(0)
    return buf.read()


def send_email(to_addr, subject, body_text, attachments):
    """Send email with PDF attachments via Gmail SMTP."""
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')

    if not smtp_user or not smtp_pass:
        print("WARNING: SMTP credentials not set — email not sent")
        return False

    msg = MIMEMultipart()
    msg['From']    = smtp_user
    msg['To']      = to_addr
    msg['Subject'] = subject
    msg.attach(MIMEText(body_text, 'plain'))

    for filename, pdf_bytes in attachments:
        part = MIMEBase('application', 'pdf')
        part.set_payload(pdf_bytes)
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f'attachment; filename="{filename}"')
        msg.attach(part)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_addr, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'Dapper Threads PDF Generator'})


@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    """
    Accepts multipart form data:
    - first_name, last_name, email, order_number (text)
    - designs: JSON array of {chip_type, quantity, design_index}
    - image_1, image_2, ... (PNG files, pre-rendered from frontend canvas)
    Returns: JSON with status and any errors
    """
    try:
        # Parse order info
        order_info = {
            'first_name':    request.form.get('first_name', ''),
            'last_name':     request.form.get('last_name', ''),
            'email':         request.form.get('email', ''),
            'order_number':  request.form.get('order_number', ''),
        }
        designs_json = request.form.get('designs', '[]')
        designs      = json.loads(designs_json)

        attachments = []
        pdf_data_list = []

        for i, design in enumerate(designs):
            file_key  = f'image_{i+1}'
            chip_type = design.get('chip_type', 'standard')
            quantity  = design.get('quantity', 1)
            d_index   = design.get('design_index', i+1)

            if file_key not in request.files:
                continue

            image_bytes = request.files[file_key].read()
            pdf_bytes   = generate_card_pdf(image_bytes, chip_type, order_info)

            fname = (
                f"DapperThreads_{order_info['first_name']}{order_info['last_name']}"
                f"_Order{order_info['order_number']}"
                f"_Design{d_index}_{chip_type}chip_qty{quantity}_PRINT+CUT.pdf"
            )
            attachments.append((fname, pdf_bytes))
            pdf_data_list.append({
                'filename': fname,
                'size_kb':  round(len(pdf_bytes) / 1024)
            })

        if not attachments:
            return jsonify({'error': 'No valid images received'}), 400

        # Build email body
        chip_labels = {'standard': 'Standard Chip', 'large': 'Large Chip'}
        design_lines = '\n'.join([
            f"  Design {d.get('design_index',i+1)}: "
            f"{chip_labels.get(d.get('chip_type','standard'), 'Standard Chip')}, "
            f"Qty {d.get('quantity',1)}"
            for i, d in enumerate(designs)
        ])

        subject = (
            f"New Card Skin Order — {order_info['first_name']} {order_info['last_name']} "
            f"— Order #{order_info['order_number']}"
        )
        body = f"""New card skin order received via DapperThreadsUS.com

ORDER DETAILS
─────────────────────────────────────
Name:         {order_info['first_name']} {order_info['last_name']}
Email:        {order_info['email']}
Order #:      {order_info['order_number']}
Total designs: {len(designs)}

DESIGNS
─────────────────────────────────────
{design_lines}

FILES ATTACHED
─────────────────────────────────────
{chr(10).join([f"  {p['filename']} ({p['size_kb']} KB)" for p in pdf_data_list])}

Each PDF contains:
  • Customer photo (full bleed)
  • PerfCutContour — outer edge full cut
  • CutContour — card edge kiss cut
  • CutContour — chip hole kiss cut

Drop each PDF directly into VersaWorks 6 to print and cut.

─────────────────────────────────────
Dapper Threads Automated Order System
"""

        # Send to Erika
        email_sent = send_email(
            'erika@dapperthreadsus.com',
            subject, body, attachments
        )

        # Also send confirmation to customer
        customer_subject = f"Your Dapper Threads Order #{order_info['order_number']} — Design Received!"
        customer_body = f"""Hi {order_info['first_name']},

Thank you for your order! We've received your custom card skin design(s) and will get started on them right away.

Order #: {order_info['order_number']}
Designs submitted: {len(designs)}

Your order will ship within 10 business days. We'll be in touch if we have any questions.

Thanks for choosing Dapper Threads!
— The Dapper Threads Team
dapperthreadsus.com
"""
        send_email(order_info['email'], customer_subject, customer_body, [])

        return jsonify({
            'status':     'success',
            'designs':    len(attachments),
            'email_sent': email_sent,
            'files':      pdf_data_list
        })

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/', methods=['GET'])
def root():
    return jsonify({'status': 'ok', 'service': 'Dapper Threads PDF Generator'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
