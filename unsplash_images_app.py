import streamlit as st
import requests
from dotenv import load_dotenv
import os
import base64
import urllib.parse




load_dotenv()
api_key = os.getenv("GETTY_API_KEY")  
client_secret = os.getenv("GETTY_CLIENT_SECRET")  
unsplash_access_key = os.getenv("UNSPLASH_ACCESS_KEY")
unsplash_secret_key = os.getenv("UNSPLASH_SECRET_KEY")

# Global variable to store access token
access_token = None
token_expiry = None

def get_access_token():
    """Get OAuth2 access token for Getty Images API"""
    global access_token, token_expiry
    
    # Check if we have a valid token
    if access_token and token_expiry:
        import time
        if time.time() < token_expiry:
            return access_token
    
    url = "https://authentication.gettyimages.com/oauth2/token"
    
    # Prepare credentials for basic auth
    credentials = f"{api_key}:{client_secret}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "client_credentials"
    }
    
    try:
        response = requests.post(url, headers=headers, data=data)
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            expires_in = token_data.get("expires_in", 1800)
            
            import time
            token_expiry = time.time() + expires_in - 60  # Refresh 1 minute before expiry
            
            return access_token
        else:
            st.error(f"Failed to get access token: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error getting access token: {str(e)}")
        return None

# Fetch images from Getty and Unsplash together
def fetch_images(query, page=1, per_page=100, orientation='landscape'):
    """Fetch images from Getty and Unsplash for a query."""
    # Fetch Getty images
    token = get_access_token()
    if not token:
        return []

    # Getty API request
    getty_url = "https://api.gettyimages.com/v3/search/images/creative"
    headers = {
        "Api-Key": api_key,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    params = {
        "phrase": query,
        "page": page,
        "page_size": per_page,
        "fields": "id,title,thumb,preview,comp,display_sizes,max_dimensions"
    }

    getty_response = requests.get(getty_url, headers=headers, params=params)
    getty_images = []
    if getty_response.status_code == 200:
        getty_images = getty_response.json().get("images", [])
    else:
        st.error(f"Getty Images API error {getty_response.status_code}: {getty_response.text}")

    # Fetch Unsplash images
    unsplash_url = "https://api.unsplash.com/search/photos"
    unsplash_headers = {
        "Authorization": f"Client-ID {unsplash_access_key}"
    }

    encoded_query = urllib.parse.quote_plus(query)

    if orientation == 'portrait':
        unsplash_params = {
            "query": f"{encoded_query} ",
            "page": page,  # Include page number for pagination
            "per_page": per_page,  # Number of images per page
            # Do not pass 'orientation' to Unsplash for city search, we'll filter later
        }
    else:
        # For the attraction section, only fetch landscape
        unsplash_params = {
            "query": f"{encoded_query} ",
            "page": page,
            "per_page": per_page,
            "orientation": orientation  # Apply landscape filter for attractions
        }

    unsplash_response = requests.get(unsplash_url, headers=unsplash_headers, params=unsplash_params)
    unsplash_images = []
    if unsplash_response.status_code == 200:
        unsplash_images = unsplash_response.json().get("results", [])
    else:
        st.error(f"Unsplash API error {unsplash_response.status_code}: {unsplash_response.text}")

    # Combine Getty and Unsplash images
    combined_images = getty_images + unsplash_images
    return combined_images

def filter_images(images):
    filtered_images = []
    # Add keywords and their plural forms or related terms
    exclude_keywords = ['person', 'people', 'man', 'woman', 'boy', 'girl', 'logo', 'brand', 'advertisement', 'face', 'group']

    for image in images:
        description = image.get('alt_description', '').lower()  # Convert description to lowercase
        tags = [tag['title'].lower() for tag in image.get('tags', [])]  # Convert tags to lowercase

        # Check if any exclusion keyword exists in the description or tags
        if not any(keyword in description or keyword in tags for keyword in exclude_keywords):
            filtered_images.append(image)

    return filtered_images


# Fetch multiple pages of images (adjusted)
def fetch_many_images(query, max_pages=5, per_page=100, orientation='landscape'):
    """Fetch multiple pages of results from Getty and Unsplash for a query."""
    all_images = []
    for page in range(1, max_pages + 1):
        images = fetch_images(query, page=page, per_page=per_page, orientation=orientation)
        if not images:
            break
        all_images.extend(images)
        if len(images) < per_page:
            break  # No more pages
    return all_images

# Function to get the thumbnail URL (for Getty and Unsplash)
def get_thumbnail_url(img_data):
    """Get the thumbnail URL for Getty and Unsplash images."""
    thumb_url = None
    # For Getty images
    if 'display_sizes' in img_data:
        for size in img_data["display_sizes"]:
            if size["name"] == "thumb":
                thumb_url = size["uri"]
                break
    # For Unsplash images
    elif 'urls' in img_data:
        thumb_url = img_data["urls"].get("thumb")
    
    return thumb_url

# Function to get the largest image URL (for Getty and Unsplash)
def get_largest_image_url(img_data):
    """Get the largest image URL for Getty and Unsplash images."""
    if "display_sizes" in img_data:
        # Prefer 'comp', then 'preview', then 'thumb'
        preferred_order = ["comp", "preview", "thumb"]
        for name in preferred_order:
            for size in img_data["display_sizes"]:
                if size.get("name") == name:
                    return size["uri"]
        # Fallback: largest by area
        sizes = sorted(
            img_data["display_sizes"],
            key=lambda s: s.get("width", 0) * s.get("height", 0),
            reverse=True
        )
        if sizes:
            return sizes[0]["uri"]
    # For Unsplash images
    elif "urls" in img_data:
        return img_data["urls"].get("full")
    
    return None

# Function to get the photographer/source (for Getty and Unsplash)
def get_image_source(img_data):
    """Get the image description and source for Getty and Unsplash images."""
    image_description = ""
    source = ""

    if 'title' in img_data:  # Getty Images
        image_description = img_data.get('title', 'No description available')
        source = "Getty Images"
    elif 'user' in img_data:  # Unsplash Images
        image_description = img_data.get('alt_description', 'No description available')
        photographer_name = img_data['user']['name']
        photographer_profile = img_data['user']['links']['html']
        source = f"Photo by [@{photographer_name}]({photographer_profile}) on Unsplash"
    
    return f"Image: {image_description}\n\nSource: {source}"


def filter_portrait(images, orientation='portrait'):
    """Filter portrait images from Getty and Unsplash."""
    portrait_images = []
    for img in images:
        # For Getty images
        if 'max_dimensions' in img:
            height = img['max_dimensions'].get('height', 0)
            width = img['max_dimensions'].get('width', 0)
        # For Unsplash images
        else:
            height = img.get('height', 0)
            width = img.get('width', 0)
        
        # If the height is greater than the width, it's portrait
        if height > width:
            portrait_images.append(img)
    
    return portrait_images

def filter_landscape(images, orientation='landscape'):
    """Filter landscape images from Getty and Unsplash."""
    landscape_images = []
    for img in images:
        # For Getty images (check 'max_dimensions' for width and height)
        if 'max_dimensions' in img:
            height = img['max_dimensions'].get('height', 0)
            width = img['max_dimensions'].get('width', 0)
        # For Unsplash images (directly check 'height' and 'width' in the image object)
        elif 'height' in img and 'width' in img:
            height = img['height']
            width = img['width']
        else:
            # If neither Getty nor Unsplash image structure, skip
            continue
        
        # If width > height, it's considered landscape
        if width > height:
            landscape_images.append(img)
    
    return landscape_images



def main():
    st.set_page_config(layout="wide")
    st.title("Things to see | Image Selection ")

    # --- Custom CSS to style expanders and buttons ---
    st.markdown(
        """
        <style>
        /* Style the expanders with a border and padding */
        .st-expander {
            border: 2px solid #ccc;
            padding: 10px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        /* Optionally hide the expander arrow if not needed */
        .st-expanderHeader .st-expanderArrow {
            display: none;
        }
        /* Make buttons smaller */
        button[data-baseweb="button"] {
            font-size: 0.8rem;
            padding: 0.25rem 0.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ---------- Initialize Session State ----------
    # City-related state
    if "city_query" not in st.session_state:
        st.session_state.city_query = ""
    if "city_page" not in st.session_state:
        st.session_state.city_page = 1
    if "city_total" not in st.session_state:
        st.session_state.city_total = 0
    if "city_images" not in st.session_state:
        st.session_state.city_images = []
    if "selected_city_image" not in st.session_state:
        st.session_state.selected_city_image = ""
    if "selected_city_photographer" not in st.session_state:
        st.session_state.selected_city_photographer = ""
    if "selected_city_image_data" not in st.session_state:
        st.session_state.selected_city_image_data = None

    # Attraction-related state
    if "attraction_query" not in st.session_state:
        st.session_state.attraction_query = ""
    if "attraction_page" not in st.session_state:
        st.session_state.attraction_page = 1
    if "attraction_total" not in st.session_state:
        st.session_state.attraction_total = 0
    if "attraction_images" not in st.session_state:
        st.session_state.attraction_images = []
    if "selected_attraction_image" not in st.session_state:
        st.session_state.selected_attraction_image = ""
    if "selected_attraction_photographer" not in st.session_state:
        st.session_state.selected_attraction_photographer = ""
    if "selected_attraction_image_data" not in st.session_state:
        st.session_state.selected_attraction_image_data = None

    # Attraction2-related state
    if "attraction2_query" not in st.session_state:
        st.session_state.attraction2_query = ""
    if "attraction2_page" not in st.session_state:
        st.session_state.attraction2_page = 1
    if "attraction2_total" not in st.session_state:
        st.session_state.attraction2_total = 0
    if "attraction2_images" not in st.session_state:
        st.session_state.attraction2_images = []
    if "selected_attraction2_image" not in st.session_state:
        st.session_state.selected_attraction2_image = ""
    if "selected_attraction2_photographer" not in st.session_state:
        st.session_state.selected_attraction2_photographer = ""
    if "selected_attraction2_image_data" not in st.session_state:
        st.session_state.selected_attraction2_image_data = None

    # ========== City Search Section ==========
    st.subheader("Search Destination City")
    city_input = st.text_input("Enter city", key="city_input_value")
    if "city_input_prev" not in st.session_state:
        st.session_state.city_input_prev = ""

    city_search_triggered = False
    if st.button("Search City"):
        city_search_triggered = True
    elif st.session_state.city_input_value != st.session_state.city_input_prev and st.session_state.city_input_value.strip():
        city_search_triggered = True
    if city_search_triggered:
        st.session_state.city_query = st.session_state.city_input_value
        st.session_state.city_input_prev = st.session_state.city_input_value
        st.session_state.city_page = 1
        all_images = fetch_many_images(st.session_state.city_query, max_pages=20, per_page=100, orientation='portrait')
        filtered = filter_portrait(all_images)
        st.session_state.city_images = filtered
        st.session_state.city_total = len(filtered)
        st.session_state.selected_city_image = ""
        st.session_state.selected_city_photographer = ""
        st.session_state.selected_city_image_data = None
        st.session_state.city_debug = all_images  # Store debug info

    city_col, destination_col = st.columns([3, 2], gap="large")

    with city_col:
        if st.session_state.city_query and st.session_state.city_images:
            with st.expander("City Results", expanded=True):
                st.write(f"Showing **{st.session_state.city_query}**, page {st.session_state.city_page}")
                images = st.session_state.city_images
                page = st.session_state.city_page
                per_page = 5
                start = (page - 1) * per_page
                end = start + per_page
                page_images = images[start:end]
                img_cols = st.columns(len(page_images))
                for i, img_data in enumerate(page_images):
                    with img_cols[i]:
                        thumb_url = get_thumbnail_url(img_data)
                        if thumb_url:
                            st.image(thumb_url)
                        else:
                            st.write("No thumbnail available")
                        if st.button("Select", key=f"select_city_page{page}_{i}"):
                            comp_url = get_largest_image_url(img_data)
                            st.session_state.selected_city_image = comp_url or thumb_url
                            st.session_state.selected_city_photographer = get_image_source(img_data)
                            st.session_state.selected_city_image_data = img_data

                # Pagination arrows for city section
                pages = (len(images) // per_page) + (1 if len(images) % per_page > 0 else 0)
                col_btn1, col_btn2, col_spacer = st.columns([1, 1, 8])
                with col_btn1:
                    if st.button("◀", key="city_prev") and page > 1:
                        st.session_state.city_page -= 1
                        st.rerun()
                with col_btn2:
                    if st.button("▶", key="city_next") and page < pages:
                        st.session_state.city_page += 1
                        st.rerun()

    with destination_col:
        st.write("**Destination (Full Size)**")
        if st.session_state.selected_city_image_data:
            full_url = get_largest_image_url(st.session_state.selected_city_image_data)
            if full_url:
                st.image(full_url, width=800)
            image_source = get_image_source(st.session_state.selected_city_image_data)  # Get formatted description and source
            st.markdown(image_source)  # Display the image description and source with hyperlink


    # ========== First Attraction Search Section ==========
    st.subheader("Search Highlight Attraction")
    attraction_input = st.text_input("Enter attraction", key="attraction_input_value")
    if "attraction_input_prev" not in st.session_state:
        st.session_state.attraction_input_prev = ""

    attraction_search_triggered = False
    if st.button("Search Attraction"):
        attraction_search_triggered = True
    elif st.session_state.attraction_input_value != st.session_state.attraction_input_prev and st.session_state.attraction_input_value.strip():
        attraction_search_triggered = True
    
    if attraction_search_triggered:
        st.session_state.attraction_query = st.session_state.attraction_input_value
        st.session_state.attraction_input_prev = st.session_state.attraction_input_value
        st.session_state.attraction_page = 1

        # Combine city and attraction query
        combined_query = f"{st.session_state.city_query} {st.session_state.attraction_query}".strip()

        # Encode the combined query
        encoded_query = urllib.parse.quote_plus(combined_query)

        # Fetch images from Getty and Unsplash with the encoded query
        all_images = fetch_many_images(encoded_query, max_pages=20, per_page=100, orientation='landscape')
        filtered = filter_landscape(all_images)
        st.session_state.attraction_images = filtered
        st.session_state.attraction_total = len(filtered)
        st.session_state.selected_attraction_image = ""
        st.session_state.selected_attraction_photographer = ""
        st.session_state.selected_attraction_image_data = None
        st.session_state.attraction_debug = all_images  # Store debug info

    


    attraction_col, highlight_col = st.columns([3, 2], gap="large")

    with attraction_col:
        if st.session_state.attraction_query and st.session_state.attraction_images:
            with st.expander("Attraction Results", expanded=True):
                st.write(
                    f"Showing **{st.session_state.city_query} {st.session_state.attraction_query}**, "
                    f"page {st.session_state.attraction_page}"
                )
                images = st.session_state.attraction_images
                page = st.session_state.attraction_page
                per_page = 5
                start = (page - 1) * per_page
                end = start + per_page
                page_images = images[start:end]
                img_cols = st.columns(len(page_images))
                for i, img_data in enumerate(page_images):
                    with img_cols[i]:
                        thumb_url = get_thumbnail_url(img_data)
                        if thumb_url:
                            st.image(thumb_url)
                        else:
                            st.write("No thumbnail available")
                        if st.button("Select", key=f"select_attr_page{page}_{i}"):
                            comp_url = get_largest_image_url(img_data)
                            st.session_state.selected_attraction_image = comp_url or thumb_url
                            st.session_state.selected_attraction_photographer = get_image_source(img_data)
                            st.session_state.selected_attraction_image_data = img_data

                # Pagination arrows for first attraction section
                pages = (len(images) // per_page) + (1 if len(images) % per_page > 0 else 0)
                col_btn1, col_btn2, col_spacer = st.columns([1, 1, 8])
                with col_btn1:
                    if st.button("◀", key="attr_prev") and page > 1:
                        st.session_state.attraction_page -= 1
                        st.rerun()
                with col_btn2:
                    if st.button("▶", key="attr_next") and page < pages:
                        st.session_state.attraction_page += 1
                        st.rerun()
    with highlight_col:
        st.write("**Highlight (Full Size)**")
        if st.session_state.selected_attraction_image_data:
            full_url = get_largest_image_url(st.session_state.selected_attraction_image_data)
            if full_url:
                st.image(full_url, width=800)
            image_source = get_image_source(st.session_state.selected_attraction_image_data)  # Get formatted description and source
            st.markdown(image_source)  # Display the image description and source with hyperlink


    # ========== Second Attraction Search Section ==========
    st.subheader("Search Second Highlight Attraction")
    attraction2_input = st.text_input("Enter attraction", key="attraction2_input_value")
    if "attraction2_input_prev" not in st.session_state:
        st.session_state.attraction2_input_prev = ""

    attraction2_search_triggered = False
    if st.button("Search Attraction", key="search_attraction2"):
        attraction2_search_triggered = True
    elif st.session_state.attraction2_input_value != st.session_state.attraction2_input_prev and st.session_state.attraction2_input_value.strip():
        attraction2_search_triggered = True
    
    if attraction2_search_triggered:
        st.session_state.attraction2_query = st.session_state.attraction2_input_value
        st.session_state.attraction2_input_prev = st.session_state.attraction2_input_value
        st.session_state.attraction2_page = 1
        combined_query2 = f"{st.session_state.city_query} {st.session_state.attraction2_query}".strip()
        all_images2 = fetch_many_images(combined_query2, max_pages=20, per_page=100, orientation='landscape')
        filtered2 = filter_landscape(all_images2)
        st.session_state.attraction2_images = filtered2
        st.session_state.attraction2_total = len(filtered2)
        st.session_state.selected_attraction2_image = ""
        st.session_state.selected_attraction2_photographer = ""
        st.session_state.selected_attraction2_image_data = None
        st.session_state.attraction2_debug = all_images2  # Store debug info

    attraction2_col, highlight2_col = st.columns([3, 2], gap="large")

    with attraction2_col:
        if st.session_state.attraction2_query and st.session_state.attraction2_images:
            with st.expander("Attraction 2 Results", expanded=True):
                st.write(
                    f"Showing **{st.session_state.city_query} {st.session_state.attraction2_query}**, "
                    f"page {st.session_state.attraction2_page}"
                )
                images2 = st.session_state.attraction2_images
                page2 = st.session_state.attraction2_page
                per_page2 = 5
                start2 = (page2 - 1) * per_page2
                end2 = start2 + per_page2
                page_images2 = images2[start2:end2]
                img_cols2 = st.columns(len(page_images2))
                for i, img_data in enumerate(page_images2):
                    with img_cols2[i]:
                        thumb_url = get_thumbnail_url(img_data)
                        if thumb_url:
                            st.image(thumb_url)
                        else:
                            st.write("No thumbnail available")
                        if st.button("Select", key=f"select_attr2_page{page2}_{i}"):
                            comp_url = get_largest_image_url(img_data)
                            st.session_state.selected_attraction2_image = comp_url or thumb_url
                            st.session_state.selected_attraction2_photographer = get_image_source(img_data)
                            st.session_state.selected_attraction2_image_data = img_data

                # Pagination arrows for second attraction section
                pages2 = (len(images2) // per_page2) + (1 if len(images2) % per_page2 > 0 else 0)
                col_btn1, col_btn2, col_spacer = st.columns([1, 1, 8])
                with col_btn1:
                    if st.button("◀", key="attr2_prev") and page2 > 1:
                        st.session_state.attraction2_page -= 1
                        st.rerun()
                with col_btn2:
                    if st.button("▶", key="attr2_next") and page2 < pages2:
                        st.session_state.attraction2_page += 1
                        st.rerun()


    with highlight2_col:
        st.write("**Highlight 2 (Full Size)**")
        if st.session_state.selected_attraction2_image_data:
            full_url = get_largest_image_url(st.session_state.selected_attraction2_image_data)
            if full_url:
                st.image(full_url, width=800)
            image_source = get_image_source(st.session_state.selected_attraction2_image_data)  # Get formatted description and source
            st.markdown(image_source)  # Display the image description and source with hyperlink


if __name__ == "__main__":
    main()

