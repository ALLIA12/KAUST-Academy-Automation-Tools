import os
import pandas as pd
from PyPDF2 import PdfWriter, PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import landscape
from collections import defaultdict


def read_excel(file_path):
    return pd.read_excel(file_path)


def get_badge_page_number(title):
    title_mapping = {
        'Teacher Assistant': 0,
        'Instructor': 1,
        'Student': 2,
        'Site Manager': 3
    }
    return title_mapping.get(title, 0)


def split_name_into_lines(name, words_per_line=2):
    words = name.split()
    lines = []
    for i in range(0, len(words), words_per_line):
        line = ' '.join(words[i:i + words_per_line])
        lines.append(line)
    return lines


def create_pdf_with_text(output_path, name):
    page_width = 4.44 * inch
    page_height = 6.03 * inch

    c = canvas.Canvas(output_path, pagesize=landscape((page_width, page_height)))
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor('white')

    lines = split_name_into_lines(name)
    line_height = 15  # points
    start_y = page_height * 0.55 + (len(lines) - 1) * line_height / 2

    for i, line in enumerate(lines):
        text_width = c.stringWidth(line, "Helvetica-Bold", 12)
        x_position = (page_width - text_width) / 2
        y_position = start_y - i * line_height
        c.drawString(x_position, y_position, line.upper())

    c.save()


def merge_pdfs(template_path, overlay_path, page_number, output_path):
    template_pdf = PdfReader(template_path)
    overlay_pdf = PdfReader(overlay_path)

    output = PdfWriter()
    template_page = template_pdf.pages[page_number]
    template_page.merge_page(overlay_pdf.pages[0])
    output.add_page(template_page)

    with open(output_path, "wb") as output_file:
        output.write(output_file)


def combine_pdfs_by_venue(output_folder, venue_pdfs):
    for venue, pdf_files in venue_pdfs.items():
        if not pdf_files:
            continue

        output = PdfWriter()
        venue_filename = f"{venue.replace(' ', '_')}_combined.pdf"
        output_path = os.path.join(output_folder, venue_filename)

        for pdf_file in pdf_files:
            with open(pdf_file, 'rb') as f:
                pdf = PdfReader(f)
                output.add_page(pdf.pages[0])

        with open(output_path, 'wb') as f:
            output.write(f)

        print(f"\nCompleted venue: {venue}")
        print(f"Generated badges for:")
        for pdf_file in pdf_files:
            name = os.path.basename(pdf_file).replace('_badge.pdf', '').replace('_', ' ')
            print(f"- {name}")


def main():
    excel_file = "Badges.xlsx"
    badges_folder = "Badges"
    output_folder = "output"

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    df = read_excel(excel_file)
    venue_pdfs = defaultdict(list)

    for _, row in df.iterrows():
        try:
            name = row['Name']
            title = row['Title']
            venue = row['Venue'].strip()
            program = row['Program']

            template_pdf = os.path.join(badges_folder, f"{program}.pdf")
            temp_pdf = "temp.pdf"
            create_pdf_with_text(temp_pdf, name)

            page_number = get_badge_page_number(title)
            output_filename = f"{name.replace(' ', '_')}_badge.pdf"
            output_path = os.path.join(output_folder, output_filename)

            merge_pdfs(template_pdf, temp_pdf, page_number, output_path)
            venue_pdfs[venue].append(output_path)
            os.remove(temp_pdf)

        except Exception as e:
            print(f"Error processing badge for {name}: {e}")

    combine_pdfs_by_venue(output_folder, venue_pdfs)
    print("\nBadge generation completed.")


if __name__ == "__main__":
    main()