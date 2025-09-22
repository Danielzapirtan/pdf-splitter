import PyPDF2
import os
from pathlib import Path

def get_book_page_mapping(pdf_reader):
    """
    Create a mapping from book page numbers to PDF page indices.
    This is a simple implementation - you may need to customize this based on your PDF structure.
    """
    total_pdf_pages = len(pdf_reader.pages)
    
    print(f"Total PDF pages: {total_pdf_pages}")
    print("\nPage mapping options:")
    print("1. Book pages start from page 1 (1:1 mapping)")
    print("2. Custom offset (e.g., book page 1 starts at PDF page 5)")
    print("3. Manual mapping for complex books")
    
    choice = input("Choose mapping option (1, 2, or 3): ").strip()
    
    if choice == "1":
        # Simple 1:1 mapping
        return {i+1: i for i in range(total_pdf_pages)}
    
    elif choice == "2":
        # Offset mapping
        try:
            offset = int(input("Enter PDF page number where book page 1 starts: ")) - 1
            if offset < 0 or offset >= total_pdf_pages:
                print("Invalid offset. Using 1:1 mapping.")
                return {i+1: i for i in range(total_pdf_pages)}
            
            mapping = {}
            for i in range(total_pdf_pages - offset):
                mapping[i + 1] = i + offset
            return mapping
        except ValueError:
            print("Invalid input. Using 1:1 mapping.")
            return {i+1: i for i in range(total_pdf_pages)}
    
    elif choice == "3":
        # Manual mapping (simplified - you can expand this)
        print("Manual mapping not implemented in this version. Using 1:1 mapping.")
        return {i+1: i for i in range(total_pdf_pages)}
    
    else:
        print("Invalid choice. Using 1:1 mapping.")
        return {i+1: i for i in range(total_pdf_pages)}

def extract_pages_to_single_pdf(input_path, output_path, book_pages):
    """
    Extract specified book pages and concatenate them into a single PDF.
    Args:
        input_path (str): Path to input PDF file
        output_path (str): Path for output PDF file
        book_pages (list): List of book page numbers to extract
    """
    try:
        # Open the PDF file
        with open(input_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Get page mapping
            page_mapping = get_book_page_mapping(pdf_reader)
            
            # Validate book pages
            invalid_pages = []
            valid_pdf_indices = []
            
            for book_page in book_pages:
                if book_page not in page_mapping:
                    invalid_pages.append(book_page)
                else:
                    valid_pdf_indices.append(page_mapping[book_page])
            
            if invalid_pages:
                print(f"Warning: Invalid book pages: {invalid_pages}")
                if not valid_pdf_indices:
                    print("No valid pages to extract.")
                    return False
            
            # Create output PDF with selected pages
            pdf_writer = PyPDF2.PdfWriter()
            
            print(f"\nExtracting book pages: {sorted([p for p in book_pages if p in page_mapping])}")
            for pdf_index in sorted(valid_pdf_indices):
                pdf_writer.add_page(pdf_reader.pages[pdf_index])
                book_page = next(bp for bp, pi in page_mapping.items() if pi == pdf_index)
                print(f"Added book page {book_page} (PDF page {pdf_index + 1})")
            
            # Write the output PDF
            with open(output_path, 'wb') as output_file:
                pdf_writer.write(output_file)
            
            print(f"\nSuccessfully created: {output_path}")
            return True
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found.")
        return False
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False

def split_pdf_individual_pages(input_path, output_dir, book_pages=None):
    """
    Split a PDF into individual pages (original functionality with book page numbering).
    Args:
        input_path (str): Path to input PDF file
        output_dir (str): Directory to save output PDFs
        book_pages (list or None): List of book page numbers to split, None for all pages
    """
    try:
        # Ensure output directory exists
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Open the PDF file
        with open(input_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Get page mapping
            page_mapping = get_book_page_mapping(pdf_reader)
            
            if book_pages is None:
                book_pages = list(page_mapping.keys())
            
            # Validate book pages
            invalid_pages = []
            for book_page in book_pages:
                if book_page not in page_mapping:
                    invalid_pages.append(book_page)
            
            if invalid_pages:
                print(f"Error: Invalid book pages: {invalid_pages}")
                valid_pages = [p for p in book_pages if p in page_mapping]
                if not valid_pages:
                    return False
                book_pages = valid_pages
            
            # Split pages
            for book_page in book_pages:
                pdf_writer = PyPDF2.PdfWriter()
                pdf_index = page_mapping[book_page]
                pdf_writer.add_page(pdf_reader.pages[pdf_index])
                
                output_path = os.path.join(output_dir, f'book_page_{book_page}.pdf')
                with open(output_path, 'wb') as output_file:
                    pdf_writer.write(output_file)
                print(f"Created: {output_path} (book page {book_page})")

        print("PDF splitting completed successfully!")
        return True
        
    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found.")
        return False
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return False

def parse_page_numbers(page_input):
    """Parse page numbers from user input (supports ranges and comma-separated values)."""
    pages = []
    
    for part in page_input.split(','):
        part = part.strip()
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                if start <= end:
                    pages.extend(range(start, end + 1))
                else:
                    print(f"Warning: Invalid range {part} (start > end)")
            except ValueError:
                print(f"Warning: Invalid page range format: {part}")
        else:
            try:
                pages.append(int(part))
            except ValueError:
                print(f"Warning: Invalid page number: {part}")
    
    return sorted(list(set(pages)))  # Remove duplicates and sort

def main():
    print("=== PDF Page Extractor ===")
    print("This program extracts specific book pages from a PDF file.")
    
    while True:
        # Get input PDF path
        input_path = input("\nEnter the path to the PDF file (or 'q' to quit): ").strip()
        if input_path.lower() == 'q':
            print("Exiting program.")
            break
        
        if not os.path.isfile(input_path):
            print("Error: File does not exist. Please try again.")
            continue
        
        # Choose operation mode
        print("\nOperation options:")
        print("1. Extract pages to individual PDF files")
        print("2. Extract pages to a single concatenated PDF")
        mode = input("Choose an option (1 or 2): ").strip()
        
        if mode not in ["1", "2"]:
            print("Invalid option. Please try again.")
            continue
        
        # Choose page selection
        print("\nPage selection:")
        print("1. Extract all pages")
        print("2. Extract specific book pages")
        page_mode = input("Choose an option (1 or 2): ").strip()
        
        book_pages = None
        if page_mode == "2":
            page_input = input("Enter book page numbers (e.g., 1,3,5 or 1-3,5): ").strip()
            book_pages = parse_page_numbers(page_input)
            if not book_pages:
                print("No valid pages specified. Please try again.")
                continue
            print(f"Selected book pages: {book_pages}")
        
        # Execute based on mode
        if mode == "1":
            # Individual PDF files
            default_output = os.path.join(os.path.dirname(input_path), "extracted_pages")
            output_dir = input(f"Enter output directory (default: {default_output}): ").strip()
            if not output_dir:
                output_dir = default_output
            
            split_pdf_individual_pages(input_path, output_dir, book_pages)
            
        elif mode == "2":
            # Single concatenated PDF
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            default_output = os.path.join(os.path.dirname(input_path), f"{base_name}_extracted.pdf")
            output_path = input(f"Enter output file path (default: {default_output}): ").strip()
            if not output_path:
                output_path = default_output
            
            if book_pages is None:
                print("Cannot concatenate all pages without specifying which pages to extract.")
                continue
                
            extract_pages_to_single_pdf(input_path, output_path, book_pages)

if __name__ == "__main__":
    # Check if PyPDF2 is installed
    try:
        import PyPDF2
    except ImportError:
        print("Error: PyPDF2 library is not installed.")
        print("Please install it using: pip install PyPDF2")
        exit(1)
    
    main()