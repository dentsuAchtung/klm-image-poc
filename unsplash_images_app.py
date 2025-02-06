import streamlit as st
import requests
from dotenv import load_dotenv
import os

load_dotenv()
access_key = os.getenv("UNSPLASH_ACCESS_KEY")
secret_key = os.getenv("UNSPLASH_SECRET_KEY")


def fetch_images(query, page=1, per_page=5):
    """Fetch a page of results from the Unsplash API."""
    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "page": page,
        "per_page": per_page,
        "client_id": access_key
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Unsplash API error {response.status_code}: {response.text}")
        return {}


def main():
    st.set_page_config(layout="wide")
    st.title("KLM Image Explorer")

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
        st.session_state.city_images = data.get("results", [])
        st.session_state.city_total = data.get("total", 0)
        st.session_state.selected_city_image = ""
        st.session_state.selected_city_photographer = ""
        st.rerun()

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
                        thumb_url = img_data["urls"]["thumb"]
                        st.image(thumb_url, use_container_width=True)
                        # When an image is selected, store both the full version and photographer name.
                        if st.button("Select", key=f"select_city_page{st.session_state.city_page}_{i}"):
                            st.session_state.selected_city_image = img_data["urls"]["regular"]
                            st.session_state.selected_city_photographer = img_data["user"]["name"]
                            st.rerun()

                # ---------- Pagination Arrows (aligned left and closer together) ----------
                pages = (st.session_state.city_total // 5) + 1
                col_btn1, col_btn2, col_spacer = st.columns([1, 1, 8])
                with col_btn1:
                    if st.button("◀", key="city_prev") and st.session_state.city_page > 1:
                        st.session_state.city_page -= 1
                        data = fetch_images(st.session_state.city_query,
                                            page=st.session_state.city_page,
                                            per_page=5)
                        st.session_state.city_images = data.get("results", [])
                        st.session_state.city_total = data.get("total", 0)
                        st.rerun()
                with col_btn2:
                    if st.button("▶", key="city_next") and st.session_state.city_page < pages:
                        st.session_state.city_page += 1
                        data = fetch_images(st.session_state.city_query,
                                            page=st.session_state.city_page,
                                            per_page=5)
                        st.session_state.city_images = data.get("results", [])
                        st.session_state.city_total = data.get("total", 0)
                        st.rerun()

    with destination_col:
        st.write("**Destination (Full Size)**")
        if st.session_state.selected_city_image:
            # Display the full-size image with a larger width.
            st.image(st.session_state.selected_city_image, width=800)
            st.write("Photo by", st.session_state.selected_city_photographer)

    # ========== Attraction Search Section ==========
    st.subheader("Attraction Search")
    attraction_input = st.text_input("Enter attraction", key="attraction_query")

    if st.button("Search Attraction"):
        st.session_state.attraction_page = 1
        combined_query = f"{st.session_state.city_query} {st.session_state.attraction_query}".strip()
        data = fetch_images(combined_query, page=1, per_page=5)
        st.session_state.attraction_images = data.get("results", [])
        st.session_state.attraction_total = data.get("total", 0)
        st.session_state.selected_attraction_image = ""
        st.session_state.selected_attraction_photographer = ""
        st.rerun()

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
                        thumb_url = img_data["urls"]["thumb"]
                        st.image(thumb_url, use_container_width=True)
                        if st.button("Select", key=f"select_attr_page{st.session_state.attraction_page}_{i}"):
                            st.session_state.selected_attraction_image = img_data["urls"]["regular"]
                            st.session_state.selected_attraction_photographer = img_data["user"]["name"]
                            st.rerun()

                # ---------- Pagination Arrows for attractions (aligned left and closer together) ----------
                pages = (st.session_state.attraction_total // 5) + 1
                col_btn1, col_btn2, col_spacer = st.columns([1, 1, 8])
                with col_btn1:
                    if st.button("◀", key="attr_prev") and st.session_state.attraction_page > 1:
                        st.session_state.attraction_page -= 1
                        combined_query = f"{st.session_state.city_query} {st.session_state.attraction_query}".strip()
                        data = fetch_images(combined_query,
                                            page=st.session_state.attraction_page,
                                            per_page=5)
                        st.session_state.attraction_images = data.get("results", [])
                        st.session_state.attraction_total = data.get("total", 0)
                        st.rerun()
                with col_btn2:
                    if st.button("▶", key="attr_next") and st.session_state.attraction_page < pages:
                        st.session_state.attraction_page += 1
                        combined_query = f"{st.session_state.city_query} {st.session_state.attraction_query}".strip()
                        data = fetch_images(combined_query,
                                            page=st.session_state.attraction_page,
                                            per_page=5)
                        st.session_state.attraction_images = data.get("results", [])
                        st.session_state.attraction_total = data.get("total", 0)
                        st.rerun()

    with highlight_col:
        st.write("**Highlight (Full Size)**")
        if st.session_state.selected_attraction_image:
            st.image(st.session_state.selected_attraction_image, width=800)
            st.write("Photo by", st.session_state.selected_attraction_photographer)


if __name__ == "__main__":
    main()
