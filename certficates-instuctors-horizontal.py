import os
import time
import uuid
from datetime import datetime
from reportlab.lib.pagesizes import landscape
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
    # Set the correct page size (11.69 × 8.26 in)
    page_width = 11.69 * inch
    page_height = 8.26 * inch
    c = canvas.Canvas(output_path, pagesize=landscape((page_width, page_height)))

    # Set the font and size for the main text
    font_name = "Helvetica"
    name_font_size = 25
    main_font_size = 14

    # Calculate vertical positions
    y_start = page_height * 0.52  # Adjusted starting position for the name
    line_padding = 0.25 * inch  # Padding between lines

    # Draw the name
    c.setFont(font_name + "-Bold", name_font_size)
    c.setFillColor(black)
    name_text = text_data['Full Name']
    name_width = pdfmetrics.stringWidth(name_text, font_name + "-Bold", name_font_size)
    c.drawString((page_width - name_width) / 2, y_start, name_text)

    # Draw the main content
    c.setFont(font_name, main_font_size)
    y_position = y_start - name_font_size - line_padding

    date_range = format_date_range(text_data['Start Date'], text_data['End Date'])
    main_text = [
        "has significantly contributed to the success of the KAUST Academy Specialization",
        f"Program by delivering Bioinformatics courses, {date_range}.",
        "Your commitment and expertise to enhancing our training programs are highly valued.",
        "We extend our heartfelt gratitude and appreciation for your contribution."
    ]

    for line in main_text:
        text_width = pdfmetrics.stringWidth(line, font_name, main_font_size)
        c.drawString((page_width - text_width) / 2, y_position, line)
        y_position -= main_font_size + (line_padding / 2)  # Reduced line spacing

    # Add GUID to the top left corner
    c.setFont("Helvetica", 8)  # Smaller font for GUID
    c.setFillColor(gray)
    c.drawString(0.5 * inch, page_height - 0.5 * inch, str(guid))

    c.save()


def format_single_date(date_input):
    if isinstance(date_input, str):
        date = datetime.strptime(date_input, '%Y-%m-%d %H:%M:%S')
    elif isinstance(date_input, pd.Timestamp):
        date = date_input.to_pydatetime()
    else:
        raise ValueError("Unsupported date format")
    return date


def format_date_range(start_date, end_date):
    start = format_single_date(start_date)
    end = format_single_date(end_date)

    if start.year == end.year:
        return f"from {start.strftime('%B %d')} to {end.strftime('%B %d')} {end.year}"
    else:
        return f"from {start.strftime('%B %d %Y')} to {end.strftime('%B %d %Y')}"

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
    excel_file = "input.xlsx"
    template_pdf = "KAUST_Academy_Certificate.pdf"
    output_folder = "output"

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    df = read_excel(excel_file)
    # Create a new column for GUIDs
    df['GUID'] = [str(uuid.uuid4()) for _ in range(len(df))]
    for _, row in df.iterrows():
        try:
            text_data = {
                "Full Name": row["Full Name"],
                "Specialization": row["Specialization"],
                "Email": row["Email"],
                "Start Date": row["Start Date"],
                "End Date": row["End Date"],
            }

            temp_pdf = "temp.pdf"
            create_pdf_with_text(temp_pdf, text_data, row["GUID"])

            output_filename = f"{text_data['Specialization']}_{text_data['Full Name'].replace(' ', '_')}.pdf"
            output_path = os.path.join(output_folder, output_filename)

            merge_pdfs(template_pdf, temp_pdf, output_path)

            # Cleanup
            os.remove(temp_pdf)

            # Send the generated PDF via email
            subject = f"Certificate of Contribution - KAUST Academy Specialization Program"

            body = f"""Dear {text_data['Full Name']},

            We are pleased to present you with the attached certificate in recognition of your significant contribution to the KAUST Academy Specialization Program.

            Your dedication in delivering Bioinformatics courses from {format_date_range(text_data['Start Date'], text_data['End Date'])} has been instrumental to the success of our program.

            We highly value your commitment and expertise in enhancing our training programs. Please accept our heartfelt gratitude and appreciation for your contribution.

            Thank you for your outstanding service.

            Best regards,
            KAUST Academy Team"""
            send_email_with_attachment(text_data['Email'], subject, body, output_path)
            exit()
            break
        except Exception as e:
            print(f"Error in sending information: {e}")
            print(row["Full Name"])
    # Save the updated DataFrame with GUIDs back to Excel
    output_excel = f"output_with_guids{time.time()}.xlsx"
    df.to_excel(output_excel, index=False)

    print("PDF generation, email sending, and GUID Excel creation completed.")


if __name__ == "__main__":
    main()
