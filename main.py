import os
from dotenv import load_dotenv
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import json
from datetime import datetime

# Load environment variables from .env file
load_dotenv()


class DocumentAnalyzer:
    def __init__(self):
        """Initialize the Document Intelligence client using environment variables"""
        endpoint = os.getenv('DOC_INTELLIGENCE_ENDPOINT')
        api_key = os.getenv('DOC_INTELLIGENCE_KEY')

        if not endpoint or not api_key:
            raise ValueError("Missing environment variables. Please check your .env file.")

        self.client = DocumentAnalysisClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(api_key)
        )
        print(f"Connected to Azure Document Intelligence at: {endpoint}")

    def analyze_document_from_file(self, file_path, model_id="prebuilt-document"):
        """Analyze document from local file"""
        try:
            print(f"Analyzing document: {file_path}")
            print(f"Using model: {model_id}")

            with open(file_path, "rb") as document:
                poller = self.client.begin_analyze_document(
                    model_id=model_id,
                    document=document
                )
                result = poller.result()
                print("Analysis completed successfully")
                return result

        except FileNotFoundError:
            print(f"File not found: {file_path}")
            return None
        except Exception as e:
            print(f"Error analyzing document: {str(e)}")
            return None

    def extract_and_display_results(self, result, model_used, file_path):
        """Extract and display all document information"""
        if not result:
            print("No results to display")
            return None

        print("\n" + "=" * 40)
        print("RESULTS")
        print("=" * 40)

        print(f"\nDocument: {os.path.basename(file_path)}")
        print(f"Model Used: {model_used}")
        print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        extracted_data = {
            'file_name': os.path.basename(file_path),
            'model_used': model_used,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'extracted_fields': [],
            'tables': [],
            'full_text': ""
        }

        # Extract fields with confidence scores
        print("\n" + "=" * 40)
        print("EXTRACTED FIELDS")
        print("=" * 40)

        if hasattr(result, 'documents') and result.documents:
            for doc_idx, document in enumerate(result.documents):
                print(f"\nDocument {doc_idx + 1}:")
                if hasattr(document, 'doc_type'):
                    print(f"Document Type: {document.doc_type}")

                if hasattr(document, 'fields') and document.fields:
                    for field_name, field_value in document.fields.items():
                        confidence = field_value.confidence if hasattr(field_value, 'confidence') else 0
                        value = field_value.value if hasattr(field_value, 'value') else field_value.content

                        print(f"  • {field_name}: {value} (Confidence: {confidence:.2%})")

                        extracted_data['extracted_fields'].append({
                            'field_name': field_name,
                            'value': str(value),
                            'confidence': confidence
                        })
        else:
            print("No structured fields found")

        # Extract table data
        print("\n" + "=" * 40)
        print("TABLE DATA")
        print("=" * 40)

        if hasattr(result, 'tables') and result.tables:
            for table_idx, table in enumerate(result.tables):
                print(f"\nTable {table_idx + 1}:")
                print(f"Dimensions: {table.row_count} rows × {table.column_count} columns")

                table_data = []
                table_matrix = [["" for _ in range(table.column_count)] for _ in range(table.row_count)]

                for cell in table.cells:
                    row_idx = cell.row_index
                    col_idx = cell.column_index
                    content = cell.content
                    confidence = cell.confidence if hasattr(cell, 'confidence') else 0

                    table_matrix[row_idx][col_idx] = f"{content} ({confidence:.1%})"
                    table_data.append({
                        'row': row_idx,
                        'column': col_idx,
                        'content': content,
                        'confidence': confidence
                    })

                for row_idx, row in enumerate(table_matrix):
                    print(f"  Row {row_idx}: {' | '.join(row)}")

                extracted_data['tables'].append({
                    'table_index': table_idx,
                    'row_count': table.row_count,
                    'column_count': table.column_count,
                    'cells': table_data
                })
        else:
            print("No tables found in the document")

        # Extract full text content
        print("\n" + "=" * 40)
        print("FULL TEXT CONTENT")
        print("=" * 40)

        full_text = ""
        if hasattr(result, 'content'):
            full_text = result.content
            print(f"\n{full_text}")
        elif hasattr(result, 'pages'):
            for page_idx, page in enumerate(result.pages):
                print(f"\n--- Page {page_idx + 1} ---")
                if hasattr(page, 'lines'):
                    page_text = "\n".join([line.content for line in page.lines])
                    full_text += page_text + "\n"
                    print(page_text)

        extracted_data['full_text'] = full_text
        return extracted_data

    def save_text_to_file(self, text_content, original_filename):
        """Save extracted text to a local file (content only, no headers)"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(original_filename)[0]
        output_filename = f"extracted_{base_name}_{timestamp}.txt"

        try:
            with open(output_filename, 'w', encoding='utf-8') as file:
                # Save only the raw extracted content
                file.write(text_content)

            print(f"\nText content saved to: {output_filename}")
            return output_filename
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            return None


def main():
    """Main function to run the document analysis with recurring input"""
    print()
    print("=" * 40)
    print("Azure Document Intelligence Analyzer")
    print("=" * 40)
    print()

    try:
        # Initialize analyzer once (credentials loaded from .env)
        analyzer = DocumentAnalyzer()

        # Available models
        models = {
            # General-purpose model for basic text extraction and key-value pairs
            # Use for: contracts, reports, letters, unknown document types, general PDFs
            # Best when: Document structure is simple or unknown
            "1": "prebuilt-document",

            # Advanced layout analysis with table and structure detection
            # Use for: financial reports, multi-column documents, complex tables, research papers
            # Best when: Document has tables, charts, or complex formatting that needs preservation
            "2": "prebuilt-layout",

            # Specialized model for financial documents with invoice-specific fields
            # Use for: invoices, bills, receipts, purchase orders, utility statements
            # Best when: Need to extract vendor info, line items, totals, dates, tax amounts
            "3": "prebuilt-invoice"
        }

        # Main analysis loop
        while True:
            print("\nAvailable Models:")
            for key, model in models.items():
                print(f"  {key}. {model}")

            model_choice = input("\nSelect model (1-3) [default: 1]: ").strip() or "1"
            selected_model = models.get(model_choice, "prebuilt-document")

            # Get local file path
            file_path = input("\nEnter local file path: ").strip()
            if not file_path:
                print("No file path provided")
                continue

            # Check if file exists
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                continue

            # Analyze document
            result = analyzer.analyze_document_from_file(file_path, selected_model)

            if result:
                extracted_data = analyzer.extract_and_display_results(result, selected_model, file_path)

                if extracted_data and extracted_data['full_text']:
                    # Save extracted text
                    output_file = analyzer.save_text_to_file(
                        extracted_data['full_text'],
                        os.path.basename(file_path)
                    )

                    # Option to save structured data as JSON
                    save_json = input("\nSave structured data as JSON? (y/n): ").strip().lower()
                    if save_json == 'y':
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        base_name = os.path.splitext(os.path.basename(file_path))[0]
                        json_filename = f"analysis_{base_name}_{timestamp}.json"

                        try:
                            with open(json_filename, 'w', encoding='utf-8') as json_file:
                                json.dump(extracted_data, json_file, indent=2, ensure_ascii=False)
                            print(f"Structured data saved to: {json_filename}")
                        except Exception as e:
                            print(f"Error saving JSON: {str(e)}")
            else:
                print("Failed to analyze document")

            # Ask if user wants to continue
            print("\n" + "=" * 50)
            continue_choice = input("Analyze another document? (y/n): ").strip().lower()

            if continue_choice not in ['y', 'yes']:
                print("\nThank you for using Azure Document Intelligence Analyzer!")
                print("Goodbye!")
                break

    except ValueError as e:
        print(f"Configuration error: {str(e)}")
        print("Please check your .env file configuration")
    except KeyboardInterrupt:
        print("\n\n⚠Process interrupted by user")
        print("Goodbye!")
    except Exception as e:
        print(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    main()