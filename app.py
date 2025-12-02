import streamlit as st
import json
from jinja2 import Template
import io

# --- CONFIGURATION ---
# Columns that should NOT be treated as Technical Questions
# Add any new personal info columns here to prevent them from appearing in the Q&A section
BIO_FIELDS = [
    'ID', 'Start time', 'Completion time', 'Email', 'Name', 
    'First & Last Name', 'LinkedIn Profile URL', 'Portfolio URL', 
    'Position Type', 'Degree', 'Graduation Year', 
    'Preferred Start Date', 'Submission Time'
]

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
                
            # Check if this column is in our known Bio Fields list (case insensitive check)
            if any(bio_key.lower() == key.lower() for bio_key in BIO_FIELDS):
                metadata[key] = value
            else:
                # It's a technical question
                # Only add if the answer isn't empty/null (optional cleanup)
                if value: 
                    qa_list.append({'question': key, 'answer': str(value)})

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
        email=metadata.get('Email', 'N/A'),
        submission_time=metadata.get('Completion time', 'N/A'),
        linkedin_url=metadata.get('LinkedIn Profile URL', '#'),
        portfolio_url=metadata.get('Portfolio URL', '#'),
        degree=metadata.get('Degree', 'N/A'),
        grad_year=metadata.get('Graduation Year', 'N/A'),
        qa_list=qa_list
    )
    return rendered_html

# --- STREAMLIT UI ---
st.set_page_config(page_title="Recruitment Report Generator", layout="wide")

st.title("📄 Candidate Report Generator")
st.markdown("Convert raw Power Automate JSON data into professional PDF-ready HTML reports.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Technical Report")
    uploaded_tech_file = st.file_uploader("Upload Technical JSON (from Automation)", type=['json'], key="tech")
    
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
                label="📥 Download Styled HTML Report",
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
    st.subheader("2. Behavioral Report")
    st.info("Module coming soon.")
    st.file_uploader("Upload Behavioral JSON", type=['json'], disabled=True, key="behav")