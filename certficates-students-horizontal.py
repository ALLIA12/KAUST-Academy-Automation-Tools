import os
import smtplib
import time
import uuid
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
from PyPDF2 import PdfWriter, PdfReader
from dotenv import load_dotenv
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics import renderPDF
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import black, gray, Color
from reportlab.lib.pagesizes import landscape

# Load environment variables from .env file
load_dotenv()


def read_excel(file_path):
    return pd.read_excel(file_path)


def create_pdf_with_text(output_path, text_data, guid):
    # Set the correct page size (11.69 × 8.28 in)
    page_width = 11.69 * inch
    page_height = 8.28 * inch

    c = canvas.Canvas(output_path, pagesize=landscape((page_width, page_height)))

    # Set the font and size for the main text
    font_name = "Helvetica"
    bold_font_name = "Helvetica-Bold"
    name_font_size = 25
    specialization_font_size = 20
    thank_you_font_size = 15

    # Define the new blue color (0e53b5)
    new_blue = (14 / 255, 83 / 255, 181 / 255)  # RGB values for 0e53b5

    # Set the right offset
    right_offset = 0.5 * inch

    # Calculate vertical positions
    y_start = page_height * 0.6
    y_thank_you_1 = y_start - 0.6 * inch
    y_spec_start = y_start - 1 * inch
    y_thank_you_2 = y_start - 1.4 * inch

    # Helper function to center text with right offset
    def draw_centered_text(text, y_position, font, font_size, color=black):
        c.setFont(font, font_size)
        c.setFillColor(color)
        text_width = c.stringWidth(text, font, font_size)
        x_position = (page_width - text_width) / 2 + right_offset
        c.drawString(x_position, y_position, text)

    # Draw the name (bold and new blue)
    name_text = text_data['Full Name'].upper()
    draw_centered_text(name_text, y_start, bold_font_name, name_font_size, new_blue)

    # Draw the thank you text (1)
    thankyou_1 = "Has made significant contribution to the"
    draw_centered_text(thankyou_1, y_thank_you_1, font_name, thank_you_font_size)

    # Draw the specialization (bold and new blue)
    specialization_text = text_data['Specialization'].upper()
    draw_centered_text(specialization_text, y_spec_start, bold_font_name, specialization_font_size, new_blue)

    # Draw the thank you text (2)
    thankyou_2 = "From deep down our hearts, Thank you"
    draw_centered_text(thankyou_2, y_thank_you_2, font_name, thank_you_font_size)

    # Add GUID to the top left corner (adjusted for right offset)
    c.setFont("Helvetica", 6)  # Smaller font for GUID
    c.setFillColor(gray)
    c.drawString(0.125 * inch, page_height - 0.10 * inch, str(guid))

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
    excel_file = "input.xlsx"
    template_pdf = "KA_CERT_NAEEM_SULTAN.pdf"
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
                "Number Of Weeks": row["Number Of Weeks"]
            }

            temp_pdf = "temp.pdf"
            create_pdf_with_text(temp_pdf, text_data, row["GUID"])

            output_filename = f"{text_data['Specialization']}_{text_data['Full Name'].replace(' ', '_')}.pdf"
            output_path = os.path.join(output_folder, output_filename)

            merge_pdfs(template_pdf, temp_pdf, output_path)

            # Cleanup
            os.remove(temp_pdf)

            # Send the generated PDF via email
            subject = f"Thanks on contributing to the {text_data['Specialization']} - {text_data['Full Name']}"
            body = f"Dear {text_data['Full Name']},\n\nPlease find attached your contribution certificate on {text_data['Specialization']} .\n\nKindest regards,\nKAUST Academy Team"
            send_email_with_attachment(text_data['Email'], subject, body, output_path)
            # break
        except Exception as e:
            print(f"Error in sending information: {e}")
            print(row["Full Name"])
    # Save the updated DataFrame with GUIDs back to Excel
    output_excel = f"output_with_guids{time.time()}.xlsx"
    df.to_excel(output_excel, index=False)

    print("PDF generation, email sending, and GUID Excel creation completed.")


if __name__ == "__main__":
    main()
