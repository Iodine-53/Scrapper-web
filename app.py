import io
from PIL import Image, ImageOps
import streamlit as st

st.set_page_config(page_title="Image Resizer", page_icon="🖼️")
st.title("🖼️ Image Resizer")
st.markdown("Resize your images locally. No files are uploaded to the internet.")

uploaded_file = st.file_uploader("Select Image", type=["png", "jpg", "jpeg", "webp", "bmp"])

if uploaded_file:
    col1, col2 = st.columns(2)
    with col1:
        width = st.number_input("Target Width (pixels)", min_value=1, value=800)
    with col2:
        height = st.number_input("Target Height (pixels)", min_value=1, value=600)

    img = Image.open(uploaded_file)
    st.image(img, caption="Original", use_container_width=True)

    if st.button("Resize & Download"):
        img_format = img.format if img.format else "PNG"
        resized = ImageOps.fit(img, (width, height), Image.Resampling.LANCZOS)

        buf = io.BytesIO()
        resized.save(buf, format=img_format)
        buf.seek(0)

        ext = img_format.lower().replace("jpeg", "jpg")
        filename = uploaded_file.name.rsplit(".", 1)[0] if uploaded_file.name else "image"
        st.download_button(
            label="Download Resized Image",
            data=buf,
            file_name=f"{filename}_resized.{ext}",
            mime=f"image/{ext}",
        )
