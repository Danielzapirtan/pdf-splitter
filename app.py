import PyPDF2
import os
from pathlib import Path

def split_pdf(input_path, output_dir, pages=None):
    """
    Split a PDF into individual pages or specified page ranges.
    Args:
        input_path (str): Path to input PDF file
        output_dir (str): Directory to save output PDFs
        pages (list or None): List of page numbers to split (1-based indexing), None for all pages
    """
    try:
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Open the PDF file
        with open(input_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            total_pages = len(pdf_reader.pages)

            if pages is None:
                pages = range(1, total_pages + 1)

            # Validate page numbers
            for page in pages:
                if page < 1 or page > total_pages:
                    print(f"Error: Page {page} is out of range (1-{total_pages})")
                    return

            # Split pages
            for page_num in pages:
                pdf_writer = PyPDF2.PdfWriter()
                pdf_writer.add_page(pdf_reader.pages[page_num - 1])  # Convert to 0-based indexing
                
                output_path = os.path.join(output_dir, f'page_{page_num}.pdf')
                with open(output_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
                print(f"Created: {output_path}")

        print("PDF splitting completed successfully!")
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

def main():
    print("=== PDF Splitter ===")
    print("This program splits a PDF file into individual pages or specific page ranges.")
    
    while True:
        # Get input PDF path
        input_path = input("\nEnter the path to the PDF file (or 'q' to quit): ").strip()
        if input_path.lower() == 'q':
            print("Exiting program.")
            break
        
        if not os.path.isfile(input_path):
            print("Error: File does not exist. Please try again.")
            continue
        
        # Get output directory
        default_output = os.path.join(os.path.dirname(input_path), "split_pdf_output")
        output_dir = input(f"Enter output directory (default: {default_output}): ").strip()
        if not output_dir:
            output_dir = default_output
        
        # Choose splitting mode
        print("\nSplitting options:")
        print("1. Split all pages individually")
        print("2. Split specific pages")
        mode = input("Choose an option (1 or 2): ").strip()
        
        pages = None
        if mode == "2":
            page_input = input("Enter page numbers (e.g., 1,3,5 or 1-3,5): ").strip()
            pages = []
            
            # Parse page numbers (support comma-separated and ranges)
            for part in page_input.split(','):
                part = part.strip()
                if '-' in part:
                    try:
                        start, end = map(int, part.split('-'))
                        pages.extend(range(start, end + 1))
                    except ValueError:
                        print("Error: Invalid page range format.")
                        continue
                else:
                    try:
                        pages.append(int(part))
                    except ValueError:
                        print("Error: Invalid page number.")
                        continue
        
        # Perform the splitting
        split_pdf(input_path, output_dir, pages if mode == "2" else None)

if __name__ == "__main__":
    # Check if PyPDF2 is installed
    try:
        import PyPDF2
    except ImportError:
        print("Error: PyPDF2 library is not installed.")
        print("Please install it using: pip install PyPDF2")
        exit(1)
    
    main()
