import streamlit as st
import requests
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Access the Unsplash API key
access_key = os.getenv("UNSPLASH_ACCESS_KEY")
secret_key = os.getenv("UNSPLASH_SECRET_KEY")


# Function to fetch images from Unsplash API
def fetch_images_unsplash(access_key, query, page, per_page=20):
    url = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {access_key}"}
    params = {
        "query": query,
        "page": page,
        "per_page": per_page,
    }
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        st.error(f"Failed to fetch images: {response.status_code}")
        return None

# Streamlit App
def main():
    st.title("KLM Image Explorer")

    # User input for city and attraction
    city = st.text_input("Enter city:")
    attraction = st.text_input("Enter attraction:")

    # Initialize session state variables
    if "page" not in st.session_state:
        st.session_state.page = 1
    if "selected_image" not in st.session_state:
        st.session_state.selected_image = None
    if "images" not in st.session_state:
        st.session_state.images = []

    # Search button
    if st.button("Search"):
        if city and attraction:
            query = f"{city} {attraction}"
            st.session_state.page = 1  # Reset to the first page
            data = fetch_images_unsplash(access_key, query, st.session_state.page)
            if data:
                st.session_state.images = data.get("results", [])
                st.session_state.selected_image = None
        else:
            st.error("Please fill all fields.")

    # Display search results if images are available
    if st.session_state.images:
        st.write(f"Showing results for: {city} {attraction} (Page {st.session_state.page})")
        cols = st.columns(5)

        for i, image in enumerate(st.session_state.images):
            image_url = image["urls"]["regular"]
            photographer = image["user"]["name"]

            with cols[i % 5]:
                st.image(image_url, use_container_width=True)
                if st.button("Select", key=f"select_{image['id']}"):
                    st.session_state.selected_image = (image_url, photographer)

        # Pagination controls
        col1, col2 = st.columns(2)
        if col1.button("Previous Page"):
            st.session_state.page = max(1, st.session_state.page - 1)
            data = fetch_images_unsplash(access_key, f"{city} {attraction}", st.session_state.page)
            if data:
                st.session_state.images = data.get("results", [])
        if col2.button("Next Page"):
            st.session_state.page += 1
            data = fetch_images_unsplash(access_key, f"{city} {attraction}", st.session_state.page)
            if data:
                st.session_state.images = data.get("results", [])

    # Display selected image
    if st.session_state.selected_image:
        st.write("### Selected Image:")
        selected_url, photographer = st.session_state.selected_image
        st.image(selected_url, caption=f"By {photographer}", use_container_width=True)

if __name__ == "__main__":
    main()