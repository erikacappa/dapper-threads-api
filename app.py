import os, io, zlib, json, smtplib, traceback, struct
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from flask import Flask, request, jsonify
from flask_cors import CORS
from PIL import Image, ImageStat

app = Flask(__name__)
CORS(app, origins=["https://visionary-daifuku-f59ee5.netlify.app", "http://localhost"])

CARD_W, CARD_H, CORNER = 85.6, 53.98, 3.18
BLEED, CHIP_BLEED       = 1.0, 1.0
INSET = 0.1  # perf cut sits this far inside the true outer sheet edge

# The design frame (card + its own bleed) — this is the exact area the
# uploaded design image covers. Unchanged from before; do not touch, since
# the frontend exports its 300dpi PNG to match these dimensions exactly.
CONTENT_W = CARD_W + BLEED*2   # 87.6
CONTENT_H = CARD_H + BLEED*2   # 55.98

# Extra pure-white vinyl margin added OUTSIDE the design frame, purely to
# give the VG3 more room between the kiss cut (card edge) and the full perf
# cut. The thin sliver of material that used to sit between them was
# lifting during cutting and jamming the printer. This does not change the
# design size, position, or the kiss-cut line at all — it only adds blank
# space further out and moves the perf cut out to meet it.
# Previous gap (kiss cut → perf cut) = BLEED - INSET = 0.9mm.
# Adding PERF_MARGIN of the same size doubles the total gap to ~1.8mm.
PERF_MARGIN = BLEED - INSET   # 0.9mm added → ~1.8mm total gap (2x)

PAGE_W = CONTENT_W + PERF_MARGIN*2
PAGE_H = CONTENT_H + PERF_MARGIN*2

FORM_URL = "https://visionary-daifuku-f59ee5.netlify.app"

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


# ── Upload validation ────────────────────────────────────────────────────────
# Catches two distinct failure modes we've seen in the wild:
#   1. Truly corrupted/truncated files (network drop mid-upload) — PIL raises
#      when we force a full decode via img.load().
#   2. Files that decode fine (valid PNG/JPEG) but the *browser* exported the
#      canvas before a tiled background pattern finished loading, leaving a
#      solid black block covering part of the frame. This doesn't raise any
#      decode error, so we need a content heuristic to catch it.

def looks_incomplete(img, band_count=20, blank_threshold=6, run_fraction=0.35):
    """Flag images where a contiguous block of near-black bands sits at the
    top or bottom edge of the frame, suggesting the design didn't fully
    render before export. Real dark/black designs still have variance from
    prints/text/borders; a flat, uniform black block run is the signature of
    a failed render, not an intentional dark background."""
    w, h = img.size
    band_h = max(1, h // band_count)
    means = []
    for i in range(band_count):
        top = i * band_h
        bottom = h if i == band_count - 1 else top + band_h
        band = img.crop((0, top, w, bottom))
        stat = ImageStat.Stat(band)
        means.append(sum(stat.mean) / len(stat.mean))

    def longest_blank_run_from(edge):
        seq = means if edge == 'top' else list(reversed(means))
        run = 0
        for m in seq:
            if m <= blank_threshold:
                run += 1
            else:
                break
        return run

    worst_run = max(longest_blank_run_from('top'), longest_blank_run_from('bottom'))
    return worst_run >= band_count * run_fraction


def validate_upload(image_bytes):
    """Returns (ok, reason). reason is None when ok is True."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        img.load()  # forces full decode; raises on truncated/corrupted data
    except Exception as e:
        return False, f"file appears corrupted or incomplete ({e})"

    try:
        img = img.convert('RGB')
        if looks_incomplete(img):
            return False, "design appears to be missing content (partial render)"
    except Exception as e:
        return False, f"could not process image ({e})"

    return True, None


def generate_pdf(image_bytes, chip_type, order_info):
    chip = CHIPS.get(chip_type, CHIPS['standard'])
    PW, PH = pt(PAGE_W), pt(PAGE_H)              # full physical sheet, incl. new perf margin
    CW, CH = pt(CONTENT_W), pt(CONTENT_H)        # original design/bleed frame — unchanged size

    # Prepare image
    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    iw, ih = img.size
    # (Previously also compressed the raw image bytes here as `img_comp`,
    # but that result was never used — the real compression for the PDF's
    # image stream happens later, in the Obj 5 wobj() call below. Computing
    # it twice roughly doubled the CPU time PDF generation spent on zlib
    # per design, for no benefit — removed.)

    # Image scale to cover the ORIGINAL content frame only — identical size/
    # position math to before. The image is never stretched or resized to
    # fill the new, larger sheet; it's simply placed (offset) within it.
    ia, ca = iw/ih, CONTENT_W/CONTENT_H
    if ia > ca: dh=CH; dw=CH*ia; dx=(CW-dw)/2; dy=0
    else:       dw=CW; dh=CW/ia; dx=0;          dy=(CH-dh)/2
    # Shift into position within the larger sheet — everything beyond this
    # offset region is untouched vinyl (blank/white), out to the perf cut.
    dx += pt(PERF_MARGIN)
    dy += pt(PERF_MARGIN)

    # Cut paths — kiss cut (card_path) and chip cutout keep their original
    # size and position, just translated outward by PERF_MARGIN since the
    # sheet origin moved. The perf cut now runs near the edge of the new,
    # larger sheet instead of the old one.
    perf_path = rrect(INSET, INSET, PAGE_W-INSET*2, PAGE_H-INSET*2, CORNER+BLEED+PERF_MARGIN-INSET)
    card_path = rrect(PERF_MARGIN+BLEED, PERF_MARGIN+BLEED, CARD_W, CARD_H, CORNER)
    cx  = PERF_MARGIN + BLEED + chip['x'] + CHIP_BLEED
    cy  = PERF_MARGIN + BLEED + CARD_H - chip['y'] - chip['h'] + CHIP_BLEED
    chip_path = rrect(cx, cy, chip['w']-CHIP_BLEED*2, chip['h']-CHIP_BLEED*2, max(0,chip['r']-CHIP_BLEED))

    # Image is clipped to the original content-frame shape/size, just
    # repositioned — so it never bleeds into the new blank margin.
    page_clip = rrect(PERF_MARGIN, PERF_MARGIN, CONTENT_W, CONTENT_H, CORNER+BLEED)

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


# Gmail rejects any outgoing message once its total (post-base64) size
# exceeds ~25MB. Base64 inflates raw attachment bytes by ~1.37x, so we cap
# each email's raw attachment payload well under that line. Large orders
# (many designs/copies) are automatically split across multiple emails
# instead of silently failing to send at all.
MAX_BATCH_BYTES = 15 * 1024 * 1024  # 15MB raw ≈ ~20.5MB after base64

def send_email(to_addr, subject, body, attachments):
    smtp_user = os.environ.get('SMTP_USER', '')
    smtp_pass = os.environ.get('SMTP_PASS', '')
    if not smtp_user or not smtp_pass:
        print("WARNING: SMTP credentials not set"); return False

    # Split attachments into size-safe batches.
    batches = []
    current, current_size = [], 0
    for fname, data in attachments:
        if current and current_size + len(data) > MAX_BATCH_BYTES:
            batches.append(current)
            current, current_size = [], 0
        current.append((fname, data))
        current_size += len(data)
    if current or not attachments:
        batches.append(current)

    total_parts = len(batches)
    all_ok = True
    for idx, batch in enumerate(batches, start=1):
        part_subject = subject if total_parts == 1 else f"{subject} (Part {idx} of {total_parts})"
        part_body = body if total_parts == 1 else (
            f"{body}\n\nThis order's files were split across {total_parts} emails "
            f"due to attachment size — this is part {idx} of {total_parts}."
        )
        msg = MIMEMultipart()
        msg['From']=smtp_user; msg['To']=to_addr; msg['Subject']=part_subject
        msg.attach(MIMEText(part_body,'plain'))
        for fname,data in batch:
            part=MIMEBase('application','pdf'); part.set_payload(data)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition',f'attachment; filename="{fname}"')
            msg.attach(part)
        try:
            with smtplib.SMTP_SSL('smtp.gmail.com',465) as s:
                s.login(smtp_user,smtp_pass); s.sendmail(smtp_user,to_addr,msg.as_string())
        except Exception as e:
            print(f"Email error (part {idx} of {total_parts}): {e}")
            all_ok = False
    return all_ok


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

        chip_labels = {'standard':'Standard Chip','large':'Large Chip'}
        attachments = []
        failed = []  # [{'index':.., 'chip':.., 'reason':..}]

        designs_ok = 0

        for i,design in enumerate(designs):
            fk = f'image_{i+1}'
            if fk not in request.files: continue
            chip  = design.get('chip_type','standard')
            didx  = design.get('design_index',i+1)
            try:
                qty = max(1, int(design.get('quantity',1)))
            except (TypeError, ValueError):
                qty = 1
            img_b = request.files[fk].read()
            print(f"  Design {didx}: {chip} chip, qty {qty}, {len(img_b)} bytes")

            ok, reason = validate_upload(img_b)
            if not ok:
                print(f"  ⚠ Design {didx} FAILED validation: {reason}")
                failed.append({'index': didx, 'chip': chip, 'qty': qty, 'reason': reason})
                continue

            pdf = generate_pdf(img_b, chip, order_info)
            designs_ok += 1
            # One PDF file per requested copy — so the inbox has exactly as
            # many files as cards to produce, no manual duplicating needed.
            # Naming convention: CustomerName_Order#_Design#_CopyXofX.pdf
            customer_name = f"{order_info['first_name']}{order_info['last_name']}"
            for copy_n in range(1, qty+1):
                fname = f"{customer_name}_Order{order_info['order_number']}_Design{didx}_Copy{copy_n}of{qty}.pdf"
                attachments.append((fname,pdf))
            print(f"  → {len(pdf):,} bytes × {qty} copies")

        if not attachments and not failed: return jsonify({'error':'No valid images'}),400

        design_lines = '\n'.join([f"  Design {d.get('design_index',i+1)}: {chip_labels.get(d.get('chip_type','standard'))}, Qty {d.get('quantity',1)}" for i,d in enumerate(designs)])

        subject = f"New Card Skin Order — {order_info['first_name']} {order_info['last_name']} — Order #{order_info['order_number']}"
        if failed:
            subject += " — ⚠ design upload issue"

        body = (f"New order received.\n\n"
                f"Name: {order_info['first_name']} {order_info['last_name']}\n"
                f"Email: {order_info['email']}\n"
                f"Order #: {order_info['order_number']}\n"
                f"Designs submitted: {len(designs)}\n"
                f"Designs processed OK: {designs_ok}\n"
                f"Designs failed: {len(failed)}\n"
                f"Total PDF files attached: {len(attachments)} (one per card, quantities already expanded)\n\n"
                f"{design_lines}\n")

        if failed:
            failed_lines = '\n'.join([f"  Design {f['index']} ({chip_labels.get(f['chip'],'Unknown')}): {f['reason']}" for f in failed])
            body += (f"\n⚠️ The following design(s) did NOT upload correctly and were NOT included as PDFs:\n"
                      f"{failed_lines}\n\n"
                      f"The customer has been emailed asking them to resubmit these specific design(s).\n")

        body += ("\nPDF files use proper /Separation spot colors — drop directly into VersaWorks 6.\n"
                 "  CutContour = kiss cut (card edge + chip hole)\n"
                 "  PerfCutContour = full cut (outer edge)\n")

        sent = send_email('erika@dapperthreadsus.com', subject, body, attachments)

        if failed:
            failed_customer_lines = '\n'.join([f"  Design {f['index']} ({chip_labels.get(f['chip'],'')})" for f in failed])
            cust_subject = f"Action Needed — Your Dapper Threads Order #{order_info['order_number']}"
            cust_body = (f"Hi {order_info['first_name']},\n\n"
                         f"Thanks for your order! We received {len(attachments)} of your {len(designs)} design(s) successfully "
                         f"and are already getting started on those.\n\n"
                         f"Unfortunately the following design(s) didn't upload correctly and could not be processed:\n"
                         f"{failed_customer_lines}\n\n"
                         f"This usually happens when an image doesn't finish uploading (e.g. a slow or interrupted connection). "
                         f"Please resubmit just these design(s) here: {FORM_URL}\n"
                         f"Reference Order #{order_info['order_number']} so we can match it up with the rest of your order.\n\n"
                         f"Your order ships within 10 business days of us receiving all designs.\n\n"
                         f"Questions? Email support@dapperthreadsus.com\n\n"
                         f"— The Dapper Threads Team")
        else:
            cust_subject = f"Your Dapper Threads Order #{order_info['order_number']} — Design Received!"
            cust_body = (f"Hi {order_info['first_name']},\n\n"
                         f"Thank you! We've received your design(s) and will get started right away.\n\n"
                         f"Order #: {order_info['order_number']}\n"
                         f"Designs: {len(designs)}\n\n"
                         f"Your order ships within 10 business days.\n\n"
                         f"Questions? Email support@dapperthreadsus.com\n\n"
                         f"— The Dapper Threads Team")

        send_email(order_info['email'], cust_subject, cust_body, [])

        return jsonify({
            'status': 'success' if not failed else 'partial',
            'designs_ok': designs_ok,
            'files_attached': len(attachments),
            'failed': failed,
            'email_sent': sent
        })
    except Exception as e:
        traceback.print_exc(); return jsonify({'error':str(e)}),500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT',10000)), debug=False)
