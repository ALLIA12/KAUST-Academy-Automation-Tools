import os
import time
import uuid
from datetime import datetime
from reportlab.lib.pagesizes import landscape,portrait
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import pandas as pd
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, gray
from PyPDF2 import PdfWriter, PdfReader
from dotenv import load_dotenv
from reportlab.pdfbase import pdfmetrics

# Load environment variables from .env file
load_dotenv()


def read_excel(file_path):
    return pd.read_excel(file_path)


def create_pdf_with_text(output_path, text_data, guid):
    #3.54 × 5.11
    page_width = 3.54 * inch
    page_height = 5.11 * inch
    c = canvas.Canvas(output_path, pagesize=portrait((page_width, page_height)))

    # Set the font and size for the main text
    font_name = "Helvetica"
    name_font_size = 12


    # Calculate vertical positions with increased padding
    y_start = page_height * 0.5  # Starting position

    # Draw the name
    c.setFont(font_name, name_font_size)
    c.setFillColor(black)
    name_text = text_data['Full Name'].upper()
    name_width = pdfmetrics.stringWidth(name_text, font_name, name_font_size)
    c.drawString((page_width - name_width) / 2, y_start, name_text)

    # Add GUID to the bottom left corner
    c.setFont("Helvetica", 4)  # Smaller font for GUID
    c.setFillColor(gray)
    c.drawString(0.25 * inch, 0.25 * inch, str(guid))

    c.save()


def merge_pdfs(template_path, overlay_path, output_path):
    with open(template_path, "rb") as template_file, open(overlay_path, "rb") as overlay_file:
        template_pdf = PdfReader(template_file)
        overlay_pdf = PdfReader(overlay_file)

        output = PdfWriter()

        # Get the template page
        template_page = template_pdf.pages[0]

        # Merge the overlay page onto the template page
        template_page.merge_page(overlay_pdf.pages[0])

        # Add the merged page to the output
        output.add_page(template_page)

        with open(output_path, "wb") as output_file:
            output.write(output_file)


def send_email_with_attachment(to_address, subject, body, attachment_path):
    from_address = os.getenv("EMAIL_ADDRESS")
    password = os.getenv("EMAIL_PASSWORD")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT"))

    # Setup the MIME
    msg = MIMEMultipart()
    msg['From'] = from_address
    msg['To'] = to_address
    msg['Subject'] = subject

    # Attach the body with the msg instance
    msg.attach(MIMEText(body, 'plain'))

    # Open the file as binary mode
    with open(attachment_path, "rb") as attachment:
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename= {os.path.basename(attachment_path)}",
        )
        msg.attach(part)

    # Create SMTP session for sending the mail
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()
    server.login(from_address, password)

    # Convert the message to a string and send it
    server.sendmail(from_address, to_address, msg.as_string())
    server.quit()


def main():
    excel_file = "List of Summer Students.xlsx"
    template_pdf = "Summer Certificate Oxford.pdf"
    output_folder = "output"

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    df = read_excel(excel_file)
    # print(df)
    # Create a new column for GUIDs
    df['GUID'] = [str(uuid.uuid4()) for _ in range(len(df))]
    for _, row in df.iterrows():
        try:
            text_data = {
                "Full Name": row["Name"],
            }

            temp_pdf = "temp.pdf"
            create_pdf_with_text(temp_pdf, text_data, row["GUID"])

            output_filename = f"Oxford_{text_data['Full Name'].replace(' ', '_')}.pdf"
            output_path = os.path.join(output_folder, output_filename)

            merge_pdfs(template_pdf, temp_pdf, output_path)

            # Cleanup
            os.remove(temp_pdf)

            # Send the generated PDF via email
            subject = f"Congratulation on finishing Oxford Training - {text_data['Full Name']}"
            body = f"Dear {text_data['Full Name']},\n\nPlease find attached your certificate.\n\nKindest regards,\nKAUST Academy Team"
            #send_email_with_attachment(text_data['Email'], subject, body, output_path)
            # break
        except Exception as e:
            print(f"Error in sending information: {e}")
            print(row["Name"])
    # Save the updated DataFrame with GUIDs back to Excel
    output_excel = f"output_with_guids{time.time()}.xlsx"
    df.to_excel(output_excel, index=False)

    print("PDF generation, email sending, and GUID Excel creation completed.")


if __name__ == "__main__":
    main()
