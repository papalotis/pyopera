import streamlit as st

try:
    from pyopera.accumulate_pages import main
except ImportError as e:
    import sys

    sys.path.append(".")
    try:
        from pyopera.accumulate_pages import main
    except ImportError:
        raise e

st.set_page_config(
    page_title="Vangelis OperArchive",
    page_icon=":violin:",
    menu_items={"About": "An interface for Vangelis' Opera Archive"},
)

hide_streamlit_style = """
            <style>
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

if __name__ == "__main__" and 1:
    main()
else:
    raise ValueError("This script should be run directly")
