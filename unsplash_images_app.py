import streamlit as st
import requests
from dotenv import load_dotenv
import os
import base64

load_dotenv()
api_key = os.getenv("GETTY_API_KEY", "26rguqfz64pf5vhp5pgzk6mr")  # Default to your provided key
client_secret = os.getenv("GETTY_CLIENT_SECRET", "PYzgvn4v4hz4go4Mvzaf")  # Default to your provided secret

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

def fetch_images(query, page=1, per_page=5):
    """Fetch a page of results from the Getty Images API."""
    
    # Get access token
    token = get_access_token()
    if not token:
        return {}
    
    url = "https://api.gettyimages.com/v3/search/images/creative"
    
    headers = {
        "Api-Key": api_key,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    params = {
        "phrase": query,
        "page": page,
        "page_size": per_page,
        "fields": "id,title,thumb,preview,comp,display_sizes"  # Request display sizes
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Getty Images API error {response.status_code}: {response.text}")
            return {}
    except Exception as e:
        st.error(f"Error fetching images: {str(e)}")
        return {}


def main():
    st.set_page_config(layout="wide")
    st.title("KLM Image Explorer - Getty Images")

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

    # ========== City Search Section ==========
    st.subheader("City Search")
    city_input = st.text_input("Enter city", key="city_query")

    if st.button("Search City"):
        st.session_state.city_page = 1
        data = fetch_images(st.session_state.city_query, page=1, per_page=5)
        st.session_state.city_images = data.get("images", [])
        st.session_state.city_total = data.get("result_count", 0)
        st.session_state.selected_city_image = ""
        st.session_state.selected_city_photographer = ""
        st.experimental_rerun()

    city_col, destination_col = st.columns([3, 2], gap="large")

    with city_col:
        if st.session_state.city_query and st.session_state.city_images:
            with st.expander("City Results", expanded=True):
                st.write(f"Showing **{st.session_state.city_query}**, page {st.session_state.city_page}")

                # ---------- Display the current page's row of images ----------
                images = st.session_state.city_images
                img_cols = st.columns(len(images))
                for i, img_data in enumerate(images):
                    with img_cols[i]:
                        # Getty Images API structure
                        thumb_url = None
                        if "display_sizes" in img_data:
                            for size in img_data["display_sizes"]:
                                if size["name"] == "thumb":
                                    thumb_url = size["uri"]
                                    break
                        
                        if thumb_url:
                            st.image(thumb_url)
                        else:
                            st.write("No thumbnail available")
                        
                        # When an image is selected, store both the full version and title
                        if st.button("Select", key=f"select_city_page{st.session_state.city_page}_{i}"):
                            comp_url = None
                            if "display_sizes" in img_data:
                                for size in img_data["display_sizes"]:
                                    if size["name"] == "comp":
                                        comp_url = size["uri"]
                                        break
                            
                            st.session_state.selected_city_image = comp_url or thumb_url
                            st.session_state.selected_city_photographer = img_data.get("title", "Getty Images")
                            st.experimental_rerun()

                # ---------- Pagination Arrows (aligned left and closer together) ----------
                if st.session_state.city_total > 0:
                    pages = (st.session_state.city_total // 5) + (1 if st.session_state.city_total % 5 > 0 else 0)
                    col_btn1, col_btn2, col_spacer = st.columns([1, 1, 8])
                    with col_btn1:
                        if st.button("◀", key="city_prev") and st.session_state.city_page > 1:
                            st.session_state.city_page -= 1
                            data = fetch_images(st.session_state.city_query,
                                                page=st.session_state.city_page,
                                                per_page=5)
                            st.session_state.city_images = data.get("images", [])
                            st.session_state.city_total = data.get("result_count", 0)
                            st.experimental_rerun()
                    with col_btn2:
                        if st.button("▶", key="city_next") and st.session_state.city_page < pages:
                            st.session_state.city_page += 1
                            data = fetch_images(st.session_state.city_query,
                                                page=st.session_state.city_page,
                                                per_page=5)
                            st.session_state.city_images = data.get("images", [])
                            st.session_state.city_total = data.get("result_count", 0)
                            st.experimental_rerun()

    with destination_col:
        st.write("**Destination (Full Size)**")
        if st.session_state.selected_city_image:
            # Display the full-size image with a larger width.
            st.image(st.session_state.selected_city_image, width=800)
            st.write("Image:", st.session_state.selected_city_photographer)
            st.write("Source: Getty Images")

    # ========== Attraction Search Section ==========
    st.subheader("Attraction Search")
    attraction_input = st.text_input("Enter attraction", key="attraction_query")

    if st.button("Search Attraction"):
        st.session_state.attraction_page = 1
        combined_query = f"{st.session_state.city_query} {st.session_state.attraction_query}".strip()
        data = fetch_images(combined_query, page=1, per_page=5)
        st.session_state.attraction_images = data.get("images", [])
        st.session_state.attraction_total = data.get("result_count", 0)
        st.session_state.selected_attraction_image = ""
        st.session_state.selected_attraction_photographer = ""
        st.experimental_rerun()

    attraction_col, highlight_col = st.columns([3, 2], gap="large")

    with attraction_col:
        if st.session_state.attraction_query and st.session_state.attraction_images:
            with st.expander("Attraction Results", expanded=True):
                st.write(
                    f"Showing **{st.session_state.city_query} {st.session_state.attraction_query}**, "
                    f"page {st.session_state.attraction_page}"
                )

                images = st.session_state.attraction_images
                img_cols = st.columns(len(images))
                for i, img_data in enumerate(images):
                    with img_cols[i]:
                        # Getty Images API structure
                        thumb_url = None
                        if "display_sizes" in img_data:
                            for size in img_data["display_sizes"]:
                                if size["name"] == "thumb":
                                    thumb_url = size["uri"]
                                    break
                        
                        if thumb_url:
                            st.image(thumb_url)
                        else:
                            st.write("No thumbnail available")
                        
                        if st.button("Select", key=f"select_attr_page{st.session_state.attraction_page}_{i}"):
                            comp_url = None
                            if "display_sizes" in img_data:
                                for size in img_data["display_sizes"]:
                                    if size["name"] == "comp":
                                        comp_url = size["uri"]
                                        break
                            
                            st.session_state.selected_attraction_image = comp_url or thumb_url
                            st.session_state.selected_attraction_photographer = img_data.get("title", "Getty Images")
                            st.experimental_rerun()

                # ---------- Pagination Arrows for attractions (aligned left and closer together) ----------
                if st.session_state.attraction_total > 0:
                    pages = (st.session_state.attraction_total // 5) + (1 if st.session_state.attraction_total % 5 > 0 else 0)
                    col_btn1, col_btn2, col_spacer = st.columns([1, 1, 8])
                    with col_btn1:
                        if st.button("◀", key="attr_prev") and st.session_state.attraction_page > 1:
                            st.session_state.attraction_page -= 1
                            combined_query = f"{st.session_state.city_query} {st.session_state.attraction_query}".strip()
                            data = fetch_images(combined_query,
                                                page=st.session_state.attraction_page,
                                                per_page=5)
                            st.session_state.attraction_images = data.get("images", [])
                            st.session_state.attraction_total = data.get("result_count", 0)
                            st.experimental_rerun()
                    with col_btn2:
                        if st.button("▶", key="attr_next") and st.session_state.attraction_page < pages:
                            st.session_state.attraction_page += 1
                            combined_query = f"{st.session_state.city_query} {st.session_state.attraction_query}".strip()
                            data = fetch_images(combined_query,
                                                page=st.session_state.attraction_page,
                                                per_page=5)
                            st.session_state.attraction_images = data.get("images", [])
                            st.session_state.attraction_total = data.get("result_count", 0)
                            st.experimental_rerun()

    with highlight_col:
        st.write("**Highlight (Full Size)**")
        if st.session_state.selected_attraction_image:
            st.image(st.session_state.selected_attraction_image, width=800)
            st.write("Image:", st.session_state.selected_attraction_photographer)
            st.write("Source: Getty Images")


if __name__ == "__main__":
    main()
