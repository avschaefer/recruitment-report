import streamlit as st
import json
from jinja2 import Template
import io
import datetime

# --- CONFIGURATION ---
# Columns that should NOT be treated as Technical Questions
# Add any new personal info columns here to prevent them from appearing in the Q&A section
BIO_FIELDS = [
    'ID', 'ItemInternalId', 'Start time', 'Completion time', 'Email', 'Email1', 'Name', 
    'First & Last Name', 'LinkedIn Profile URL', 'Portfolio URL', 
    'Position Type', 'Degree', 'Graduation Year', 
    'Preferred Start Date', 'Preferred Start Date1', 'Submission Time'
]

def clean_key(key):
    """
    Cleans SharePoint/Excel encoded characters from keys.
    """
    key = key.replace("_x002e_", ".")
    key = key.replace("_x003a_", ":")
    key = key.replace("_x0023_", "#")
    
    # Normalize specific fields with variable suffixes
    if "LinkedIn Profile URL" in key:
        return "LinkedIn Profile URL"
    if "Portfolio URL" in key:
        return "Portfolio URL"
    
    return key.strip()

def format_excel_date(serial):
    """
    Converts Excel serial date to readable string.
    """
    if not serial:
        return "N/A"
    try:
        # Check if it looks like a float/int
        float(serial)
        # Excel base date is usually Dec 30, 1899
        base_date = datetime.datetime(1899, 12, 30)
        delta = datetime.timedelta(days=float(serial))
        return (base_date + delta).strftime("%B %d, %Y")
    except ValueError:
        return serial

def parse_json_data(json_content):
    """
    Parses the Power Automate JSON. output.
    Expected Input: A list containing a single dictionary object (the candidate row).
    Returns: 
        - metadata (dict): Key-value pairs for bio info
        - qa_list (list): List of dicts {'question': '...', 'answer': '...'}
    """
    try:
        data = json.loads(json_content)
        
        # Power Automate 'List rows' returns a list. Get the first item.
        if isinstance(data, list) and len(data) > 0:
            candidate_data = data[0]
        elif isinstance(data, dict) and 'value' in data:
             # Handle case where full OData response is saved
            candidate_data = data['value'][0]
        else:
            return None, None

        # Separate Bio from Technical Questions
        metadata = {}
        qa_list = []

        for key, value in candidate_data.items():
            # Skip internal Excel fields like @odata.etag
            if key.startswith("@"):
                continue
            
            # Clean the key (decode characters, normalize names)
            clean_k = clean_key(key)
                
            # Check if this column is in our known Bio Fields list (case insensitive check)
            if any(bio_key.lower() == clean_k.lower() for bio_key in BIO_FIELDS):
                # Apply date formatting if applicable
                if clean_k in ['Completion time', 'Start time', 'Submission Time', 'Preferred Start Date', 'Preferred Start Date1']:
                    metadata[clean_k] = format_excel_date(value)
                else:
                    metadata[clean_k] = value
            else:
                # It's a technical question
                # Only add if the answer isn't empty/null (optional cleanup)
                if value: 
                    qa_list.append({'question': clean_k, 'answer': str(value)})

        return metadata, qa_list
    except Exception as e:
        st.error(f"JSON Parsing Error: {e}")
        return None, None

def render_report(metadata, qa_list, template_code):
    """
    Injects data into the HTML template.
    """
    template = Template(template_code)
    
    # Safe getters for metadata to prevent crashes if fields are missing
    rendered_html = template.render(
        candidate_name=metadata.get('First & Last Name', metadata.get('Name', 'Unknown Candidate')),
        position_type=metadata.get('Position Type', 'N/A'),
        email=metadata.get('Email1', metadata.get('Email', 'N/A')),
        submission_time=metadata.get('Completion time', 'N/A'),
        preferred_start_date=metadata.get('Preferred Start Date1', metadata.get('Preferred Start Date', 'N/A')),
        linkedin_url=metadata.get('LinkedIn Profile URL', '#'),
        portfolio_url=metadata.get('Portfolio URL', '#'),
        degree=metadata.get('Degree', 'N/A'),
        grad_year=metadata.get('Graduation Year', 'N/A'),
        qa_list=qa_list
    )
    return rendered_html

# --- STREAMLIT UI ---
st.set_page_config(page_title="Recruitment Report Generator", layout="wide")

st.title("Candidate Report Generator")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Technical Report")
    uploaded_tech_file = st.file_uploader("Upload Technical JSON (from Power Automate Flow)", type=['json'], key="tech")
    
    if uploaded_tech_file is not None:
        # Load the Template
        with open("templates/report_template.html", "r") as f:
            template_html = f.read()

        # Parse Data
        raw_json = uploaded_tech_file.getvalue().decode("utf-8")
        metadata, qa_list = parse_json_data(raw_json)

        if metadata:
            # Render
            final_report = render_report(metadata, qa_list, template_html)
            
            st.success("Report Generated Successfully!")
            
            # Download Button
            st.download_button(
                label="Download HTML Report",
                data=final_report,
                file_name=f"Report_{metadata.get('First & Last Name', 'Candidate')}.html",
                mime="text/html"
            )
            
            # Preview
            with st.expander("Preview Report", expanded=True):
                st.components.v1.html(final_report, height=800, scrolling=True)
        else:
            st.error("Could not parse the JSON file. Ensure it is the raw output from Power Automate.")

with col2:
    st.subheader("Behavioral Report-Coming Soon")
    st.file_uploader("Upload Behavioral JSON", type=['json'], disabled=True, key="behav")