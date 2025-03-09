import streamlit as st
from googlesearch import search
import json
import anthropic
from anthropic.types.text_block import TextBlock as TB
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("ANTHROPIC_API_KEY")


model = "claude-3-5-sonnet-20241022"
client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key=API_KEY,
    )

class TextBlock:
    def __init__(self, text):
        self.text = text  

def NAICS_DESC(client, model, business_data):
    try:
        # Define the JSON response template separately
        json_template = '''{
    "company_name": "",
    "naics_verification": {
        "primary_code": "",
        "primary_description": "",
        "secondary_code": "",
        "secondary_description": "",
        "reason": ""
    },
    "company_description": "",
    "property_type": "",
    "underwriter_notes": "",
    "recommendation": ""
}'''

        message = client.messages.create(
            model=model,
            max_tokens=8192,
            temperature=0,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"""You are an expert underwriter tasked with analyzing a business based on its name and location.
                            Your goal is to gather and interpret information that will help assess the business's risk profile. 
                            Here's the company information you need to analyze:

Company Name: {business_data['business_name']}
Company Location: {business_data['location']}
Google search: {business_data['urls']}

Your task is to conduct a thorough analysis following these steps:

1. Perform a web search using the provided company name and location.

2. Based on the information you find, analyze the following:
   a. Determine if the address is a commercial property or an individual house.
   b. Identify the specific business associated with this address.
   c. Classify the industry and determine the appropriate NAICS codes.
   d. Extract a concise company description from the website or search results.

3. Compile your findings and present them in a structured format that will assist in underwriting decisions.

<underwriting_analysis>
[Analysis will go here]
</underwriting_analysis>

{json_template}"""
                        }
                    ]
                },
                {
                    "role": "assistant",
                    "content": [
                        {
                            "type": "text",
                            "text": "<underwriting_analysis>"
                        }
                    ]
                }
            ]
        )
        return message.content
    except Exception as e:
        print(f"Error generating information: {e}")
        return None
    
# Extract email content from the TextBlock
def extract_content(text_block):
    if isinstance(text_block, TB):  # Ensure it's a TextBlock
        raw_text = text_block.text
        return raw_text

# Replace placeholders like {{COMPANY_NAME}} with real values,
# because the SDK does not support variables.


# Initialize session state for storing business data
if "all_business_data" not in st.session_state:
    st.session_state.all_business_data = []  # Stores all businesses as a JSON list

# Initialize session state for inputs and URLs
if "business_name" not in st.session_state:
    st.session_state.business_name = ""

if "location" not in st.session_state:
    st.session_state.location = ""

if "urls" not in st.session_state:
    st.session_state.urls = []

# Function to perform Google search
def search_business(business_name, location):
    try:
        query = f"{business_name} {location} business"
        search_results = list(search(query, num_results=8))
        return search_results
    except Exception as e:
        return [f"An error occurred: {str(e)}"]

def format_underwriter_output(output):
    output = extract_content(output[0])
    parts = output.split('</underwriting_analysis>')
    analysis_text = parts[0].split('\n', 1)[1]  # Remove the first empty line
    json_text = parts[1].strip()
     
    return analysis_text, json_text

def display_in_streamlit(output):
    try:

        analysis, json_text = format_underwriter_output(output)
        
        # Display Analysis Section
        st.header("Underwriting Analysis")
        st.markdown(analysis)
        
        # Display JSON Section
        st.header("Structured Assessment")
        try:
            json_obj = json.loads(json_text)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Company Information")
                st.write(f"**Company Name:** {json_obj['company_name']}")
                st.write(f"**Property Type:** {json_obj['property_type']}")
                
                st.subheader("Business Description")
                st.write(json_obj['company_description'])
            
            with col2:
                st.subheader("NAICS Classification")
                naics = json_obj['naics_verification']
                st.write(f"**Primary Code:** {naics['primary_code']}")
                st.write(f"**Primary Description:** {naics['primary_description']}")
                st.write(f"**Secondary Code:** {naics['secondary_code']}")
                st.write(f"**Secondary Description:** {naics['secondary_description']}")
                st.write(f"**Reason:** {naics['reason']}")
            
            st.subheader("Underwriter Notes")
            notes = json_obj['underwriter_notes'].split('\n')
            for note in notes:
                st.write(note)
            
            st.subheader("Recommendation")
            st.warning(json_obj['recommendation'])
            
        except json.JSONDecodeError as e:
            st.error(f"Error parsing JSON data: {e}")
            st.code(json_text)  # Display the raw JSON text for debugging
            
    except Exception as e:
        st.error(f"Error processing output: {e}")
        # Debug information
        st.write("Output type:", type(output))
        st.write("Output structure:", dir(output))
        st.code(str(output))  # Display the raw output for debugging


# Streamlit UI
st.title("🔍 Business Search & JSON Storage")

# User Input Fields
new_business_name = st.text_input("Enter Business Name:", placeholder="e.g., Spracht Inc")
new_location = st.text_input("Enter Location:", placeholder="e.g., Palo Alto, CA")

# Check if the user entered a new business name or location, and reset URLs
if new_business_name != st.session_state.business_name or new_location != st.session_state.location:
    st.session_state.business_name = new_business_name
    st.session_state.location = new_location
    st.session_state.urls = []  # Reset URLs when new input is detected

# Search Button
if st.button("Search Business"):
    if st.session_state.business_name and st.session_state.location:
        st.write(f"### 🔎 Searching for: {st.session_state.business_name} in {st.session_state.location}")

        # Get search results
        results = search_business(st.session_state.business_name, st.session_state.location)

        if isinstance(results, list):
            st.session_state.urls = results  # Store new URLs in session state
        else:
            st.error("No results found. Try a different search.")

# Editable URL List
st.write("### 📝 Edit or Add URLs")
edited_urls = st.text_area("Modify URLs (one per line):", value="\n".join(st.session_state.urls), height=150)

# Save Updated URLs
if st.button("Save Changes"):
    st.session_state.urls = edited_urls.split("\n")
    st.success("✅ URLs Updated Successfully!")

# Store All Data in One JSON Variable
if st.button("Send data to AI"):
    if st.session_state.business_name and st.session_state.location and st.session_state.urls:
        business_data = {
            "business_name": st.session_state.business_name,
            "location": st.session_state.location,
            "urls": st.session_state.urls
        }
        st.session_state.all_business_data.append(business_data)
        st.success("✅ Business Data sent Successfully!")
        output_desc = NAICS_DESC(client, model, business_data)
        if output_desc is not None:
            display_in_streamlit(output_desc)
        else:
            st.error("Failed to generate analysis. Please check the input data and try again.")   

       

# Reset All Stored Data
if st.button("Reset Data"):
    st.session_state.business_name = ""
    st.session_state.location = ""
    st.session_state.urls = []
    st.session_state.all_business_data = []
    st.success("🔄 Data Reset Successfully! Enter new details.")


# Footer
st.markdown("---")

